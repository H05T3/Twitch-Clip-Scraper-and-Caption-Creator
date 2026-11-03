"""Typed access to environment variables (loaded from the project's .env file).

Kept separate from config.py so that config.py can stay a plain list of settings.
"""
import os
from pathlib import Path


class EnvReader:
    """Single responsibility: read environment variables and convert them to
    the right Python type, falling back to a supplied default when unset/blank."""

    def __init__(self, project_root: Path):
        # Relative paths from the .env file are resolved against this folder.
        self.project_root = project_root

    def _raw(self, name: str, default):
        """Return the raw string for `name`, or `default` if missing or blank."""
        value = os.environ.get(name)
        if value is None or value.strip() == "":
            return default
        return value.strip()

    def text(self, name: str, default: str = "") -> str:
        return str(self._raw(name, default))

    def integer(self, name: str, default: int) -> int:
        return int(self._raw(name, default))

    def number(self, name: str, default: float) -> float:
        return float(self._raw(name, default))

    def boolean(self, name: str, default: bool) -> bool:
        raw = self._raw(name, default)
        if isinstance(raw, bool):
            return raw
        return str(raw).lower() in ("1", "true", "yes", "on")

    def path(self, name: str, default: str) -> Path:
        """Read a path; relative paths are anchored at the project root."""
        candidate = Path(str(self._raw(name, default))).expanduser()
        return candidate if candidate.is_absolute() else self.project_root / candidate
