"""Capture Lappa Qt GUI screenshots."""

from __future__ import annotations

import sys
from pathlib import Path

SERVER = Path(__file__).resolve().parents[1]
ROOT = SERVER.parents[1]  # Lappa repo root
sys.path.insert(0, str(SERVER / "src"))
OUT = ROOT / "docs" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from lappa.gui.app import app_icon_path
    from lappa.gui.main_window import MainWindow

    app = QApplication(sys.argv)
    icon_path = app_icon_path()
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))
    win = MainWindow(show_welcome=False)
    win.show()
    app.processEvents()
    # start a short sim for trail
    win.sim_run()
    win.sl_lx.setValue(40)
    win.sl_az.setValue(30)

    shots = [
        ("gui-welcome.png", "welcome"),
        ("gui-sim.png", "sim"),
        ("gui-demos.png", "demos"),
        ("gui-models.png", "models"),
        ("gui-packages.png", "packages"),
        ("gui-ros2.png", "ros2"),
    ]

    def grab(i: int = 0) -> None:
        if i >= len(shots):
            win.sim_stop()
            app.quit()
            return
        name, page = shots[i]
        if page == "models":
            obj = next((p for p in win._all_files if p.endswith(".obj")), None)
            if obj:
                win._open_file(obj)
        win._goto(page)
        app.processEvents()
        # let sim run a bit on sim page
        if page == "sim":
            for _ in range(8):
                win._tick_sim()
                app.processEvents()
        path = OUT / name
        win.grab().save(str(path), "PNG")
        print("wrote", path, path.stat().st_size)
        QTimer.singleShot(150, lambda: grab(i + 1))

    QTimer.singleShot(400, grab)
    app.exec()


if __name__ == "__main__":
    main()
