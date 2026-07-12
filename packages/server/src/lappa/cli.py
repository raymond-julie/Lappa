from __future__ import annotations

import time
from pathlib import Path

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from lappa import __version__, docker_bridge, models3d, packager, ros2_versions
from lappa.config import DEMOS_ROOT, IDE_ROOT, ensure_dirs
from lappa.package_loader import list_demo_packages, load_package
from lappa.sim.session import SESSION

app = typer.Typer(help="Lappa — ROS2 package IDE server CLI", no_args_is_help=True)
workspace_app = typer.Typer(help="Workspace / package")
demos_app = typer.Typer(help="Demo robots")
sim_app = typer.Typer(help="Native / docker sim")
docker_app = typer.Typer(help="Docker show mode")
ros2_app = typer.Typer(help="ROS2 distro selection")
pkg_app = typer.Typer(help="Bundle / package ROS2 pkgs")
model_app = typer.Typer(help="Procedural 3D meshes")
app.add_typer(workspace_app, name="workspace")
app.add_typer(demos_app, name="demos")
app.add_typer(sim_app, name="sim")
app.add_typer(docker_app, name="docker")
app.add_typer(ros2_app, name="ros2")
app.add_typer(pkg_app, name="package")
app.add_typer(model_app, name="model")
console = Console()


@app.command("version")
def version_cmd() -> None:
    rprint({"version": __version__})


@app.command("demo")
def demo_cmd() -> None:
    """Offline smoke: sim engines + ROS2 version + bundle + 3D mesh attach."""
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
    # ROS2 versions
    sel = ros2_versions.get_selected()
    rprint({"ros2_selected": sel.get("id"), "docker_image": sel.get("docker_image")})
    ros2_versions.set_selected("jazzy")
    rprint({"switched_to": ros2_versions.get_selected()["id"]})
    ros2_versions.set_selected(sel.get("id") or "humble")
    docker_bridge.apply_ros2_dockerfile()
    # packager
    bundle = packager.package_bundle(["diff_drive_2w", "omni_3w"], distro="humble")
    rprint({"bundle": bundle["filename"], "size": bundle["size_bytes"]})
    # 3D model
    mesh = models3d.create_model("chassis", name="demo_chassis", sx=0.45, sy=0.32, sz=0.12)
    att = models3d.attach_model_to_package("diff_drive_2w", mesh["id"])
    rprint({"mesh": mesh["id"], "attached_urdf": att["urdf"]})
    dstat = docker_bridge.status()
    rprint({"docker": dstat["available"], "daemon": dstat.get("daemon"), "ide": IDE_ROOT.is_dir()})
    rprint("Lappa demo complete (sim + ros2 version + package + 3d).")


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


@ros2_app.command("list")
def ros2_list() -> None:
    table = Table(title="ROS2 versions")
    table.add_column("Id")
    table.add_column("Name")
    table.add_column("Ubuntu")
    table.add_column("Status")
    table.add_column("Image")
    sel = ros2_versions.get_selected()["id"]
    for v in ros2_versions.list_versions():
        mark = " *" if v["id"] == sel else ""
        table.add_row(v["id"] + mark, v["name"], v["ubuntu"], v["status"], v["docker_image"])
    console.print(table)


@ros2_app.command("get")
def ros2_get() -> None:
    rprint(ros2_versions.get_selected())


@ros2_app.command("set")
def ros2_set(distro: str = typer.Argument(..., help="humble|iron|jazzy|kilted|rolling")) -> None:
    selected = ros2_versions.set_selected(distro)
    docker_bridge.apply_ros2_dockerfile(distro)
    rprint(selected)


@pkg_app.command("list")
def pkg_list() -> None:
    for p in packager.list_bundleable():
        rprint(f"{p['name']}: {p['files']} files — {p['description'][:50]}")


@pkg_app.command("bundle")
def pkg_bundle(
    packages: list[str] | None = typer.Option(
        None,
        "--pkg",
        "-p",
        help="Package name (repeatable). Default: all demos.",
    ),
    distro: str | None = typer.Option(None, "--distro", "-d"),
) -> None:
    names = packages if packages else None
    rprint(packager.package_bundle(names, distro=distro))


@pkg_app.command("bundles")
def pkg_bundles() -> None:
    rprint(packager.list_bundles())


@model_app.command("presets")
def model_presets() -> None:
    for p in models3d.list_presets():
        rprint(f"{p['id']}: {p['description']}")


@model_app.command("create")
def model_create(
    preset: str = typer.Argument("box"),
    name: str | None = typer.Option(None, "--name", "-n"),
) -> None:
    rprint(models3d.create_model(preset, name=name))


@model_app.command("list")
def model_list() -> None:
    rprint(models3d.list_library())


@model_app.command("attach")
def model_attach(
    package: str = typer.Argument(..., help="Demo package id"),
    model_id: str = typer.Argument(..., help="Model id from library"),
) -> None:
    rprint(models3d.attach_model_to_package(package, model_id))


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
