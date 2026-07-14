"""Entry: lappa-gui"""

from __future__ import annotations

import sys
from pathlib import Path

from lappa.paths import bundle_root, is_frozen


def app_icon_path() -> Path:
    if is_frozen():
        return bundle_root() / "lappa" / "assets" / "lappa.ico"
    return Path(__file__).resolve().parents[1] / "assets" / "lappa.ico"


def main(argv: list[str] | None = None) -> int:
    try:
        from PySide6.QtGui import QIcon
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print('Install GUI extras: pip install -e ".[gui]"  (needs PySide6)', file=sys.stderr)
        return 1
    from lappa.gui.main_window import MainWindow

    app = QApplication(sys.argv if argv is None else argv)
    app.setApplicationName("Lappa")
    app.setOrganizationName("MergeOS")
    icon_path = app_icon_path()
    icon = QIcon(str(icon_path)) if icon_path.is_file() else QIcon()
    if not icon.isNull():
        app.setWindowIcon(icon)
    win = MainWindow()
    if not icon.isNull():
        win.setWindowIcon(icon)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
