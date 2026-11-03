"""Central configuration for the whole app.

RULE: no value is hard-coded anywhere else. Every adjustable value is
declared in DEFAULTS below, can be overridden from the .env file, and is
exposed to the rest of the program through the `Settings` object.

Usage:
    from APP.BackEnd.config import load_settings
    settings = load_settings()
"""
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from APP.BackEnd.env_reader import EnvReader

# ----------------------------------------------------------------------------
# DECLARATIONS - change defaults here, or override any of them in .env
# ----------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE_NAME = ".env"

DEFAULTS = {
    # Folders / files
    "SAVED_CLIPS_DIR": "APP/SavedClips",
    "WORKSPACE_DIR": "APP/Workspace",
    "SETTINGS_FILE": "APP/settings.json",
    "PROMPT_FILE": "APP/Assets/prompts/analysis_prompt.txt",
    # User settings
    "THEME": "dark",
    "CLIP_COUNT": 5,
    "CLIP_LOOKBACK_DAYS": 30,
    "MAX_CLIP_PAGES": 5,
    # Output video
    "OUTPUT_WIDTH": 1080,
    "OUTPUT_HEIGHT": 1920,
    "VIDEO_CRF": 21,
    "VIDEO_PRESET": "veryfast",
    "AUDIO_BITRATE": "160k",
    "BACKGROUND_BLUR": 30,
    "BACKGROUND_DIM": 0.55,
    "VIDEO_Y_OFFSET": 0,
    "VIDEO_CODEC": "libx264",
    "AUDIO_CODEC": "aac",
    "PIXEL_FORMAT": "yuv420p",
    # Title banner
    "TITLE_FONT": "DejaVu Sans",
    "TITLE_FONT_SIZE": 64,
    "TITLE_TEXT_COLOR": "#FFFFFF",
    "TITLE_BANNER_COLOR": "#000000",
    "TITLE_BANNER_OPACITY": 0.75,
    "TITLE_TOP_MARGIN": 140,
    "TITLE_SIDE_MARGIN": 60,
    "TITLE_MAX_CHARS": 60,
    "TITLE_BANNER_PADDING": 22,
    # Subtitles
    "SUBTITLE_FONT": "DejaVu Sans",
    "SUBTITLE_FONT_SIZE": 78,
    "SUBTITLE_TEXT_COLOR": "#FFFFFF",
    "SUBTITLE_HIGHLIGHT_COLOR": "#FFE100",
    "SUBTITLE_OUTLINE_COLOR": "#000000",
    "SUBTITLE_OUTLINE_WIDTH": 6,
    "SUBTITLE_BOTTOM_MARGIN": 420,
    "SUBTITLE_SIDE_MARGIN": 70,
    "SUBTITLE_MAX_WORDS": 4,
    "SUBTITLE_MAX_CHARS": 16,
    "SUBTITLE_MAX_GAP_SECONDS": 0.8,
    "SUBTITLE_UPPERCASE": True,
    # Zoom
    "ZOOM_ENABLED": True,
    "ZOOM_MAX_FACTOR": 1.6,
    "ZOOM_MIN_FACTOR": 1.1,
    "ZOOM_MAX_REGIONS": 3,
    # AI
    "WHISPER_MODEL": "whisper-1",
    "WHISPER_LANGUAGE": "",
    "ANALYSIS_MODEL": "gpt-4o-mini",
    "ANALYSIS_TEMPERATURE": 0.3,
    "AUDIO_FORMAT": "mp3",
    "AUDIO_SAMPLE_RATE": 16000,
    "AUDIO_BITRATE_EXTRACT": "64k",
    "EMPHASIS_MAX_WORDS": 8,
    # Twitch
    "TWITCH_API_BASE": "https://api.twitch.tv/helix",
    "TWITCH_TOKEN_URL": "https://id.twitch.tv/oauth2/token",
    "TWITCH_HOSTS": "twitch.tv,www.twitch.tv,m.twitch.tv",
    "TWITCH_PAGE_SIZE": 100,
    "HTTP_TIMEOUT_SECONDS": 20,
    "DOWNLOAD_QUALITY": "best[height<=1080]/best",
    "ALLOWED_THEMES": "dark,light",
    # Tools
    "FFMPEG_BINARY": "ffmpeg",
    # Saved-clip file naming
    "CLIP_FILE_EXTENSION": ".mp4",
    "METADATA_FILE_EXTENSION": ".json",
}


