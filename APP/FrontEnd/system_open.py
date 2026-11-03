"""Open a file or folder with the operating system's default app."""
import os
import subprocess
import sys

# Command used per platform (Windows uses os.startfile instead).
MAC_OPEN_COMMAND = "open"
LINUX_OPEN_COMMAND = "xdg-open"
WINDOWS_PLATFORM_PREFIX = "win"
MAC_PLATFORM_PREFIX = "darwin"


def open_path(path) -> None:
    """Open `path` (video or folder) in the default viewer. Failures are ignored on
    purpose: a missing viewer should never crash the app."""
    path = str(path)
    try:
        if sys.platform.startswith(WINDOWS_PLATFORM_PREFIX):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform.startswith(MAC_PLATFORM_PREFIX):
            subprocess.Popen([MAC_OPEN_COMMAND, path])
        else:
            subprocess.Popen([LINUX_OPEN_COMMAND, path])
    except OSError:
        pass
