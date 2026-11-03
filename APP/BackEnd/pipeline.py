"""The orchestrator the front end talks to: channel link in -> finished portrait clips out."""
import shutil
from pathlib import Path
from typing import Callable, Optional

from APP.BackEnd.analysis_models import ProcessedClip
from APP.BackEnd.config import Settings, load_settings
from APP.BackEnd.errors import ClipperError
from APP.BackEnd.storage_service import ClipLibrary, KEY_CLIPS_CREATED, SettingsStore
from APP.BackEnd.transcription_service import AudioExtractor, ClipAnalyzer, WhisperTranscriber
from APP.BackEnd.twitch_service import ChannelUrlParser, ClipDownloader, TwitchApiClient
from APP.BackEnd.video_processor import VideoProcessor

# Sub-folder names inside the workspace for each clip's temporary files.
PREVIEW_FOLDER_NAME = "previews"
SOURCE_FOLDER_NAME = "sources"
AUDIO_FOLDER_NAME = "audio"
# Suffix added to the rendered preview file name.
PREVIEW_SUFFIX = "_portrait"
# Progress messages (kept here, not inline, so the UI/CLI text is easy to change).
MSG_LOOKUP = "Looking up channel '{channel}'..."
MSG_CLIPS_FOUND = "Found {count} clip(s)."
MSG_DOWNLOAD = "[{n}/{total}] Downloading '{title}'..."
MSG_TRANSCRIBE = "[{n}/{total}] Transcribing..."
MSG_ANALYZE = "[{n}/{total}] Analyzing (title, zoom moments)..."
MSG_RENDER = "[{n}/{total}] Rendering portrait video..."
MSG_FAILED = "[{n}/{total}] Skipped '{title}': {error}"
MSG_NO_CLIPS = "No clips found for '{channel}' in the last {days} days."

ProgressCallback = Callable[[str], None]


class ClipPipeline:
    """Single responsibility: wire the services together. The front end only needs:
        fetch_and_process(url, progress, on_clip) -> (list[ProcessedClip], list[error strings])
        save(clip) / discard(clip)        -> keep or throw away a preview
        library / store                    -> saved clips list, stats, theme"""

    def __init__(self, settings: Settings = None, **services):
        self.settings = settings or load_settings()
        s = self.settings
        # Services can be replaced (e.g. by fakes in tests) via keyword arguments.
        self.parser = services.get("parser") or ChannelUrlParser(s)
        self.twitch = services.get("twitch") or TwitchApiClient(s)
        self.downloader = services.get("downloader") or ClipDownloader(s)
        self.audio = services.get("audio") or AudioExtractor(s)
        self.transcriber = services.get("transcriber") or WhisperTranscriber(s)
        self.analyzer = services.get("analyzer") or ClipAnalyzer(s)
        self.renderer = services.get("renderer") or VideoProcessor(s)
        self.store = services.get("store") or SettingsStore(s)
        self.library = services.get("library") or ClipLibrary(s, self.store)

    def fetch_and_process(self, channel_input: str, progress: Optional[ProgressCallback] = None,
                          on_clip: Optional[Callable[[ProcessedClip], None]] = None):
        say = progress or (lambda message: None)
        s = self.settings
        channel = self.parser.parse(channel_input)
        say(MSG_LOOKUP.format(channel=channel))
        clips = self.twitch.get_recent_clips(self.twitch.get_broadcaster_id(channel))
        if not clips:
            raise ClipperError(MSG_NO_CLIPS.format(channel=channel, days=s.clip_lookback_days))
        say(MSG_CLIPS_FOUND.format(count=len(clips)))

        work = s.workspace_dir / channel
        results, errors = [], []
        for number, clip in enumerate(clips, start=1):
            info = {"n": number, "total": len(clips), "title": clip.title}
            try:
                say(MSG_DOWNLOAD.format(**info))
                source = self.downloader.download(clip, work / SOURCE_FOLDER_NAME)
                say(MSG_TRANSCRIBE.format(**info))
                audio_path = self.audio.extract(source, work / AUDIO_FOLDER_NAME)
                text, words = self.transcriber.transcribe(audio_path)
                say(MSG_ANALYZE.format(**info))
                analysis = self.analyzer.analyze(clip, text, words)
                say(MSG_RENDER.format(**info))
                output = work / PREVIEW_FOLDER_NAME / f"{clip.clip_id}{PREVIEW_SUFFIX}{s.clip_file_extension}"
                self.renderer.render(source, analysis, output)
                self.store.increment(KEY_CLIPS_CREATED)
                processed = ProcessedClip(
                    clip_id=clip.clip_id, title=analysis.title, video_path=output,
                    summary=analysis.summary, hashtags=analysis.hashtags,
                    source_url=clip.url, broadcaster_name=clip.broadcaster_name)
                results.append(processed)
                if on_clip:  # lets the UI show each card as soon as it is ready
                    on_clip(processed)
            except ClipperError as error:  # one bad clip shouldn't stop the others
                message = MSG_FAILED.format(error=error, **info)
                errors.append(message)
                say(message)
        return results, errors

    def save(self, clip: ProcessedClip) -> Path:
        """User pressed 'Save': copy into SavedClips. The temporary preview is kept
        (the UI player may still have it open); clear_workspace() removes it later."""
        return self.library.save(clip)

    def discard(self, clip: ProcessedClip) -> None:
        """User pressed 'Discard': delete the temporary preview (the UI must close its
        player first)."""
        try:
            Path(clip.video_path).unlink(missing_ok=True)
        except OSError:
            pass  # still locked by a player; clear_workspace() will remove it later

    def clear_workspace(self) -> None:
        """Remove all temporary downloads/previews."""
        shutil.rmtree(self.settings.workspace_dir, ignore_errors=True)