@dataclass(frozen=True)
class Settings:
    """Single responsibility: hold every configurable value as a typed,
    read-only attribute. Built by `load_settings()`; never edit at runtime
    (user-changeable values like theme are persisted by storage_service)."""

    # Secrets
    openai_api_key: str
    twitch_client_id: str
    twitch_client_secret: str
    # Folders / files
    project_root: Path
    saved_clips_dir: Path
    workspace_dir: Path
    settings_file: Path
    prompt_file: Path
    # User settings
    theme: str
    allowed_themes: tuple
    clip_count: int
    clip_lookback_days: int
    max_clip_pages: int
    # Output video
    output_width: int
    output_height: int
    video_crf: int
    video_preset: str
    audio_bitrate: str
    background_blur: int
    background_dim: float
    video_y_offset: int
    video_codec: str
    audio_codec: str
    pixel_format: str
    # Title
    title_font: str
    title_font_size: int
    title_text_color: str
    title_banner_color: str
    title_banner_opacity: float
    title_top_margin: int
    title_side_margin: int
    title_max_chars: int
    title_banner_padding: int
    # Subtitles
    subtitle_font: str
    subtitle_font_size: int
    subtitle_text_color: str
    subtitle_highlight_color: str
    subtitle_outline_color: str
    subtitle_outline_width: int
    subtitle_bottom_margin: int
    subtitle_side_margin: int
    subtitle_max_words: int
    subtitle_max_chars: int
    subtitle_max_gap_seconds: float
    subtitle_uppercase: bool
    # Zoom
    zoom_enabled: bool
    zoom_max_factor: float
    zoom_min_factor: float
    zoom_max_regions: int
    # AI
    whisper_model: str
    whisper_language: str
    analysis_model: str
    analysis_temperature: float
    audio_format: str
    audio_sample_rate: int
    audio_bitrate_extract: str
    emphasis_max_words: int
    # Twitch
    twitch_api_base: str
    twitch_token_url: str
    twitch_hosts: tuple
    twitch_page_size: int
    http_timeout_seconds: int
    download_quality: str
    # Tools / naming
    ffmpeg_binary: str
    clip_file_extension: str
    metadata_file_extension: str


def _split(csv: str) -> tuple:
    """'a, b' -> ('a', 'b') for list-style settings."""
    return tuple(part.strip().lower() for part in csv.split(",") if part.strip())


