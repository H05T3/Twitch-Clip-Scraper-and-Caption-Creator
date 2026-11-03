"""A card holding one video, its title and action buttons."""
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import customtkinter as ctk

from APP.BackEnd.ui_config import UiConfig
from APP.FrontEnd.components.video_player import VideoPlayer
from APP.FrontEnd.system_open import open_path

# Button styles an action can ask for.
KIND_PRIMARY, KIND_DANGER, KIND_NEUTRAL = "primary", "danger", "neutral"


@dataclass
class CardAction:
    """Purpose: describes one button on a card (id, label, look, what it does)."""

    key: str
    label: str
    kind: str
    callback: Callable  # called with the card as its only argument


class VideoCard(ctk.CTkFrame):
    """Single responsibility: display a video player + title (+ hashtags) with a row of
    buttons supplied by the page that owns it (Save/Discard in 'Get new clips',
    Delete in 'See past clips'). Also offers 'Open with sound' because the built-in
    player is silent."""

    def __init__(self, master, ui: UiConfig, title: str, video_path, actions: list,
                 subtitle: str = "", data=None):
        super().__init__(master, fg_color=ui.color_surface, corner_radius=ui.card_corner_radius,
                         border_width=1, border_color=ui.color_border, width=ui.card_width)
        self.ui, self.data, self.video_path = ui, data, Path(video_path)
        self.buttons = {}
        pad = ui.card_padding

        shown = title if len(title) <= ui.card_title_max_chars else title[: ui.card_title_max_chars - 1] + "…"
        ctk.CTkLabel(self, text=shown, wraplength=ui.card_title_wrap, justify="left", anchor="w",
                     text_color=ui.color_text, font=(ui.font_family, ui.card_title_font_size, "bold")
                     ).pack(fill="x", padx=pad, pady=(pad, pad // 2))
        VideoPlayer(self, ui, video_path).pack(padx=pad)
        if subtitle:
            ctk.CTkLabel(self, text=subtitle, wraplength=ui.card_title_wrap, justify="left", anchor="w",
                         text_color=ui.color_muted, font=(ui.font_family, ui.card_meta_font_size)
                         ).pack(fill="x", padx=pad, pady=(pad // 2, 0))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=pad, pady=(pad, pad // 2))
        for action in actions:
            fg, hover, text = {
                KIND_PRIMARY: (ui.color_accent, ui.color_accent_hover, ui.color_accent_text),
                KIND_DANGER: (ui.color_danger, ui.color_danger_hover, ui.color_accent_text),
            }.get(action.kind, (ui.color_neutral, ui.color_neutral_hover, ui.color_text))
            button = ctk.CTkButton(
                row, text=action.label, width=ui.player_button_width, fg_color=fg, hover_color=hover, text_color=text,
                corner_radius=ui.button_corner_radius, font=(ui.font_family, ui.body_font_size, "bold"),
                command=lambda a=action: a.callback(self))
            button.pack(side="left", expand=True, fill="x", padx=(0, pad // 2))
            self.buttons[action.key] = button
        ctk.CTkButton(
            self, text=ui.action_open_external, width=ui.player_button_width, fg_color="transparent", hover_color=ui.color_neutral,
            text_color=ui.color_muted, height=ui.nav_button_height - 8,
            font=(ui.font_family, ui.card_meta_font_size), command=lambda: open_path(self.video_path)
        ).pack(fill="x", padx=pad, pady=(0, pad))

    def mark_done(self, key: str, label: str) -> None:
        """Turn a button into a disabled 'done' label (e.g. Save -> Saved)."""
        self.buttons[key].configure(text=label, state="disabled", fg_color=self.ui.color_success)
