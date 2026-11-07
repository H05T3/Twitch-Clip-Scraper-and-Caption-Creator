"""Renders the 9:16 portrait video: blurred background, centred clip, zoom punch-ins,
title banner and subtitles - all in one ffmpeg pass."""
import re
from pathlib import Path

from APP.BackEnd.analysis_models import ClipAnalysis, ZoomRegion
from APP.BackEnd.caption_file_builder import CaptionFileBuilder
from APP.BackEnd.config import Settings
from APP.BackEnd.errors import ProcessingError
from APP.BackEnd.ffmpeg_runner import FfmpegRunner

# Name of the temporary caption file written next to the output (deleted afterwards).
CAPTION_FILE_SUFFIX = ".captions.ass"
# Characters allowed in the temporary caption file name (keeps ffmpeg filter paths simple).
UNSAFE_NAME_CHARS = r"[^A-Za-z0-9_-]"
# How much of an ffmpeg error message to keep.
ERROR_TAIL_CHARS = 800


class FilterGraphBuilder:
    """Single responsibility: build the ffmpeg `-filter_complex` string.

    Layout: [blurred+dimmed full-frame copy] <- [clip scaled to full width, centred]
    then, for each ZoomRegion, a cropped+scaled copy of the clip is overlaid only
    during that time range, and finally the caption file is burned in."""

    def __init__(self, settings: Settings):
        self.settings = settings

    @staticmethod
    def non_overlapping(regions: list) -> list:
        """Sort by start time and trim so no two zoom regions overlap."""
        cleaned, last_end = [], 0.0
        for region in sorted(regions, key=lambda r: r.start):
            start = max(region.start, last_end)
            if region.end - start > 0:
                cleaned.append(ZoomRegion(start, region.end, region.focus_x, region.focus_y, region.zoom, region.reason))
                last_end = region.end
        return cleaned

    def build(self, caption_filename: str, regions: list) -> str:
        s = self.settings
        w, h = s.output_width, s.output_height
        regions = self.non_overlapping(regions) if s.zoom_enabled else []
        split_count = 2 + len(regions)
        labels = "".join(f"[src{i}]" for i in range(split_count))
        parts = [
            f"[0:v]split={split_count}{labels}",
            # Background: fill the portrait frame, blur it, darken it.
            f"[src0]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
            f"boxblur={s.background_blur}:1,lutyuv=y=val*{s.background_dim}[bg]",
            # Foreground: full width, original aspect ratio.
            f"[src1]scale={w}:-2[fg]",
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2+{s.video_y_offset}[v0]",
        ]
        for index, region in enumerate(regions):
            z, fx, fy = region.zoom, region.focus_x, region.focus_y
            # Crop window of size (iw/z, ih/z) centred on the focus point, kept inside the frame.
            crop_x = f"min(max({fx}*iw-iw/(2*{z}),0),iw-iw/{z})"
            crop_y = f"min(max({fy}*ih-ih/(2*{z}),0),ih-ih/{z})"
            parts.append(
                f"[src{index + 2}]crop=iw/{z}:ih/{z}:x='{crop_x}':y='{crop_y}',scale={w}:-2[z{index}]"
            )
            parts.append(
                f"[v{index}][z{index}]overlay=(W-w)/2:(H-h)/2+{s.video_y_offset}:"
                f"enable='between(t,{region.start:.3f},{region.end:.3f})'[v{index + 1}]"
            )
        parts.append(f"[v{len(regions)}]ass=filename={caption_filename}[vout]")
        return ";".join(parts)


class VideoProcessor:
    """Single responsibility: run ffmpeg to produce the finished portrait MP4
    (1080x1920 by default) from a downloaded clip and its ClipAnalysis."""

    def __init__(self, settings: Settings, caption_builder: CaptionFileBuilder = None,
                 graph_builder: FilterGraphBuilder = None, runner: FfmpegRunner = None):
        self.settings = settings
        self.runner = runner or FfmpegRunner(settings)
        self.caption_builder = caption_builder or CaptionFileBuilder(settings)
        self.graph_builder = graph_builder or FilterGraphBuilder(settings)

    def render(self, source: Path, analysis: ClipAnalysis, output_path: Path) -> Path:
        s = self.settings
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        safe_stem = re.sub(UNSAFE_NAME_CHARS, "_", output_path.stem)
        caption_path = output_path.parent / f"{safe_stem}{CAPTION_FILE_SUFFIX}"
        self.caption_builder.write(analysis, caption_path)
        graph = self.graph_builder.build(caption_path.name, analysis.zoom_regions)
        arguments = [
            "-y", "-i", str(Path(source).resolve()),
            "-filter_complex", graph, "-map", "[vout]", "-map", "0:a?",
            "-c:v", s.video_codec, "-crf", str(s.video_crf), "-preset", s.video_preset,
            "-pix_fmt", s.pixel_format, "-c:a", s.audio_codec, "-b:a", s.audio_bitrate,
            "-movflags", "+faststart", str(output_path),
        ]
        # cwd = caption file folder so the ass filter gets a plain file name (no path escaping).
        result = self.runner.run(arguments, cwd=output_path.parent)
        caption_path.unlink(missing_ok=True)
        if result.returncode != 0:
            raise ProcessingError(f"ffmpeg failed: {result.stderr[-ERROR_TAIL_CHARS:]}")
        return output_path
