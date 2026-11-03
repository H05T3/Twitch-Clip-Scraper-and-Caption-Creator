"""'See past clips' page: every saved clip in a card grid."""
from tkinter import messagebox

import customtkinter as ctk

from APP.BackEnd.pipeline import ClipPipeline
from APP.BackEnd.ui_config import UiConfig
from APP.FrontEnd.components.responsive_grid import ResponsiveGrid
from APP.FrontEnd.components.video_card import KIND_DANGER, CardAction, VideoCard

# Card button id and hashtag prefix.
ACTION_DELETE = "delete"
HASHTAG_PREFIX = "#"


class GalleryView(ctk.CTkFrame):
    """Single responsibility: list the MP4s found in the SavedClips folder as playable
    cards, and delete them on request. Re-reads the folder each time it is shown."""

    def __init__(self, master, ui: UiConfig, pipeline: ClipPipeline):
        super().__init__(master, fg_color="transparent")
        self.ui, self.pipeline = ui, pipeline
        pad = ui.page_padding
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=pad, pady=(pad, 0))
        ctk.CTkLabel(header, text=ui.gallery_title, text_color=ui.color_text,
                     font=(ui.font_family, ui.heading_font_size, "bold")).pack(side="left")
        self.count_label = ctk.CTkLabel(header, text="", text_color=ui.color_muted,
                                        font=(ui.font_family, ui.body_font_size))
        self.count_label.pack(side="left", padx=pad)
        self.grid_area = ResponsiveGrid(self, ui)
        self.grid_area.pack(fill="both", expand=True, padx=pad, pady=pad // 2)

    def on_show(self) -> None:
        self.grid_area.clear()
        clips = self.pipeline.library.list_clips()
        if not clips:
            ctk.CTkLabel(self.grid_area, text=self.ui.gallery_empty, text_color=self.ui.color_muted,
                         font=(self.ui.font_family, self.ui.body_font_size)).pack(pady=self.ui.page_padding)
        for meta in clips:
            tags = " ".join(HASHTAG_PREFIX + t for t in meta.get("hashtags", []))
            self.grid_area.add(VideoCard(
                self.grid_area, self.ui, meta.get("title", ""), meta["video_path"], subtitle=tags, data=meta,
                actions=[CardAction(ACTION_DELETE, self.ui.action_delete, KIND_DANGER, self._delete)]))
        self._update_count()

    def _update_count(self) -> None:
        self.count_label.configure(text=self.ui.gallery_count.format(count=len(self.grid_area.items)))

    def _delete(self, card: VideoCard) -> None:
        title = card.data.get("title", "")
        if not messagebox.askyesno(self.ui.gallery_delete_confirm_title,
                                   self.ui.gallery_delete_confirm.format(title=title)):
            return
        path = card.video_path
        self.grid_area.remove(card)   # release the video file before deleting it
        self.pipeline.library.delete(path)
        self._update_count()
