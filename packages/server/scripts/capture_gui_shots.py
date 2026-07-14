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
    from PySide6.QtWidgets import QApplication

    from lappa.gui.main_window import MainWindow

    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    app.processEvents()
    # start a short sim for trail
    win.sim_run()
    win.sl_lx.setValue(40)
    win.sl_az.setValue(30)

    shots = [
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
