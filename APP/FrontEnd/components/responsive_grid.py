"""A scrollable grid that re-flows its cards into as many columns as fit."""
import customtkinter as ctk

from APP.BackEnd.ui_config import UiConfig


class ResponsiveGrid(ctk.CTkScrollableFrame):
    """Single responsibility: lay out child widgets (cards) in a grid whose column
    count follows the window width. Add widgets with add(), remove with remove()."""

    def __init__(self, master, ui: UiConfig):
        super().__init__(master, fg_color="transparent")
        self.ui = ui
        self.items = []
        self._columns = 0
        self._debounce = None
        self.bind("<Configure>", self._on_resize)

    def add(self, widget) -> None:
        self.items.append(widget)
        self._layout(force=True)

    def remove(self, widget) -> None:
        if widget in self.items:
            self.items.remove(widget)
            widget.destroy()
            self._layout(force=True)

    def clear(self) -> None:
        """Remove every child (cards and any placeholder label)."""
        for widget in self.winfo_children():
            widget.destroy()
        self.items = []
        self._columns = 0

    def _on_resize(self, _event=None) -> None:
        if self._debounce is not None:
            self.after_cancel(self._debounce)
        self._debounce = self.after(self.ui.resize_debounce_ms, self._layout)

    def _layout(self, force: bool = False) -> None:
        self._debounce = None
        slot = self.ui.card_width + self.ui.card_gap
        columns = max(1, self.winfo_width() // slot)
        if columns == self._columns and not force:
            return
        self._columns = columns
        for widget in self.items:
            widget.grid_forget()
        for index, widget in enumerate(self.items):
            widget.grid(row=index // columns, column=index % columns, sticky="n",
                        padx=self.ui.card_gap // 2, pady=self.ui.card_gap // 2)
