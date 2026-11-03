"""Runs slow backend work on a thread so the window never freezes."""
import queue
import threading
from typing import Callable

# Message kinds sent from the worker thread to the UI thread.
KIND_PROGRESS, KIND_CLIP, KIND_DONE, KIND_ERROR = "progress", "clip", "done", "error"


class BackgroundTask:
    """Single responsibility: run `work(emit)` on a daemon thread and let the UI
    thread collect its messages safely via `drain()` (call it from tk's after()).
    The worker calls emit(kind, payload); the UI never touches the worker's data directly."""

    def __init__(self, work: Callable):
        self._queue = queue.Queue()
        self._thread = threading.Thread(target=self._run, args=(work,), daemon=True)

    def start(self) -> None:
        self._thread.start()

    def _run(self, work: Callable) -> None:
        try:
            work(lambda kind, payload=None: self._queue.put((kind, payload)))
        except Exception as error:  # surface *any* failure to the UI instead of dying silently
            self._queue.put((KIND_ERROR, str(error) or error.__class__.__name__))

    def drain(self) -> list:
        """Return all messages received since the last call."""
        messages = []
        while True:
            try:
                messages.append(self._queue.get_nowait())
            except queue.Empty:
                return messages
