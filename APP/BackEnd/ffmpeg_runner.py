"""Finds ffmpeg and runs it, turning 'file not found' into a clear, friendly error."""
import os
import shutil
import subprocess

from APP.BackEnd.config import Settings
from APP.BackEnd.errors import ProcessingError

# Shown when no ffmpeg can be found anywhere.
MSG_FFMPEG_MISSING = (
    "ffmpeg was not found. Run:  pip install imageio-ffmpeg   (easiest), or install ffmpeg "
    "and add it to your PATH, or set FFMPEG_BINARY in .env to its full path. (Looked for: '{name}')"
)
MSG_FFMPEG_FAILED_TO_START = "ffmpeg could not be started ({error}). Check FFMPEG_BINARY in .env."


class FfmpegRunner:
    """Single responsibility: locate an ffmpeg executable and run it.
    Search order: (1) FFMPEG_BINARY from .env as a full path, (2) that name on the PATH,
    (3) the copy bundled with the 'imageio-ffmpeg' pip package.
    Any failure to find/start it raises ProcessingError with instructions, instead of
    a raw 'WinError 2'."""

    def __init__(self, settings: Settings, allow_bundled: bool = True):
        self.settings = settings
        self.allow_bundled = allow_bundled
        self._resolved = None

    def locate(self) -> str:
        if self._resolved:
            return self._resolved
        configured = self.settings.ffmpeg_binary
        found = configured if os.path.isfile(configured) else shutil.which(configured)
        if not found and self.allow_bundled:
            try:
                import imageio_ffmpeg
                found = imageio_ffmpeg.get_ffmpeg_exe()
            except Exception:  # package missing or its binary unavailable
                found = None
        if not found:
            raise ProcessingError(MSG_FFMPEG_MISSING.format(name=configured))
        self._resolved = found
        return found

    def run(self, arguments: list, cwd=None) -> subprocess.CompletedProcess:
        """Run ffmpeg with `arguments` (everything after the program name)."""
        command = [self.locate()] + [str(a) for a in arguments]
        try:
            return subprocess.run(command, capture_output=True, text=True, cwd=cwd)
        except OSError as error:
            raise ProcessingError(MSG_FFMPEG_FAILED_TO_START.format(error=error)) from error
