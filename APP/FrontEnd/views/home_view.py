"""Home page: glowing welcome banner and the user's stats."""
import customtkinter as ctk

from APP.BackEnd.pipeline import ClipPipeline
from APP.BackEnd.ui_config import UiConfig
from APP.FrontEnd.components.glow_frame import GlowFrame
from APP.FrontEnd.system_open import open_path


class HomeView(ctk.CTkFrame):
    """Single responsibility: the first page the user sees. Shows 'Welcome User' inside
    a blue glow, how many clips were created/saved, and where they are stored."""

    def __init__(self, master, ui: UiConfig, pipeline: ClipPipeline):
        super().__init__(master, fg_color="transparent")
        self.ui, self.pipeline = ui, pipeline
        pad = ui.page_padding

        glow = GlowFrame(self, ui)
        glow.pack(pady=(pad * 2, pad), padx=pad)
        ctk.CTkLabel(glow.content, text=ui.home_welcome, text_color=ui.color_text,
                     font=(ui.font_family, ui.home_welcome_font_size, "bold")).pack(padx=pad * 3, pady=(pad, 4))
        ctk.CTkLabel(glow.content, text=ui.home_subtitle, text_color=ui.color_muted,
                     font=(ui.font_family, ui.body_font_size)).pack(padx=pad * 3, pady=(0, pad))

        card = ctk.CTkFrame(self, fg_color=ui.color_surface, corner_radius=ui.card_corner_radius,
                            border_width=1, border_color=ui.color_border)
        card.pack(padx=pad, pady=pad, fill="x")
        ctk.CTkLabel(card, text=ui.home_stats_title, text_color=ui.color_text, anchor="w",
                     font=(ui.font_family, ui.heading_font_size // 1.4, "bold")).pack(fill="x", padx=pad, pady=(pad, 0))

        numbers = ctk.CTkFrame(card, fg_color="transparent")
        numbers.pack(fill="x", padx=pad, pady=pad)
        self.created_value = self._stat(numbers, ui.home_stat_created)
        self.saved_value = self._stat(numbers, ui.home_stat_saved)

        folder_row = ctk.CTkFrame(card, fg_color="transparent")
        folder_row.pack(fill="x", padx=pad, pady=(0, pad))
        ctk.CTkLabel(folder_row, text=ui.home_stat_folder, text_color=ui.color_muted,
                     font=(ui.font_family, ui.body_font_size)).pack(side="left")
        self.folder_label = ctk.CTkLabel(folder_row, text="", text_color=ui.color_text, anchor="w",
                                         font=(ui.font_family, ui.body_font_size))
        self.folder_label.pack(side="left", padx=ui.card_padding, fill="x", expand=True)
        ctk.CTkButton(folder_row, text=ui.home_open_folder, fg_color=ui.color_accent, hover_color=ui.color_accent_hover, text_color=ui.color_accent_text, corner_radius=ui.button_corner_radius,
                      font=(ui.font_family, ui.body_font_size, "bold"),
                      command=lambda: open_path(self.pipeline.library.folder)).pack(side="right")

    def _stat(self, parent, caption: str) -> ctk.CTkLabel:
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.pack(side="left", padx=(0, self.ui.page_padding * 2))
        value = ctk.CTkLabel(box, text="0", text_color=self.ui.color_accent,
                             font=(self.ui.font_family, self.ui.stat_value_font_size, "bold"))
        value.pack(anchor="w")
        ctk.CTkLabel(box, text=caption, text_color=self.ui.color_muted,
                     font=(self.ui.font_family, self.ui.body_font_size)).pack(anchor="w")
        return value

    def on_show(self) -> None:
        """Refresh the numbers every time the page is opened."""
        stats = self.pipeline.library.stats()
        self.created_value.configure(text=str(stats["clips_created"]))
        self.saved_value.configure(text=str(stats["clips_saved"]))
        self.folder_label.configure(text=stats["saved_clips_dir"])
