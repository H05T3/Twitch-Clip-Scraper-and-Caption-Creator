"""Local persistence: user settings/counters (settings.json) and the SavedClips library."""
import json
import re
import shutil
from pathlib import Path

from APP.BackEnd.analysis_models import ProcessedClip
from APP.BackEnd.config import Settings
from APP.BackEnd.errors import ClipperError

# Keys inside settings.json and their starting values.
KEY_THEME = "theme"
KEY_CLIPS_CREATED = "clips_created"
KEY_CLIPS_SAVED = "clips_saved"
# Characters unsafe in file names.
UNSAFE_NAME_CHARS = r"[^A-Za-z0-9_-]"
# Max length of the title part of a saved file name.
MAX_NAME_SLUG_LENGTH = 40


class SettingsStore:
    """Single responsibility: read/write settings.json, which remembers the UI
    theme (so it is preset next launch) and the clip counters shown on Home.
    The theme from .env is only the first-run default."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.path = settings.settings_file

    def _load(self) -> dict:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @property
    def theme(self) -> str:
        return self._load().get(KEY_THEME, self.settings.theme)

    def set_theme(self, theme: str) -> None:
        theme = theme.lower()
        if theme not in self.settings.allowed_themes:
            raise ClipperError(f"Theme must be one of: {', '.join(self.settings.allowed_themes)}")
        data = self._load()
        data[KEY_THEME] = theme
        self._save(data)

    def get_counter(self, key: str) -> int:
        return int(self._load().get(key, 0))

    def increment(self, key: str, amount: int = 1) -> int:
        data = self._load()
        data[key] = int(data.get(key, 0)) + amount
        self._save(data)
        return data[key]


class ClipLibrary:
    """Single responsibility: manage finished clips on disk. Saving copies the
    rendered MP4 into SavedClips with a small .json sidecar (title, summary,
    hashtags, source link); listing/deleting works on that folder."""

    def __init__(self, settings: Settings, store: SettingsStore):
        self.settings = settings
        self.store = store
        self.folder = settings.saved_clips_dir

    def save(self, clip: ProcessedClip) -> Path:
        self.folder.mkdir(parents=True, exist_ok=True)
        slug = re.sub(UNSAFE_NAME_CHARS, "_", clip.title.replace(" ", "_"))[:MAX_NAME_SLUG_LENGTH].strip("_")
        base = f"{slug}_{re.sub(UNSAFE_NAME_CHARS, '_', clip.clip_id)}" if slug else re.sub(UNSAFE_NAME_CHARS, "_", clip.clip_id)
        video_target = self.folder / f"{base}{self.settings.clip_file_extension}"
        shutil.copy2(clip.video_path, video_target)
        meta = clip.to_dict()
        meta["video_path"] = str(video_target)
        video_target.with_suffix(self.settings.metadata_file_extension).write_text(
            json.dumps(meta, indent=2), encoding="utf-8")
        self.store.increment(KEY_CLIPS_SAVED)
        return video_target

    def list_clips(self) -> list:
        """All saved clips, newest first, as dicts {video_path, title, ...}."""
        if not self.folder.exists():
            return []
        videos = sorted(self.folder.glob(f"*{self.settings.clip_file_extension}"),
                        key=lambda p: p.stat().st_mtime, reverse=True)
        clips = []
        for video in videos:
            sidecar = video.with_suffix(self.settings.metadata_file_extension)
            try:
                meta = json.loads(sidecar.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                meta = {"title": video.stem}
            meta["video_path"] = str(video)
            clips.append(meta)
        return clips

    def delete(self, video_path: Path) -> None:
        video_path = Path(video_path)
        if video_path.parent.resolve() != self.folder.resolve():
            raise ClipperError("Can only delete clips inside the SavedClips folder.")
        video_path.unlink(missing_ok=True)
        video_path.with_suffix(self.settings.metadata_file_extension).unlink(missing_ok=True)

    def stats(self) -> dict:
        """Numbers for the Home screen."""
        return {
            "clips_created": self.store.get_counter(KEY_CLIPS_CREATED),
            "clips_saved": len(self.list_clips()),
            "saved_clips_dir": str(self.folder),
        }
