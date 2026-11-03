"""Builds the .ass caption file (top title banner + bottom word-highlight subtitles)."""
import math
import textwrap
from pathlib import Path

from APP.BackEnd.analysis_models import ClipAnalysis
from APP.BackEnd.config import Settings

# Average glyph width / line height relative to font size (used to wrap the title).
CHAR_WIDTH_RATIO = 0.62
LINE_HEIGHT_RATIO = 1.25
# ASS layers: higher draws on top.
LAYER_BANNER, LAYER_TITLE, LAYER_SUBTITLE = 0, 1, 2
# ASS alignment codes (numpad layout): 8 = top-center, 2 = bottom-center.
ALIGN_TOP_CENTER, ALIGN_BOTTOM_CENTER = 8, 2
# Scale (%) applied to emphasis words.
EMPHASIS_SCALE_PERCENT = 115
# Style names used inside the .ass file.
STYLE_TITLE, STYLE_SUBTITLE, STYLE_BANNER = "Title", "Sub", "Banner"
# Events last until the end of the video; this is "a very long time" in seconds.
FOREVER_SECONDS = 36000


def ass_color(hex_color: str, opacity: float = 1.0) -> str:
    """'#RRGGBB' (+ opacity 0..1) -> ASS '&HAABBGGRR' (AA: 00 opaque .. FF clear)."""
    value = hex_color.lstrip("#")
    red, green, blue = value[0:2], value[2:4], value[4:6]
    alpha = round((1.0 - min(max(opacity, 0.0), 1.0)) * 255)
    return f"&H{alpha:02X}{blue}{green}{red}".upper()


def ass_time(seconds: float) -> str:
    """Seconds -> ASS timestamp h:mm:ss.cc"""
    centis = int(round(max(seconds, 0.0) * 100))
    return f"{centis // 360000}:{centis // 6000 % 60:02d}:{centis // 100 % 60:02d}.{centis % 100:02d}"


def ass_text(text: str) -> str:
    """Remove characters that ASS treats as markup."""
    return text.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ")


class CaptionFileBuilder:
    """Single responsibility: turn a ClipAnalysis (title + subtitle lines +
    emphasis words) into the text of an ASS subtitle file that ffmpeg burns
    into the video. Layout/colours/fonts all come from Settings."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def _wrap(self, title: str) -> list:
        s = self.settings
        usable = s.output_width - 2 * s.title_side_margin
        chars_per_line = max(1, int(usable / (s.title_font_size * CHAR_WIDTH_RATIO)))
        return textwrap.wrap(title, width=chars_per_line) or [title]

    def build(self, analysis: ClipAnalysis) -> str:
        s = self.settings
        lines = self._wrap(ass_text(analysis.title))
        text_height = math.ceil(len(lines) * s.title_font_size * LINE_HEIGHT_RATIO)
        banner_height = text_height + 2 * s.title_banner_padding
        banner_top = s.title_top_margin
        center_x = s.output_width // 2

        header = [
            "[Script Info]", "ScriptType: v4.00+",
            f"PlayResX: {s.output_width}", f"PlayResY: {s.output_height}",
            "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
            "[V4+ Styles]",
            "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,"
            "Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,"
            "Alignment,MarginL,MarginR,MarginV,Encoding",
            # Title: text colour, no outline.
            f"Style: {STYLE_TITLE},{s.title_font},{s.title_font_size},{ass_color(s.title_text_color)},"
            f"{ass_color(s.title_text_color)},&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,"
            f"{ALIGN_TOP_CENTER},{s.title_side_margin},{s.title_side_margin},0,1",
            # Subtitles: base colour, outlined, bottom-centre.
            f"Style: {STYLE_SUBTITLE},{s.subtitle_font},{s.subtitle_font_size},{ass_color(s.subtitle_text_color)},"
            f"{ass_color(s.subtitle_text_color)},{ass_color(s.subtitle_outline_color)},&H00000000,-1,0,0,0,100,100,0,0,1,"
            f"{s.subtitle_outline_width},0,{ALIGN_BOTTOM_CENTER},{s.subtitle_side_margin},{s.subtitle_side_margin},"
            f"{s.subtitle_bottom_margin},1",
            # Banner: only used for the vector rectangle.
            f"Style: {STYLE_BANNER},{s.title_font},{s.title_font_size},{ass_color(s.title_banner_color, s.title_banner_opacity)},"
            f"&H00000000,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1",
            "", "[Events]",
            "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
        ]
        end = ass_time(FOREVER_SECONDS)
        events = [
            # Backing banner = filled rectangle drawn with ASS vector commands.
            f"Dialogue: {LAYER_BANNER},{ass_time(0)},{end},{STYLE_BANNER},,0,0,0,,"
            f"{{\\pos(0,{banner_top})\\p1}}m 0 0 l {s.output_width} 0 {s.output_width} {banner_height} 0 {banner_height}{{\\p0}}",
            f"Dialogue: {LAYER_TITLE},{ass_time(0)},{end},{STYLE_TITLE},,0,0,0,,"
            f"{{\\pos({center_x},{banner_top + s.title_banner_padding})}}" + "\\N".join(lines),
        ]
        events.extend(self._subtitle_events(analysis))
        return "\n".join(header + events) + "\n"

    def _subtitle_events(self, analysis: ClipAnalysis) -> list:
        """One event per word: the whole line is shown, and only the word being
        spoken is coloured with the highlight colour (TikTok style)."""
        s = self.settings
        emphasis = set(analysis.emphasis_words)
        highlight = ass_color(s.subtitle_highlight_color)
        base = ass_color(s.subtitle_text_color)
        events = []
        for line in analysis.subtitle_lines:
            for index, active in enumerate(line.words):
                start = active.start
                end = line.words[index + 1].start if index + 1 < len(line.words) else line.end
                if end <= start:
                    end = start + 0.05
                parts = []
                for word in line.words:
                    shown = ass_text(word.text.upper() if s.subtitle_uppercase else word.text)
                    colour = highlight if word is active else base
                    scale = EMPHASIS_SCALE_PERCENT if word.text.lower().strip(".,!?\"'") in emphasis else 100
                    parts.append(f"{{\\c{colour}\\fscx{scale}\\fscy{scale}}}{shown}")
                events.append(
                    f"Dialogue: {LAYER_SUBTITLE},{ass_time(start)},{ass_time(end)},{STYLE_SUBTITLE},,0,0,0,,"
                    + " ".join(parts)
                )
        return events

    def write(self, analysis: ClipAnalysis, path: Path) -> Path:
        path.write_text(self.build(analysis), encoding="utf-8")
        return path
