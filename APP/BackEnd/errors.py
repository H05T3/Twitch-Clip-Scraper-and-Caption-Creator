"""Exception types shared by the backend, so the UI can show friendly messages."""


class ClipperError(Exception):
    """Base class for every error this app raises on purpose.
    The front end can catch just this type and display str(error)."""


class TwitchServiceError(ClipperError):
    """Raised when talking to Twitch fails (bad URL, auth, no clips, download)."""


class ProcessingError(ClipperError):
    """Raised when audio extraction, OpenAI calls or video rendering fail."""
