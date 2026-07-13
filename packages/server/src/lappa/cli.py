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


@app.command("gui")
def gui_cmd() -> None:
    """Launch modern Qt desktop shell (pip install -e '.[gui]')."""
    from lappa.gui.app import main as gui_main

    raise SystemExit(gui_main())


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
    # Full aligned 3D robot (chassis + wheels + lidar fitted)
    built = models3d.build_aligned_robot("diff_drive_2w")
    rprint(
        {
            "3d_robot": built["package"],
            "links": built["links"],
            "models": built["models"],
            "scene_nodes": built["scene"]["count"],
        }
    )
    # trajectory CSV
    from lappa.config import WORKSPACES

    SESSION.start("diff_drive_2w", DEMOS_ROOT / "diff_drive_2w")
    SESSION.cmd(linear_x=0.5, angular_z=0.3)
    for _ in range(8):
        time.sleep(0.05)
        SESSION.tick()
    WORKSPACES.mkdir(parents=True, exist_ok=True)
    csv_path = WORKSPACES / "demo_trajectory.csv"
    csv_path.write_text(SESSION.trajectory_csv(), encoding="utf-8")
    rprint({"trajectory_csv": str(csv_path), "points": SESSION.status()["trajectory_points"]})
    SESSION.stop()
    dstat = docker_bridge.status()
    rprint({"docker": dstat["available"], "daemon": dstat.get("daemon"), "ide": IDE_ROOT.is_dir()})
    rprint("Lappa demo complete (sim + ros2 version + package + 3d + trajectory).")


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


@sim_app.command("summary")
def sim_summary() -> None:
    """Print compact sim session summary (pose, joints count, lidar rays)."""
    st = SESSION.status()
    state = st.get("state") or st
    lidar = state.get("lidar") or []
    joints = state.get("joints") or []
    rprint(
        {
            "demo": state.get("demo") or st.get("demo"),
            "kind": state.get("kind"),
            "running": state.get("running"),
            "pose": {
                "x": state.get("x"),
                "y": state.get("y"),
                "theta": state.get("theta"),
            },
            "n_joints": len(joints),
            "n_lidar": len(lidar),
            "lidar_min": min(lidar) if lidar else None,
            "t": state.get("t"),
        }
    )


@sim_app.command("trajectory")
def sim_trajectory(
    out: Path | None = typer.Option(None, "--out", "-o", help="Write CSV path"),
) -> None:
    """Export recorded odom trail as CSV."""
    csv = SESSION.trajectory_csv()
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(csv, encoding="utf-8")
        rprint({"ok": True, "path": str(out), "bytes": out.stat().st_size})
    else:
        print(csv)


@docker_app.command("status")
def docker_status() -> None:
    rprint(docker_bridge.status())


@docker_app.command("show")
def docker_show() -> None:
    rprint(docker_bridge.show_info())


@docker_app.command("start")
def docker_start() -> None:
    """Start Docker runtime (demos mounted at /ws/src for IDE edits)."""
    rprint(docker_bridge.start_runtime())


@docker_app.command("stop")
def docker_stop() -> None:
    rprint(docker_bridge.stop_runtime())


@docker_app.command("build")
def docker_build(
    demo: str = typer.Option(
        "",
        "--demo",
        "-d",
        help="Package to colcon-build (empty = all under /ws/src)",
    ),
) -> None:
    """colcon build ROS2 package(s) inside the container."""
    rprint(docker_bridge.build_package(demo or None))


@docker_app.command("launch")
def docker_launch(
    demo: str = typer.Option("diff_drive_2w", "--demo", "-d", help="Demo package name"),
    no_rebuild: bool = typer.Option(False, "--no-rebuild", help="Skip colcon build"),
) -> None:
    """Load ROS2, colcon-build package, ros2 launch <pkg> sim.launch.py."""
    rprint(docker_bridge.launch_demo(demo, rebuild=not no_rebuild))


@docker_app.command("launch-stop")
def docker_launch_stop() -> None:
    rprint(docker_bridge.stop_launch())


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
    auto_fit: bool = typer.Option(True, "--auto-fit/--no-auto-fit"),
    link: str = typer.Option("base_link", "--link"),
) -> None:
    rprint(
        models3d.attach_model_to_package(
            package,
            model_id,
            link_name=link,
            auto_fit=auto_fit,
        )
    )


@model_app.command("fit")
def model_fit(
    model_id: str = typer.Argument(..., help="Library model id"),
    sx: float = typer.Option(0.4, "--sx"),
    sy: float = typer.Option(0.3, "--sy"),
    sz: float = typer.Option(0.12, "--sz"),
    uniform: bool = typer.Option(False, "--uniform"),
    save_as: str | None = typer.Option(None, "--as", help="Output model id"),
) -> None:
    """Auto-scale mesh AABB to target size (khớp 3D)."""
    rprint(
        models3d.fit_library_model(
            model_id,
            [sx, sy, sz],
            uniform=uniform,
            save_as=save_as,
        )
    )


@model_app.command("build-robot")
def model_build_robot(
    package: str = typer.Argument(..., help="Demo package id"),
    kind: str | None = typer.Option(None, "--kind", "-k", help="Layout kind (default=package name)"),
) -> None:
    """Build full aligned 3D robot (chassis + wheels + lidar) into package URDF."""
    rprint(models3d.build_aligned_robot(package, kind=kind))


@model_app.command("scene")
def model_scene(package: str = typer.Argument(...)) -> None:
    """Print package scene3d JSON for the WebGL viewer."""
    rprint(models3d.package_scene3d(package))


@app.command("serve")
def serve_cmd(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8840, "--port"),
    open_browser: bool = typer.Option(False, "--open/--no-open", help="Open system browser"),
) -> None:
    """Serve IDE + API."""
    if open_browser:
        from lappa.desktop import run_desktop

        run_desktop(host=host, port=port, open_browser=True)
        return
    ensure_dirs()
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit('Install API extras: pip install -e ".[api]"') from exc
    from lappa.api import app as fastapi_app

    rprint(f"Lappa IDE → http://{host}:{port}")
    uvicorn.run(fastapi_app, host=host, port=port, log_level="info")


@app.command("desktop")
def desktop_cmd(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8840, "--port"),
    no_browser: bool = typer.Option(False, "--no-browser"),
) -> None:
    """Launch IDE server and open the browser (release builds default here)."""
    from lappa.desktop import run_desktop

    run_desktop(host=host, port=port, open_browser=not no_browser)


if __name__ == "__main__":
    app()
