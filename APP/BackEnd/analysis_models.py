"""Data containers for the AI analysis result and the final rendered clip."""
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class ZoomRegion:
    """Purpose: a time range where the video should punch-in toward a point.
    focus_x / focus_y are 0..1 fractions of the source frame."""

    start: float
    end: float
    focus_x: float = 0.5
    focus_y: float = 0.5
    zoom: float = 1.3
    reason: str = ""


@dataclass
class ClipAnalysis:
    """Purpose: everything the AI extracted for one clip - title, subtitle lines
    (built from Whisper timestamps), emphasis words, zoom moments and extras."""

    title: str
    summary: str = ""
    subtitle_lines: list = field(default_factory=list)   # list[SubtitleLine]
    emphasis_words: list = field(default_factory=list)   # list[str], lowercase
    zoom_regions: list = field(default_factory=list)     # list[ZoomRegion]
    hashtags: list = field(default_factory=list)         # list[str]
    transcript: str = ""


@dataclass
class ProcessedClip:
    """Purpose: result of the full pipeline for one clip - what the UI shows in a
    card and what storage_service saves."""

    clip_id: str
    title: str
    video_path: Path
    summary: str = ""
    hashtags: list = field(default_factory=list)
    source_url: str = ""
    broadcaster_name: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        data["video_path"] = str(self.video_path)
        return data
