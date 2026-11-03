"""Twitch integration: parse a channel URL, list recent clips (Helix API), download them.

Needs TWITCH_CLIENT_ID / TWITCH_CLIENT_SECRET in .env (free at dev.twitch.tv/console).
"""
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

from APP.BackEnd.config import Settings
from APP.BackEnd.errors import TwitchServiceError
from APP.BackEnd.models import ClipInfo

# Twitch login names: 4-25 chars of letters, digits, underscore (we allow 1+ to be lenient).
CHANNEL_NAME_PATTERN = r"^[A-Za-z0-9_]{1,25}$"
# Seconds of safety margin before a cached app token expires.
TOKEN_EXPIRY_MARGIN_SECONDS = 60
# Helix timestamp format.
HELIX_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
# Characters that are unsafe in file names.
UNSAFE_FILENAME_CHARS = r"[^A-Za-z0-9_-]"


class ChannelUrlParser:
    """Single responsibility: turn whatever the user typed (a full URL such as
    https://www.twitch.tv/somestreamer/clips, or just 'somestreamer') into a
    clean lowercase channel login name."""

    # Path segments on twitch.tv that are not channel names.
    RESERVED_SEGMENTS = {"directory", "videos", "settings", "downloads", "p", "login"}

    def __init__(self, settings: Settings):
        self.settings = settings

    def parse(self, text: str) -> str:
        text = (text or "").strip()
        if not text:
            raise TwitchServiceError("Please enter a Twitch channel link or name.")
        if "/" in text or "." in text:
            if "://" not in text:
                text = "https://" + text
            parsed = urlparse(text)
            host = (parsed.hostname or "").lower()
            if host not in self.settings.twitch_hosts:
                raise TwitchServiceError(f"'{host}' is not a Twitch link.")
            segments = [s for s in parsed.path.split("/") if s]
            if not segments or segments[0].lower() in self.RESERVED_SEGMENTS:
                raise TwitchServiceError("Could not find a channel name in that link.")
            name = segments[0]
        else:
            name = text
        if not re.match(CHANNEL_NAME_PATTERN, name):
            raise TwitchServiceError(f"'{name}' is not a valid Twitch channel name.")
        return name.lower()


class TwitchApiClient:
    """Single responsibility: authenticate with Twitch (app access token) and
    fetch channel + clip metadata from the Helix API.

    NOTE: Helix returns clips ordered by VIEWS, not date. To get the *most
    recent* clips we request a lookback window, page through it, and sort by
    created_at ourselves."""

    def __init__(self, settings: Settings, session: requests.Session = None):
        self.settings = settings
        self.session = session or requests.Session()
        self._token = None
        self._token_expires_at = 0.0

    def _auth_headers(self) -> dict:
        if not self.settings.twitch_client_id or not self.settings.twitch_client_secret:
            raise TwitchServiceError(
                "Twitch credentials missing. Set TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET in .env."
            )
        if not self._token or time.time() >= self._token_expires_at:
            response = self.session.post(
                self.settings.twitch_token_url,
                data={
                    "client_id": self.settings.twitch_client_id,
                    "client_secret": self.settings.twitch_client_secret,
                    "grant_type": "client_credentials",
                },
                timeout=self.settings.http_timeout_seconds,
            )
            if response.status_code != 200:
                raise TwitchServiceError(f"Twitch login failed ({response.status_code}). Check your Client ID/Secret.")
            body = response.json()
            self._token = body["access_token"]
            self._token_expires_at = time.time() + body.get("expires_in", 0) - TOKEN_EXPIRY_MARGIN_SECONDS
        return {"Client-Id": self.settings.twitch_client_id, "Authorization": f"Bearer {self._token}"}

    def _get(self, endpoint: str, params: dict) -> dict:
        try:
            response = self.session.get(
                f"{self.settings.twitch_api_base}/{endpoint}",
                headers=self._auth_headers(),
                params=params,
                timeout=self.settings.http_timeout_seconds,
            )
        except requests.RequestException as error:
            raise TwitchServiceError(f"Could not reach Twitch: {error}") from error
        if response.status_code != 200:
            raise TwitchServiceError(f"Twitch API error {response.status_code} on '{endpoint}'.")
        return response.json()

    def get_broadcaster_id(self, login: str) -> str:
        data = self._get("users", {"login": login}).get("data", [])
        if not data:
            raise TwitchServiceError(f"Twitch channel '{login}' was not found.")
        return data[0]["id"]

    def get_recent_clips(self, broadcaster_id: str) -> list:
        """Return up to settings.clip_count ClipInfo objects, newest first."""
        now = datetime.now(timezone.utc)
        started_at = (now - timedelta(days=self.settings.clip_lookback_days)).strftime(HELIX_TIME_FORMAT)
        ended_at = now.strftime(HELIX_TIME_FORMAT)
        params = {
            "broadcaster_id": broadcaster_id,
            "first": self.settings.twitch_page_size,
            "started_at": started_at,
            "ended_at": ended_at,
        }
        raw_clips = []
        for _ in range(self.settings.max_clip_pages):
            body = self._get("clips", params)
            raw_clips.extend(body.get("data", []))
            cursor = body.get("pagination", {}).get("cursor")
            if not cursor:
                break
            params["after"] = cursor
        raw_clips.sort(key=lambda clip: clip["created_at"], reverse=True)
        return [self._to_clip_info(raw) for raw in raw_clips[: self.settings.clip_count]]

    @staticmethod
    def _to_clip_info(raw: dict) -> ClipInfo:
        return ClipInfo(
            clip_id=raw["id"],
            url=raw["url"],
            title=raw.get("title", ""),
            broadcaster_name=raw.get("broadcaster_name", ""),
            creator_name=raw.get("creator_name", ""),
            created_at=raw.get("created_at", ""),
            duration=float(raw.get("duration", 0)),
            view_count=int(raw.get("view_count", 0)),
            thumbnail_url=raw.get("thumbnail_url", ""),
        )


class ClipDownloader:
    """Single responsibility: download a clip's source MP4 into the workspace
    folder using yt-dlp (which knows how to resolve Twitch clip URLs)."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def download(self, clip: ClipInfo, target_dir: Path) -> Path:
        """Download `clip` into `target_dir` and set/return clip.source_path."""
        import yt_dlp  # imported lazily so the rest of the app works without it

        target_dir.mkdir(parents=True, exist_ok=True)
        safe_id = re.sub(UNSAFE_FILENAME_CHARS, "_", clip.clip_id)
        output_template = str(target_dir / f"{safe_id}.%(ext)s")
        options = {
            "format": self.settings.download_quality,
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "merge_output_format": self.settings.clip_file_extension.lstrip("."),
        }
        try:
            with yt_dlp.YoutubeDL(options) as downloader:
                downloader.download([clip.url])
        except Exception as error:  # yt-dlp raises many error types
            raise TwitchServiceError(f"Could not download clip '{clip.title}': {error}") from error
        matches = sorted(target_dir.glob(f"{safe_id}.*"))
        if not matches:
            raise TwitchServiceError(f"Download finished but no file was found for clip '{clip.title}'.")
        clip.source_path = matches[0]
        return clip.source_path
