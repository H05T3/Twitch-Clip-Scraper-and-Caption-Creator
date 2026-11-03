"""A frame with a soft blue glow around it (tkinter has no real drop-shadow)."""
import customtkinter as ctk

from APP.BackEnd.ui_config import UiConfig

# Index of the light-mode / dark-mode colour inside a (light, dark) pair.
LIGHT, DARK = 0, 1


def blend(base_hex: str, top_hex: str, amount: float) -> str:
    """Mix two '#RRGGBB' colours: amount 0 -> base, 1 -> top."""
    base = [int(base_hex[i:i + 2], 16) for i in (1, 3, 5)]
    top = [int(top_hex[i:i + 2], 16) for i in (1, 3, 5)]
    mixed = [round(b + (t - b) * amount) for b, t in zip(base, top)]
    return "#{:02X}{:02X}{:02X}".format(*mixed)


class GlowFrame(ctk.CTkFrame):
    """Single responsibility: draw concentric rounded rectangles that fade from the
    page background to the glow colour, giving an ambient blue halo around
    `self.content` (put your widgets inside `content`). Works in light and dark mode
    because every layer colour is a (light, dark) pair."""

    def __init__(self, master, ui: UiConfig):
        outer_colors = self._layer_color(ui, 0)
        super().__init__(master, fg_color=outer_colors, corner_radius=ui.glow_corner_radius)
        parent = self
        for layer in range(1, ui.glow_layers + 1):
            radius = max(ui.glow_corner_radius - layer * ui.glow_step_padding, 0)
            frame = ctk.CTkFrame(parent, fg_color=self._layer_color(ui, layer), corner_radius=radius)
            frame.pack(fill="both", expand=True, padx=ui.glow_step_padding, pady=ui.glow_step_padding)
            parent = frame
        self.content = parent  # innermost frame: place the real widgets here

    @staticmethod
    def _layer_color(ui: UiConfig, layer: int) -> tuple:
        """Layer 0 (outside) is almost the background colour; the last layer is the brightest."""
        fraction = ((layer + 1) / (ui.glow_layers + 1)) ** 2
        return tuple(
            blend(ui.color_bg[mode], ui.glow_color[mode], ui.glow_strength * fraction)
            for mode in (LIGHT, DARK)
        )
