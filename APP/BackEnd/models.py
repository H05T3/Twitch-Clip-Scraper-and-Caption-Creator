"""Plain data containers for clips and transcripts (no logic beyond simple helpers)."""
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass
class ClipInfo:
    """Purpose: metadata about one Twitch clip, as returned by the Helix API,
    plus the local path of its downloaded source file once available."""

    clip_id: str
    url: str
    title: str
    broadcaster_name: str
    creator_name: str
    created_at: str
    duration: float
    view_count: int = 0
    thumbnail_url: str = ""
    source_path: Optional[Path] = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["source_path"] = str(self.source_path) if self.source_path else None
        return data


@dataclass
class WordTiming:
    """Purpose: one spoken word with its start/end time in seconds."""

    text: str
    start: float
    end: float


@dataclass
class SubtitleLine:
    """Purpose: a short group of words shown together on screen at one time.
    `words` keeps per-word timing so the renderer can highlight word-by-word."""

    words: list = field(default_factory=list)  # list[WordTiming]

    @property
    def start(self) -> float:
        return self.words[0].start

    @property
    def end(self) -> float:
        return self.words[-1].end

    @property
    def text(self) -> str:
        return " ".join(word.text for word in self.words)
