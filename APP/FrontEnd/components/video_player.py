"""A small in-app video player (OpenCV frames drawn into a label). Video only - no sound."""
import time

import customtkinter as ctk
import cv2
from PIL import Image

from APP.BackEnd.ui_config import UiConfig

# Slider range when the video length is unknown.
MIN_SLIDER_MAX = 1
# Milliseconds in a second (for frame timing).
MS_PER_SECOND = 1000.0


class VideoPlayer(ctk.CTkFrame):
    """Single responsibility: show one portrait video with Play/Pause and a scrub
    slider. Shows the first frame as a thumbnail, plays on demand, loops back to
    the start when finished. Call destroy() (done automatically with its parent)
    to release the file handle."""

    def __init__(self, master, ui: UiConfig, video_path):
        super().__init__(master, fg_color="transparent")
        self.ui = ui
        self._job = None
        self._playing = False
        self._image = None  # keep a reference so tk doesn't garbage-collect the picture
        self.width = ui.player_width
        self.height = self.width * ui.video_aspect_height // ui.video_aspect_width

        self.capture = cv2.VideoCapture(str(video_path))
        self.ok = self.capture.isOpened()
        self.fps = (self.capture.get(cv2.CAP_PROP_FPS) or ui.player_default_fps) if self.ok else ui.player_default_fps
        self.total = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT)) if self.ok else 0

        self.screen = ctk.CTkLabel(self, text="", width=self.width, height=self.height,
                                   fg_color=ui.color_video_bg, corner_radius=ui.corner_radius // 2)
        self.screen.pack()
        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.pack(fill="x", pady=(ui.card_padding // 2, 0))
        self.play_button = ctk.CTkButton(
            controls, text=ui.player_play, fg_color=ui.color_accent, hover_color=ui.color_accent_hover,
            text_color=ui.color_accent_text, width=ui.player_button_width, corner_radius=ui.button_corner_radius,
            font=(ui.font_family, ui.card_meta_font_size, "bold"), command=self.toggle)
        self.play_button.pack(side="left")
        slider_width = self.width - ui.player_button_width - ui.card_padding  # keep the card exactly as wide as the video
        self.slider = ctk.CTkSlider(controls, width=slider_width, from_=0, to=max(self.total - 1, MIN_SLIDER_MAX),
                                    command=self._on_scrub, progress_color=ui.color_accent,
                                    button_color=ui.color_accent, button_hover_color=ui.color_accent_hover)
        self.slider.pack(side="left", fill="x", expand=True, padx=(ui.card_padding, 0))
        self.slider.set(0)

        if self.ok:
            self._show_frame()
        else:
            self.screen.configure(text=ui.player_error, text_color=ui.color_muted)
            self.play_button.configure(state="disabled")
            self.slider.configure(state="disabled")

    # ---- frame handling ----
    def _show_frame(self) -> bool:
        """Read the next frame and draw it. Returns False at the end of the video."""
        ok, frame = self.capture.read()
        if not ok:
            return False
        rgb = cv2.cvtColor(cv2.resize(frame, (self.width, self.height), interpolation=cv2.INTER_AREA),
                           cv2.COLOR_BGR2RGB)
        picture = Image.fromarray(rgb)
        self._image = ctk.CTkImage(light_image=picture, dark_image=picture, size=(self.width, self.height))
        self.screen.configure(image=self._image)
        return True

    def _position(self) -> int:
        return int(self.capture.get(cv2.CAP_PROP_POS_FRAMES))

    def _on_scrub(self, value: float) -> None:
        """User dragged the slider: jump to that frame and show it."""
        self.capture.set(cv2.CAP_PROP_POS_FRAMES, int(value))
        self._show_frame()

    # ---- play / pause ----
    def toggle(self) -> None:
        self.pause() if self._playing else self.play()

    def play(self) -> None:
        if not self.ok or self._playing:
            return
        if self.total and self._position() >= self.total - 1:
            self.capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self._playing = True
        self.play_button.configure(text=self.ui.player_pause)
        self._tick(time.monotonic())

    def pause(self) -> None:
        self._playing = False
        self.play_button.configure(text=self.ui.player_play)
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None

    def _tick(self, started: float) -> None:
        if not self._playing:
            return
        if not self._show_frame():
            self.capture.set(cv2.CAP_PROP_POS_FRAMES, 0)  # finished: rewind, show first frame, stop
            self._show_frame()
            self.capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.slider.set(0)
            self.pause()
            return
        self.slider.set(self._position())
        frame_ms = MS_PER_SECOND / self.fps
        spent = (time.monotonic() - started) * MS_PER_SECOND
        self._job = self.after(max(1, int(frame_ms - spent)), lambda: self._tick(time.monotonic()))

    def destroy(self) -> None:
        self._playing = False
        if self._job is not None:
            try:
                self.after_cancel(self._job)
            except Exception:
                pass
            self._job = None
        if self.capture is not None:
            self.capture.release()
            self.capture = None
        super().destroy()
