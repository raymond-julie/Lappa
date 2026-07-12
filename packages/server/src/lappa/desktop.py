"""Desktop / frozen entry: start IDE server and open the browser."""

from __future__ import annotations

import threading
import time
import webbrowser
from typing import Optional

from rich import print as rprint

from lappa import __version__
from lappa.config import ensure_dirs
from lappa.paths import is_frozen


def run_desktop(
    host: str = "127.0.0.1",
    port: int = 8840,
    open_browser: bool = True,
) -> None:
    ensure_dirs()
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit('Install API extras: pip install -e ".[api]"') from exc
    from lappa.api import app as fastapi_app

    url = f"http://{host}:{port}"
    rprint(f"[bold]Lappa[/bold] v{__version__}  frozen={is_frozen()}")
    rprint(f"IDE → {url}")

    if open_browser:

        def _open() -> None:
            time.sleep(1.2)
            try:
                webbrowser.open(url)
            except Exception:
                pass

        threading.Thread(target=_open, daemon=True).start()

    uvicorn.run(fastapi_app, host=host, port=port, log_level="info")


def main(argv: Optional[list[str]] = None) -> None:
    """
    CLI entry used by PyInstaller.

    - No args / `desktop` → serve IDE + open browser
    - Otherwise forward to Typer CLI (demo, ros2, package, …)
    """
    import sys

    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("desktop", "gui", "start"):
        # parse optional --host --port --no-browser
        host = "127.0.0.1"
        port = 8840
        open_browser = True
        rest = args[1:] if args and args[0] in ("desktop", "gui", "start") else args
        i = 0
        while i < len(rest):
            if rest[i] == "--host" and i + 1 < len(rest):
                host = rest[i + 1]
                i += 2
            elif rest[i] == "--port" and i + 1 < len(rest):
                port = int(rest[i + 1])
                i += 2
            elif rest[i] == "--no-browser":
                open_browser = False
                i += 1
            else:
                i += 1
        run_desktop(host=host, port=port, open_browser=open_browser)
        return

    from lappa.cli import app

    # Typer reads sys.argv
    sys.argv = [sys.argv[0], *args]
    app()


if __name__ == "__main__":
    main()
