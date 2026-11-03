"""Audio extraction, OpenAI Whisper transcription and GPT clip analysis."""
import json
import subprocess
from pathlib import Path

from APP.BackEnd.analysis_models import ClipAnalysis, ZoomRegion
from APP.BackEnd.config import Settings
from APP.BackEnd.errors import ProcessingError
from APP.BackEnd.models import ClipInfo, WordTiming
from APP.BackEnd.subtitle_builder import SubtitleLineBuilder

# Placeholders in the prompt file that are replaced with values from Settings.
PROMPT_PLACEHOLDERS = ("{title_max_chars}", "{zoom_max_regions}", "{zoom_max_factor}")
# Decimal places for timestamps sent to GPT (keeps the prompt small).
TIMESTAMP_PRECISION = 2
# Characters stripped from words when matching emphasis words.
WORD_STRIP_CHARS = ".,!?\"'()[]:;"


def _field(item, name, default=None):
    """Read `name` from an SDK object or a plain dict."""
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


class AudioExtractor:
    """Single responsibility: pull the audio track out of a video file with ffmpeg
    (mono, low bitrate - small enough for the Whisper upload limit)."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def extract(self, video_path: Path, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        audio_path = output_dir / f"{video_path.stem}.{self.settings.audio_format}"
        command = [
            self.settings.ffmpeg_binary, "-y", "-i", str(video_path), "-vn", "-ac", "1",
            "-ar", str(self.settings.audio_sample_rate),
            "-b:a", self.settings.audio_bitrate_extract, str(audio_path),
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise ProcessingError(f"Audio extraction failed: {result.stderr[-500:]}")
        return audio_path


class WhisperTranscriber:
    """Single responsibility: send an audio file to OpenAI Whisper and return
    (full_text, list[WordTiming]) with word-level timestamps."""

    def __init__(self, settings: Settings, client=None):
        self.settings = settings
        self._client = client  # injectable for tests

    def _get_client(self):
        if self._client is None:
            if not self.settings.openai_api_key:
                raise ProcessingError("OPENAI_API_KEY is missing. Add it to your .env file.")
            from openai import OpenAI
            self._client = OpenAI(api_key=self.settings.openai_api_key)
        return self._client

    def transcribe(self, audio_path: Path):
        params = {
            "model": self.settings.whisper_model,
            "response_format": "verbose_json",
            "timestamp_granularities": ["word"],
        }
        if self.settings.whisper_language:
            params["language"] = self.settings.whisper_language
        try:
            with open(audio_path, "rb") as audio_file:
                response = self._get_client().audio.transcriptions.create(file=audio_file, **params)
        except ProcessingError:
            raise
        except Exception as error:
            raise ProcessingError(f"Whisper transcription failed: {error}") from error
        words = [
            WordTiming(text=str(_field(w, "word", "")).strip(),
                       start=float(_field(w, "start", 0.0)),
                       end=float(_field(w, "end", 0.0)))
            for w in (_field(response, "words", None) or [])
        ]
        return str(_field(response, "text", "") or "").strip(), words


class ClipAnalyzer:
    """Single responsibility: ask GPT (using the prompt file) for the title,
    emphasis words and zoom moments, validate the answer, and combine it with
    subtitle lines built from the Whisper word timings into a ClipAnalysis."""

    def __init__(self, settings: Settings, client=None, line_builder: SubtitleLineBuilder = None):
        self.settings = settings
        self._client = client
        self.line_builder = line_builder or SubtitleLineBuilder(settings)

    def _get_client(self):
        if self._client is None:
            if not self.settings.openai_api_key:
                raise ProcessingError("OPENAI_API_KEY is missing. Add it to your .env file.")
            from openai import OpenAI
            self._client = OpenAI(api_key=self.settings.openai_api_key)
        return self._client

    def _system_prompt(self) -> str:
        try:
            prompt = self.settings.prompt_file.read_text(encoding="utf-8")
        except OSError as error:
            raise ProcessingError(f"Could not read prompt file: {error}") from error
        values = (self.settings.title_max_chars, self.settings.zoom_max_regions, self.settings.zoom_max_factor)
        for placeholder, value in zip(PROMPT_PLACEHOLDERS, values):
            prompt = prompt.replace(placeholder, str(value))
        return prompt

    def _user_message(self, clip: ClipInfo, text: str, words: list) -> str:
        return json.dumps({
            "clip_title": clip.title,
            "streamer": clip.broadcaster_name,
            "duration_seconds": clip.duration,
            "transcript": text,
            "words": [[round(w.start, TIMESTAMP_PRECISION), w.text] for w in words],
        })

    def analyze(self, clip: ClipInfo, text: str, words: list) -> ClipAnalysis:
        try:
            response = self._get_client().chat.completions.create(
                model=self.settings.analysis_model,
                temperature=self.settings.analysis_temperature,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": self._system_prompt()},
                    {"role": "user", "content": self._user_message(clip, text, words)},
                ],
            )
            data = json.loads(response.choices[0].message.content)
        except ProcessingError:
            raise
        except Exception as error:
            raise ProcessingError(f"Clip analysis failed: {error}") from error
        return self._build_analysis(clip, text, words, data if isinstance(data, dict) else {})

    def _build_analysis(self, clip: ClipInfo, text: str, words: list, data: dict) -> ClipAnalysis:
        """Validate/clamp the model's JSON so bad values can never break rendering."""
        s = self.settings
        title = str(data.get("title") or clip.title).strip()[: s.title_max_chars]
        emphasis = [str(w).lower().strip(WORD_STRIP_CHARS) for w in data.get("emphasis_words", [])]
        regions = []
        if s.zoom_enabled:
            for raw in data.get("zoom_regions", [])[: s.zoom_max_regions]:
                try:
                    start, end = float(raw["start"]), float(raw["end"])
                    if clip.duration:
                        end = min(end, clip.duration)
                    if start < 0 or end <= start:
                        continue
                    regions.append(ZoomRegion(
                        start=start, end=end,
                        focus_x=min(max(float(raw.get("focus_x", 0.5)), 0.0), 1.0),
                        focus_y=min(max(float(raw.get("focus_y", 0.5)), 0.0), 1.0),
                        zoom=min(max(float(raw.get("zoom", s.zoom_min_factor)), s.zoom_min_factor), s.zoom_max_factor),
                        reason=str(raw.get("reason", "")),
                    ))
                except (KeyError, TypeError, ValueError):
                    continue
        return ClipAnalysis(
            title=title or clip.title,
            summary=str(data.get("summary", "")),
            subtitle_lines=self.line_builder.build(words),
            emphasis_words=[w for w in emphasis if w][: s.emphasis_max_words],
            zoom_regions=regions,
            hashtags=[str(h).lstrip("#") for h in data.get("hashtags", [])],
            transcript=text,
        )
