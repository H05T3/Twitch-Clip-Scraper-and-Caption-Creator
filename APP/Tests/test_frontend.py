"""Front-end tests. The pure-logic parts always run; the window test needs tkinter + a display
(on a headless machine run it with:  xvfb-run -a python -m pytest APP/Tests)."""
import dataclasses
import os
import time

import pytest

from APP.BackEnd.ui_config import UiConfig
from APP.FrontEnd.components.glow_frame import blend
from APP.FrontEnd.task_runner import KIND_DONE, KIND_ERROR, KIND_PROGRESS, BackgroundTask


def test_blend_endpoints():
    assert blend("#000000", "#FFFFFF", 0) == "#000000"
    assert blend("#000000", "#FFFFFF", 1) == "#FFFFFF"
    assert blend("#000000", "#FF0000", 0.5) == "#800000"


def test_ui_colours_are_light_dark_pairs():
    ui = UiConfig()
    for name, value in dataclasses.asdict(ui).items():
        if name.startswith("color_") or name == "glow_color":
            assert isinstance(value, tuple) and len(value) == 2, name


def test_background_task_delivers_messages_and_errors():
    def work(emit):
        emit(KIND_PROGRESS, "a")
        emit(KIND_DONE, 1)

    def bad(_emit):
        raise ValueError("boom")

    for task, expected in ((BackgroundTask(work), [(KIND_PROGRESS, "a"), (KIND_DONE, 1)]),
                           (BackgroundTask(bad), [(KIND_ERROR, "boom")])):
        task.start()
        time.sleep(0.2)
        assert task.drain() == expected


def _display_available():
    try:
        import tkinter
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _display_available(), reason="needs tkinter and a display")
def test_window_opens_on_home_and_switches_pages(settings):
    import customtkinter  # noqa: F401  (import here so the module loads without a display)
    from APP.BackEnd.pipeline import ClipPipeline
    from APP.FrontEnd.main_window import MainWindow

    app = MainWindow(ClipPipeline(settings))
    try:
        app.update()
        assert app.nav._buttons["home"].cget("fg_color") == app.ui.color_accent  # Home is first
        app.show_page("fetch"); app.update()
        app.show_page("gallery"); app.update()
        assert "No saved clips" in app.pages["gallery"].grid_area.winfo_children()[0].cget("text")
        app.set_dark_mode(False)
        assert ClipPipeline(settings).store.theme == "light"  # theme remembered
    finally:
        app.close()
