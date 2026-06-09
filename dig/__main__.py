"""dig/__main__.py — Main entry point for the DIG application.
exports: main() -> int
used_by: PyInstaller
rules:
Must safely use `sys._MEIPASS` when frozen.
Must add a first-run config `~/.dig/` creation step.
"""

import os
import sys
from pathlib import Path


def main() -> int:
    """Launch the DIG application."""
    if getattr(sys, "frozen", False):
        # If the application is run as a bundle, the PyInstaller bootloader
        # extends the sys module by a flag frozen=True and sets the app
        # path into variable _MEIPASS.
        application_path = sys._MEIPASS
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))

    # Create first-run config directory
    config_dir = Path.home() / ".dig"
    if not config_dir.exists():
        config_dir.mkdir(parents=True, exist_ok=True)
        # Create default config if needed
        config_file = config_dir / "config.yaml"
        if not config_file.exists():
            config_file.write_text("# DIG User Configuration\n")

    # Launch the PyQt/PySide app
    from PySide6.QtWidgets import QApplication
    from dig.viz.main_window import MainWindow

    # Force X11 on Linux to prevent VTK BadWindow errors under Wayland
    if sys.platform.startswith("linux"):
        os.environ["QT_QPA_PLATFORM"] = "xcb"

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    print(f"DIG Application initialized from {application_path}")
    print(f"User configuration directory: {config_dir}")

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
