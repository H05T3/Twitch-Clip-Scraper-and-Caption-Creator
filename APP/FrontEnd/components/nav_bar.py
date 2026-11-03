"""Top navigation bar: three tabs, full-screen button and the dark-mode switch."""
from typing import Callable

import customtkinter as ctk

from APP.BackEnd.ui_config import UiConfig

# Internal keys for the three pages.
PAGE_HOME, PAGE_FETCH, PAGE_GALLERY = "home", "fetch", "gallery"


class NavBar(ctk.CTkFrame):
    """Single responsibility: show the page tabs (Home / Get new clips / See past
    clips), highlight the active one, and expose the full-screen and theme controls.
    It knows nothing about the pages - it only calls the callbacks it is given."""

    def __init__(self, master, ui: UiConfig, on_navigate: Callable, on_fullscreen: Callable,
                 on_theme: Callable, dark_mode: bool):
        super().__init__(master, fg_color=ui.color_nav, corner_radius=0, height=ui.nav_height)
        self.ui = ui
        self._buttons = {}
        self.grid_propagate(False)
        self.pack_propagate(False)

        tabs = ((PAGE_HOME, ui.nav_home), (PAGE_FETCH, ui.nav_fetch), (PAGE_GALLERY, ui.nav_gallery))
        for key, label in tabs:
            button = ctk.CTkButton(
                self, text=label, width=ui.nav_button_width, height=ui.nav_button_height,
                corner_radius=ui.button_corner_radius, font=(ui.font_family, ui.body_font_size, "bold"),
                command=lambda k=key: on_navigate(k))
            button.pack(side="left", padx=(ui.page_padding // 2, 0), pady=(ui.nav_height - ui.nav_button_height) // 2)
            self._buttons[key] = button

        self.theme_switch = ctk.CTkSwitch(
            self, text=ui.nav_dark_mode, font=(ui.font_family, ui.body_font_size),
            text_color=ui.color_text, progress_color=ui.color_accent,
            command=lambda: on_theme(bool(self.theme_switch.get())))
        self.theme_switch.pack(side="right", padx=ui.page_padding)
        if dark_mode:
            self.theme_switch.select()
        ctk.CTkButton(
            self, text=ui.nav_fullscreen, width=ui.nav_button_width // 1.3, height=ui.nav_button_height,
            corner_radius=ui.button_corner_radius, fg_color=ui.color_neutral,
            hover_color=ui.color_neutral_hover, text_color=ui.color_text,
            font=(ui.font_family, ui.body_font_size), command=on_fullscreen,
        ).pack(side="right")
        self.set_active(PAGE_HOME)

    def set_active(self, key: str) -> None:
        """Highlight the tab for the page being shown."""
        ui = self.ui
        for name, button in self._buttons.items():
            active = name == key
            button.configure(
                fg_color=ui.color_accent if active else "transparent",
                hover_color=ui.color_accent_hover if active else ui.color_neutral,
                text_color=ui.color_accent_text if active else ui.color_text)
