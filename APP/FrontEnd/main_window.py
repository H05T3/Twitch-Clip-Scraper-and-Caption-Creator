"""The application window: nav bar on top, one page visible below."""
import customtkinter as ctk

from APP.BackEnd.pipeline import ClipPipeline
from APP.BackEnd.ui_config import UiConfig
from APP.FrontEnd.components.nav_bar import PAGE_FETCH, PAGE_GALLERY, PAGE_HOME, NavBar
from APP.FrontEnd.views.fetch_view import FetchView
from APP.FrontEnd.views.gallery_view import GalleryView
from APP.FrontEnd.views.home_view import HomeView

# customtkinter appearance-mode names.
MODE_DARK, MODE_LIGHT = "dark", "light"


class MainWindow(ctk.CTk):
    """Single responsibility: own the window (title, size, minimise/maximise/close via the
    native title bar, F11 full screen, Esc to leave it), build the pages, switch
    between them, and apply + remember the light/dark theme. Opens on Home."""

    def __init__(self, pipeline: ClipPipeline, ui: UiConfig = None):
        self.ui = ui or UiConfig()
        self.pipeline = pipeline
        theme = pipeline.store.theme
        ctk.set_appearance_mode(theme)  # preset from the last session
        super().__init__(fg_color=self.ui.color_bg)
        self.title(self.ui.window_title)
        self.geometry(f"{self.ui.window_width}x{self.ui.window_height}")
        self.minsize(self.ui.window_min_width, self.ui.window_min_height)
        self._fullscreen = False

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.nav = NavBar(self, self.ui, on_navigate=self.show_page, on_fullscreen=self.toggle_fullscreen,
                          on_theme=self.set_dark_mode, dark_mode=(theme == MODE_DARK))
        self.nav.grid(row=0, column=0, sticky="ew")

        self.pages = {
            PAGE_HOME: HomeView(self, self.ui, pipeline),
            PAGE_FETCH: FetchView(self, self.ui, pipeline),
            PAGE_GALLERY: GalleryView(self, self.ui, pipeline),
        }
        for page in self.pages.values():
            page.grid(row=1, column=0, sticky="nsew")

        self.bind(self.ui.fullscreen_key, lambda _e: self.toggle_fullscreen())
        self.bind(self.ui.exit_fullscreen_key, lambda _e: self.toggle_fullscreen(False))
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.show_page(PAGE_HOME)  # the Home screen is always first

    def show_page(self, key: str) -> None:
        page = self.pages[key]
        page.tkraise()
        self.nav.set_active(key)
        page.on_show()

    def toggle_fullscreen(self, state: bool = None) -> None:
        self._fullscreen = (not self._fullscreen) if state is None else state
        self.attributes("-fullscreen", self._fullscreen)

    def set_dark_mode(self, dark: bool) -> None:
        """Switch theme now and remember it for the next launch."""
        mode = MODE_DARK if dark else MODE_LIGHT
        ctk.set_appearance_mode(mode)
        self.pipeline.store.set_theme(mode)

    def close(self) -> None:
        """Window closed: stop players, remove temporary files."""
        for page in self.pages.values():
            page.destroy()
        self.pipeline.clear_workspace()
        self.destroy()
