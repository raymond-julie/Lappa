from __future__ import annotations

import time
from pathlib import Path

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from lappa import __version__, docker_bridge
from lappa.config import DEMOS_ROOT, IDE_ROOT, ensure_dirs
from lappa.package_loader import list_demo_packages, load_package
from lappa.sim.session import SESSION

app = typer.Typer(help="Lappa — ROS2 package IDE server CLI", no_args_is_help=True)
workspace_app = typer.Typer(help="Workspace / package")
demos_app = typer.Typer(help="Demo robots")
sim_app = typer.Typer(help="Native / docker sim")
docker_app = typer.Typer(help="Docker show mode")
app.add_typer(workspace_app, name="workspace")
app.add_typer(demos_app, name="demos")
app.add_typer(sim_app, name="sim")
app.add_typer(docker_app, name="docker")
console = Console()


@app.command("version")
def version_cmd() -> None:
    rprint({"version": __version__})


@app.command("demo")
def demo_cmd() -> None:
    """Offline smoke: list demos, run short sim steps for each engine."""
    ensure_dirs()
    packs = list_demo_packages(DEMOS_ROOT)
    rprint({"demos": len(packs), "names": [p.name for p in packs]})
    for p in packs:
        SESSION.start(p.name, p.path)
        SESSION.cmd(linear_x=0.4, linear_y=0.2, angular_z=0.2)
        for _ in range(5):
            time.sleep(0.05)
            SESSION.tick()
        st = SESSION.tick()
        rprint(f"  {p.name}: x={st.get('x')} y={st.get('y')} theta={st.get('theta')}")
        SESSION.stop()
    dstat = docker_bridge.status()
    rprint({"docker": dstat["available"], "daemon": dstat.get("daemon"), "ide": IDE_ROOT.is_dir()})
    rprint("Lappa demo complete (offline native sim).")


@demos_app.command("list")
def demos_list() -> None:
    table = Table(title="Lappa demos")
    table.add_column("Id")
    table.add_column("Description")
    table.add_column("Files")
    for p in list_demo_packages(DEMOS_ROOT):
        table.add_row(p.name, p.description[:60], str(len(p.files)))
    console.print(table)


@workspace_app.command("open")
def workspace_open(path: Path) -> None:
    pkg = load_package(path if path.is_absolute() else DEMOS_ROOT / path)
    rprint(pkg.to_dict())


@sim_app.command("start")
def sim_start(
    demo: str = typer.Option("diff_drive_2w", "--demo", "-d"),
) -> None:
    path = DEMOS_ROOT / demo
    out = SESSION.start(demo, path if path.is_dir() else None)
    rprint(out)


@sim_app.command("status")
def sim_status() -> None:
    rprint(SESSION.status())


@sim_app.command("stop")
def sim_stop() -> None:
    rprint(SESSION.stop())


@sim_app.command("cmd")
def sim_cmd(
    lx: float = typer.Option(0.3, "--lx"),
    ly: float = typer.Option(0.0, "--ly"),
    az: float = typer.Option(0.1, "--az"),
) -> None:
    rprint(SESSION.cmd(lx, ly, az))


@docker_app.command("status")
def docker_status() -> None:
    rprint(docker_bridge.status())


@docker_app.command("show")
def docker_show() -> None:
    rprint(docker_bridge.show_info())


@app.command("serve")
def serve_cmd(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8840, "--port"),
) -> None:
    """Serve IDE + API."""
    ensure_dirs()
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit('Install API extras: pip install -e ".[api]"') from exc
    from lappa.api import app as fastapi_app

    rprint(f"Lappa IDE → http://{host}:{port}")
    uvicorn.run(fastapi_app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    app()
