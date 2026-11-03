"""All front-end text, sizes, timings and colours in one place.

RULE: no UI file contains a literal string, size or colour. To change how the app
looks or reads, edit the values below. Colours are (light_mode, dark_mode) pairs.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class UiConfig:
    """Purpose: the single, read-only source of truth for everything visual in
    the front end (window, nav bar, views, cards, player, colours, wording)."""

    # ---- Window ----
    window_title: str = "Twitch Clip Shorts"
    window_width: int = 1180
    window_height: int = 800
    window_min_width: int = 820
    window_min_height: int = 600
    fullscreen_key: str = "<F11>"
    exit_fullscreen_key: str = "<Escape>"

    # ---- Navigation ----
    nav_home: str = "Home"
    nav_fetch: str = "Get new clips"
    nav_gallery: str = "See past clips"
    nav_fullscreen: str = "Full screen"
    nav_dark_mode: str = "Dark mode"
    nav_height: int = 56
    nav_button_width: int = 150
    nav_button_height: int = 36

    # ---- Home ----
    home_welcome: str = "Welcome User"
    home_subtitle: str = "Turn Twitch clips into vertical shorts in a few clicks."
    home_welcome_font_size: int = 44
    home_stats_title: str = "Your stats"
    home_stat_created: str = "Clips created"
    home_stat_saved: str = "Clips saved"
    home_stat_folder: str = "Saved to"
    home_open_folder: str = "Open folder"
    glow_layers: int = 7
    glow_step_padding: int = 5
    glow_corner_radius: int = 40

    # ---- Get new clips ----
    fetch_title: str = "Get new clips"
    fetch_hint: str = "Paste a link to a Twitch streamer's page"
    fetch_placeholder: str = "https://www.twitch.tv/streamer"
    fetch_button: str = "Fetch & Process"
    fetch_busy_button: str = "Working..."
    fetch_entry_start_width: int = 60
    fetch_entry_end_width: int = 620
    fetch_entry_height: int = 46
    fetch_animation_ms: int = 450
    fetch_animation_step_ms: int = 15
    fetch_empty: str = "Your clips will appear here."
    fetch_done: str = "Done: {count} clip(s) ready to review."
    fetch_done_with_errors: str = "Done: {count} ready, {failed} skipped."
    fetch_error_prefix: str = "Error: "
    fetch_poll_ms: int = 100

    # ---- Past clips ----
    gallery_title: str = "Saved clips"
    gallery_empty: str = "No saved clips yet. Fetch some and press Save."
    gallery_count: str = "{count} saved clip(s)"
    gallery_delete_confirm_title: str = "Delete clip"
    gallery_delete_confirm: str = "Delete '{title}' permanently?"

    # ---- Cards / player ----
    card_width: int = 244
    card_gap: int = 16
    card_corner_radius: int = 16
    card_padding: int = 12
    card_title_font_size: int = 15
    card_title_wrap: int = 210
    card_title_max_chars: int = 70
    card_meta_font_size: int = 12
    video_aspect_width: int = 9
    video_aspect_height: int = 16
    player_width: int = 212
    player_play: str = "Play"
    player_pause: str = "Pause"
    player_error: str = "Cannot play this video"
    player_button_width: int = 70
    player_default_fps: float = 30.0
    action_save: str = "Save"
    action_saved: str = "Saved"
    action_discard: str = "Discard"
    action_delete: str = "Delete"
    action_open_external: str = "Open with sound"
    resize_debounce_ms: int = 120

    # ---- Fonts / spacing ----
    font_family: str = "Segoe UI"
    page_padding: int = 24
    heading_font_size: int = 28
    body_font_size: int = 14
    stat_value_font_size: int = 34
    corner_radius: int = 12
    button_corner_radius: int = 10

    # ---- Colours: (light, dark) ----
    color_bg: tuple = ("#F2F4F8", "#0E1117")
    color_surface: tuple = ("#FFFFFF", "#171B24")
    color_nav: tuple = ("#FFFFFF", "#12151C")
    color_text: tuple = ("#111827", "#E8ECF3")
    color_muted: tuple = ("#6B7280", "#9AA4B5")
    color_border: tuple = ("#D5DAE3", "#2A3140")
    color_accent: tuple = ("#2F6FED", "#3B82F6")
    color_accent_hover: tuple = ("#2559C4", "#2563EB")
    color_accent_text: tuple = ("#FFFFFF", "#FFFFFF")
    color_danger: tuple = ("#DC2626", "#EF4444")
    color_danger_hover: tuple = ("#B91C1C", "#DC2626")
    color_success: tuple = ("#16A34A", "#22C55E")
    color_neutral: tuple = ("#E3E7EE", "#252B38")
    color_neutral_hover: tuple = ("#D3D9E3", "#313949")
    color_video_bg: tuple = ("#000000", "#000000")
    glow_color: tuple = ("#5AA2FF", "#3B82F6")
    glow_strength: float = 0.55  # 0..1, how strongly the glow colour shows at its brightest ring
