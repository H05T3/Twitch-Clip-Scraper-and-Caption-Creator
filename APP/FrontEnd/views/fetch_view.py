"""'Get new clips' page: paste a streamer link, watch progress, review/save/discard results."""
import customtkinter as ctk

from APP.BackEnd.pipeline import ClipPipeline
from APP.BackEnd.ui_config import UiConfig
from APP.FrontEnd.components.responsive_grid import ResponsiveGrid
from APP.FrontEnd.components.video_card import KIND_DANGER, KIND_PRIMARY, CardAction, VideoCard
from APP.FrontEnd.task_runner import KIND_CLIP, KIND_DONE, KIND_ERROR, KIND_PROGRESS, BackgroundTask

# Card button ids.
ACTION_SAVE, ACTION_DISCARD = "save", "discard"
# Joiner for hashtags shown under a card.
HASHTAG_PREFIX = "#"


class FetchView(ctk.CTkFrame):
    """Single responsibility: drive the fetch workflow on screen. A text box expands
    smoothly when the page opens; pressing Fetch runs the backend on a worker thread;
    each finished clip appears as a card the user can Save or Discard."""

    def __init__(self, master, ui: UiConfig, pipeline: ClipPipeline):
        super().__init__(master, fg_color="transparent")
        self.ui, self.pipeline = ui, pipeline
        self._task = None
        self._animation_job = None
        pad = ui.page_padding

        ctk.CTkLabel(self, text=ui.fetch_title, text_color=ui.color_text, anchor="w",
                     font=(ui.font_family, ui.heading_font_size, "bold")).pack(fill="x", padx=pad, pady=(pad, 0))
        ctk.CTkLabel(self, text=ui.fetch_hint, text_color=ui.color_muted, anchor="w",
                     font=(ui.font_family, ui.body_font_size)).pack(fill="x", padx=pad)

        self.entry_zone = ctk.CTkFrame(self, fg_color="transparent", height=ui.fetch_entry_height + pad)
        self.entry_zone.pack(fill="x", padx=pad, pady=(pad // 2, 0))
        self.entry_zone.pack_propagate(False)
        self.entry = ctk.CTkEntry(self.entry_zone, width=ui.fetch_entry_start_width, height=ui.fetch_entry_height,
                                  placeholder_text=ui.fetch_placeholder, corner_radius=ui.corner_radius,
                                  font=(ui.font_family, ui.body_font_size))
        self.entry.place(relx=0.5, rely=0.5, anchor="center")
        self.entry.bind("<Return>", lambda _e: self.start())

        self.button = ctk.CTkButton(self, text=ui.fetch_button, fg_color=ui.color_accent, hover_color=ui.color_accent_hover, text_color=ui.color_accent_text, height=ui.nav_button_height,
                                    corner_radius=ui.button_corner_radius,
                                    font=(ui.font_family, ui.body_font_size, "bold"), command=self.start)
        self.button.pack(pady=(ui.card_padding, 0))
        self.status = ctk.CTkLabel(self, text="", text_color=ui.color_muted, font=(ui.font_family, ui.body_font_size))
        self.status.pack(pady=(ui.card_padding, 0))
        self.progress = ctk.CTkProgressBar(self, mode="indeterminate", progress_color=ui.color_accent)
        self.detail = ctk.CTkLabel(self, text="", text_color=ui.color_muted, justify="left",
                                   font=(ui.font_family, ui.card_meta_font_size))
        self.grid_area = ResponsiveGrid(self, ui)
        self.grid_area.pack(fill="both", expand=True, padx=pad, pady=pad // 2)
        self.empty_label = ctk.CTkLabel(self.grid_area, text=ui.fetch_empty, text_color=ui.color_muted,
                                        font=(ui.font_family, ui.body_font_size))
        self.empty_label.pack(pady=pad)

    # ---- page lifecycle ----
    def on_show(self) -> None:
        """Replay the smooth text-box expansion each time the page is opened."""
        self.entry.configure(width=self.ui.fetch_entry_start_width)
        if self._animation_job is not None:
            self.after_cancel(self._animation_job)
        self._animate(0)

    def _animate(self, elapsed_ms: int) -> None:
        ui = self.ui
        progress = min(elapsed_ms / ui.fetch_animation_ms, 1.0)
        eased = 1 - (1 - progress) ** 3  # ease-out
        target = max(min(ui.fetch_entry_end_width, self.winfo_width() - 2 * ui.page_padding), ui.fetch_entry_start_width)
        self.entry.configure(width=int(ui.fetch_entry_start_width + (target - ui.fetch_entry_start_width) * eased))
        self._animation_job = None
        if progress < 1.0:
            self._animation_job = self.after(ui.fetch_animation_step_ms,
                                             lambda: self._animate(elapsed_ms + ui.fetch_animation_step_ms))

    # ---- running a fetch ----
    def start(self) -> None:
        if self._task is not None:
            return  # already running
        url = self.entry.get().strip()
        self._reset_results()
        self.detail.pack_forget()
        self._set_busy(True)
        self.status.configure(text="")

        def work(emit):
            clips, errors = self.pipeline.fetch_and_process(
                url, progress=lambda m: emit(KIND_PROGRESS, m), on_clip=lambda c: emit(KIND_CLIP, c))
            emit(KIND_DONE, (len(clips), errors))

        self._task = BackgroundTask(work)
        self._task.start()
        self._poll()

    def _poll(self) -> None:
        for kind, payload in self._task.drain():
            if kind == KIND_PROGRESS:
                self.status.configure(text=payload, text_color=self.ui.color_muted)
            elif kind == KIND_CLIP:
                self._add_card(payload)
            elif kind == KIND_DONE:
                self._finish(*payload)
                return
            elif kind == KIND_ERROR:
                self._set_busy(False)
                self._task = None
                self.status.configure(text=self.ui.fetch_error_prefix + payload, text_color=self.ui.color_danger)
                return
        self.after(self.ui.fetch_poll_ms, self._poll)

    def _finish(self, count: int, errors: list) -> None:
        ui = self.ui
        self._set_busy(False)
        self._task = None
        text = ui.fetch_done.format(count=count) if not errors else ui.fetch_done_with_errors.format(
            count=count, failed=len(errors))
        self.status.configure(text=text, text_color=ui.color_success if not errors else ui.color_muted)
        if errors:
            self.detail.configure(text="\n".join(errors))
            self.detail.pack(after=self.status)

    def _set_busy(self, busy: bool) -> None:
        self.button.configure(state="disabled" if busy else "normal",
                              text=self.ui.fetch_busy_button if busy else self.ui.fetch_button)
        if busy:
            self.progress.pack(after=self.status, pady=(self.ui.card_padding // 2, 0))
            self.progress.start()
        else:
            self.progress.stop()
            self.progress.pack_forget()

    # ---- cards ----
    def _reset_results(self) -> None:
        """Throw away the previous run's cards and temporary files."""
        self.grid_area.clear()
        self.pipeline.clear_workspace()
        self.empty_label = ctk.CTkLabel(self.grid_area, text=self.ui.fetch_empty, text_color=self.ui.color_muted,
                                        font=(self.ui.font_family, self.ui.body_font_size))
        self.empty_label.pack(pady=self.ui.page_padding)

    def _add_card(self, clip) -> None:
        ui = self.ui
        if self.empty_label.winfo_exists():
            self.empty_label.destroy()
        subtitle = " ".join(HASHTAG_PREFIX + tag for tag in clip.hashtags)
        card = VideoCard(
            self.grid_area, ui, clip.title, clip.video_path, subtitle=subtitle, data=clip,
            actions=[CardAction(ACTION_SAVE, ui.action_save, KIND_PRIMARY, self._save),
                     CardAction(ACTION_DISCARD, ui.action_discard, KIND_DANGER, self._discard)])
        self.grid_area.add(card)

    def _save(self, card: VideoCard) -> None:
        self.pipeline.save(card.data)
        card.mark_done(ACTION_SAVE, self.ui.action_saved)
        card.buttons[ACTION_DISCARD].configure(state="disabled")

    def _discard(self, card: VideoCard) -> None:
        clip = card.data
        self.grid_area.remove(card)   # closes the player's file handle first
        self.pipeline.discard(clip)