def load_settings(env_file: Path = None) -> Settings:
    """Read .env (if present) and build a Settings object from DEFAULTS + overrides."""
    load_dotenv(env_file or (PROJECT_ROOT / ENV_FILE_NAME), override=True)
    e, d = EnvReader(PROJECT_ROOT), DEFAULTS
    return Settings(
        openai_api_key=e.text("OPENAI_API_KEY"),
        twitch_client_id=e.text("TWITCH_CLIENT_ID"),
        twitch_client_secret=e.text("TWITCH_CLIENT_SECRET"),
        project_root=PROJECT_ROOT,
        saved_clips_dir=e.path("SAVED_CLIPS_DIR", d["SAVED_CLIPS_DIR"]),
        workspace_dir=e.path("WORKSPACE_DIR", d["WORKSPACE_DIR"]),
        settings_file=e.path("SETTINGS_FILE", d["SETTINGS_FILE"]),
        prompt_file=e.path("PROMPT_FILE", d["PROMPT_FILE"]),
        theme=e.text("THEME", d["THEME"]).lower(),
        allowed_themes=_split(e.text("ALLOWED_THEMES", d["ALLOWED_THEMES"])),
        clip_count=e.integer("CLIP_COUNT", d["CLIP_COUNT"]),
        clip_lookback_days=e.integer("CLIP_LOOKBACK_DAYS", d["CLIP_LOOKBACK_DAYS"]),
        max_clip_pages=e.integer("MAX_CLIP_PAGES", d["MAX_CLIP_PAGES"]),
        output_width=e.integer("OUTPUT_WIDTH", d["OUTPUT_WIDTH"]),
        output_height=e.integer("OUTPUT_HEIGHT", d["OUTPUT_HEIGHT"]),
        video_crf=e.integer("VIDEO_CRF", d["VIDEO_CRF"]),
        video_preset=e.text("VIDEO_PRESET", d["VIDEO_PRESET"]),
        audio_bitrate=e.text("AUDIO_BITRATE", d["AUDIO_BITRATE"]),
        background_blur=e.integer("BACKGROUND_BLUR", d["BACKGROUND_BLUR"]),
        background_dim=e.number("BACKGROUND_DIM", d["BACKGROUND_DIM"]),
        video_y_offset=e.integer("VIDEO_Y_OFFSET", d["VIDEO_Y_OFFSET"]),
        video_codec=e.text("VIDEO_CODEC", d["VIDEO_CODEC"]),
        audio_codec=e.text("AUDIO_CODEC", d["AUDIO_CODEC"]),
        pixel_format=e.text("PIXEL_FORMAT", d["PIXEL_FORMAT"]),
        title_font=e.text("TITLE_FONT", d["TITLE_FONT"]),
        title_font_size=e.integer("TITLE_FONT_SIZE", d["TITLE_FONT_SIZE"]),
        title_text_color=e.text("TITLE_TEXT_COLOR", d["TITLE_TEXT_COLOR"]),
        title_banner_color=e.text("TITLE_BANNER_COLOR", d["TITLE_BANNER_COLOR"]),
        title_banner_opacity=e.number("TITLE_BANNER_OPACITY", d["TITLE_BANNER_OPACITY"]),
        title_top_margin=e.integer("TITLE_TOP_MARGIN", d["TITLE_TOP_MARGIN"]),
        title_side_margin=e.integer("TITLE_SIDE_MARGIN", d["TITLE_SIDE_MARGIN"]),
        title_max_chars=e.integer("TITLE_MAX_CHARS", d["TITLE_MAX_CHARS"]),
        title_banner_padding=e.integer("TITLE_BANNER_PADDING", d["TITLE_BANNER_PADDING"]),
        subtitle_font=e.text("SUBTITLE_FONT", d["SUBTITLE_FONT"]),
        subtitle_font_size=e.integer("SUBTITLE_FONT_SIZE", d["SUBTITLE_FONT_SIZE"]),
        subtitle_text_color=e.text("SUBTITLE_TEXT_COLOR", d["SUBTITLE_TEXT_COLOR"]),
        subtitle_highlight_color=e.text("SUBTITLE_HIGHLIGHT_COLOR", d["SUBTITLE_HIGHLIGHT_COLOR"]),
        subtitle_outline_color=e.text("SUBTITLE_OUTLINE_COLOR", d["SUBTITLE_OUTLINE_COLOR"]),
        subtitle_outline_width=e.integer("SUBTITLE_OUTLINE_WIDTH", d["SUBTITLE_OUTLINE_WIDTH"]),
        subtitle_bottom_margin=e.integer("SUBTITLE_BOTTOM_MARGIN", d["SUBTITLE_BOTTOM_MARGIN"]),
        subtitle_side_margin=e.integer("SUBTITLE_SIDE_MARGIN", d["SUBTITLE_SIDE_MARGIN"]),
        subtitle_max_words=e.integer("SUBTITLE_MAX_WORDS", d["SUBTITLE_MAX_WORDS"]),
        subtitle_max_chars=e.integer("SUBTITLE_MAX_CHARS", d["SUBTITLE_MAX_CHARS"]),
        subtitle_max_gap_seconds=e.number("SUBTITLE_MAX_GAP_SECONDS", d["SUBTITLE_MAX_GAP_SECONDS"]),
        subtitle_uppercase=e.boolean("SUBTITLE_UPPERCASE", d["SUBTITLE_UPPERCASE"]),
        zoom_enabled=e.boolean("ZOOM_ENABLED", d["ZOOM_ENABLED"]),
        zoom_max_factor=e.number("ZOOM_MAX_FACTOR", d["ZOOM_MAX_FACTOR"]),
        zoom_min_factor=e.number("ZOOM_MIN_FACTOR", d["ZOOM_MIN_FACTOR"]),
        zoom_max_regions=e.integer("ZOOM_MAX_REGIONS", d["ZOOM_MAX_REGIONS"]),
        whisper_model=e.text("WHISPER_MODEL", d["WHISPER_MODEL"]),
        whisper_language=e.text("WHISPER_LANGUAGE", d["WHISPER_LANGUAGE"]),
        analysis_model=e.text("ANALYSIS_MODEL", d["ANALYSIS_MODEL"]),
        analysis_temperature=e.number("ANALYSIS_TEMPERATURE", d["ANALYSIS_TEMPERATURE"]),
        audio_format=e.text("AUDIO_FORMAT", d["AUDIO_FORMAT"]),
        audio_sample_rate=e.integer("AUDIO_SAMPLE_RATE", d["AUDIO_SAMPLE_RATE"]),
        audio_bitrate_extract=e.text("AUDIO_BITRATE_EXTRACT", d["AUDIO_BITRATE_EXTRACT"]),
        emphasis_max_words=e.integer("EMPHASIS_MAX_WORDS", d["EMPHASIS_MAX_WORDS"]),
        twitch_api_base=e.text("TWITCH_API_BASE", d["TWITCH_API_BASE"]),
        twitch_token_url=e.text("TWITCH_TOKEN_URL", d["TWITCH_TOKEN_URL"]),
        twitch_hosts=_split(e.text("TWITCH_HOSTS", d["TWITCH_HOSTS"])),
        twitch_page_size=e.integer("TWITCH_PAGE_SIZE", d["TWITCH_PAGE_SIZE"]),
        http_timeout_seconds=e.integer("HTTP_TIMEOUT_SECONDS", d["HTTP_TIMEOUT_SECONDS"]),
        download_quality=e.text("DOWNLOAD_QUALITY", d["DOWNLOAD_QUALITY"]),
        ffmpeg_binary=e.text("FFMPEG_BINARY", d["FFMPEG_BINARY"]),
        clip_file_extension=e.text("CLIP_FILE_EXTENSION", d["CLIP_FILE_EXTENSION"]),
        metadata_file_extension=e.text("METADATA_FILE_EXTENSION", d["METADATA_FILE_EXTENSION"]),
    )
