"""Start the desktop app:   python -m APP.main"""
from APP.BackEnd.config import load_settings
from APP.BackEnd.pipeline import ClipPipeline
from APP.BackEnd.ui_config import UiConfig
from APP.FrontEnd.main_window import MainWindow


def main() -> None:
    """Build the backend pipeline and open the window."""
    MainWindow(ClipPipeline(load_settings()), UiConfig()).mainloop()


if __name__ == "__main__":
    main()
