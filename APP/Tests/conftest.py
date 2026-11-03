"""Shared test fixtures: isolated Settings that point at a temp folder."""
import dataclasses
import pytest
from APP.BackEnd.config import load_settings


@pytest.fixture
def settings(tmp_path):
    base = load_settings()
    return dataclasses.replace(
        base, saved_clips_dir=tmp_path / "saved", workspace_dir=tmp_path / "work",
        settings_file=tmp_path / "settings.json", twitch_client_id="id", twitch_client_secret="secret",
        openai_api_key="key")
