"""Docker ROS2 bridge: container lifecycle + launch demo packages.

Native kinematics sim works offline. Docker is the path for real
``ros2 launch <pkg> sim.launch.py`` against mounted package sources so
IDE edits (Explorer/Monaco/Qt Editor) land in the container without
rebuilding the image every time.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from lappa.config import DEMOS_ROOT, DOCKER_DIR
from lappa.ros2_versions import dockerfile_for, get_selected

CONTAINER_NAME = "lappa-ros2"


class _LaunchState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.demo: str | None = None
        self.proc: subprocess.Popen | None = None
        self.started_at: float | None = None
        self.last_log: str = ""
        self.mode: str = "idle"  # idle | docker_runtime | docker_launch


_STATE = _LaunchState()


def docker_available() -> bool:
    return shutil.which("docker") is not None


def _run(args: list[str], timeout: float = 20.0) -> tuple[int, str, str]:
    try:
        p = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return p.returncode, p.stdout or "", p.stderr or ""
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        return 1, "", str(e)


def apply_ros2_dockerfile(distro: str | None = None) -> dict[str, Any]:
    """Write packages/docker/Dockerfile for the selected (or given) ROS2 distro."""
    selected = get_selected() if not distro else None
    code = distro or (selected["id"] if selected else "humble")
    text = dockerfile_for(code)
    path = DOCKER_DIR / "Dockerfile"
    path.write_text(text, encoding="utf-8")
    stamp = DOCKER_DIR / "ros2_distro.txt"
    stamp.write_text(code + "\n", encoding="utf-8")
    return {
        "ok": True,
        "distro": code,
        "dockerfile": str(path),
        "image_tag": f"lappa-ros2:{code}",
    }


def status() -> dict[str, Any]:
    selected = get_selected()
    distro = selected.get("id", "humble")
    image = f"lappa-ros2:{distro}"
    with _STATE.lock:
        launch = {
            "mode": _STATE.mode,
            "demo": _STATE.demo,
            "started_at": _STATE.started_at,
            "running": _STATE.proc is not None and _STATE.proc.poll() is None,
            "last_log": _STATE.last_log[-1500:],
        }
    launch_hint = {
        "compose": str(DOCKER_DIR / "docker-compose.yml"),
        "suggested": [
            f"docker compose -f {DOCKER_DIR / 'docker-compose.yml'} up --build -d",
            "lappa docker launch --demo diff_drive_2w",
            f"# inside container: source /opt/ros/{distro}/setup.bash",
        ],
        "native_fallback": "lappa sim start --demo diff_drive_2w",
        "bridge": "IDE edits under packages/demos mount to /ws/src; launch uses that tree",
    }
    if not docker_available():
        return {
            "available": False,
            "daemon": False,
            "message": "Docker CLI not found — use native sim + IDE file editor offline",
            "compose_file": str(DOCKER_DIR / "docker-compose.yml"),
            "ros2_distro": distro,
            "image": image,
            "launch": launch_hint,
            "session": launch,
        }
    code, out, err = _run(["docker", "info", "--format", "{{json .ServerVersion}}"])
    daemon = code == 0
    ccode, cout, _ = _run(
        [
            "docker",
            "ps",
            "--filter",
            f"name={CONTAINER_NAME}",
            "--format",
            "{{.Names}} {{.Status}}",
        ]
    )
    running = bool(cout.strip()) if ccode == 0 else False
    return {
        "available": True,
        "daemon": daemon,
        "running": running,
        "ps": cout.strip(),
        "message": "ok" if daemon else (err or out or "daemon not running"),
        "compose_file": str(DOCKER_DIR / "docker-compose.yml"),
        "image": image,
        "ros2_distro": distro,
        "docker_base": selected.get("docker_image"),
        "launch": launch_hint,
        "session": launch,
    }


def start_runtime(workspace: Path | None = None) -> dict[str, Any]:
    st = status()
    if not st["available"]:
        return {"ok": False, **st}
    if not st["daemon"]:
        return {"ok": False, "error": "Docker daemon not running", **st}
    applied = apply_ros2_dockerfile()
    compose = DOCKER_DIR / "docker-compose.yml"
    if not compose.is_file():
        return {"ok": False, "error": f"missing {compose}"}
    code, out, err = _run(
        ["docker", "compose", "-f", str(compose), "up", "-d", "--build"],
        timeout=180.0,
    )
    with _STATE.lock:
        if code == 0:
            _STATE.mode = "docker_runtime"
    return {
        "ok": code == 0,
        "code": code,
        "stdout": out[-2000:],
        "stderr": err[-2000:],
        "dockerfile": applied,
        "status": status(),
        "mount": "packages/demos → /ws/src (live IDE edits)",
    }


def stop_runtime() -> dict[str, Any]:
    stop_launch()
    compose = DOCKER_DIR / "docker-compose.yml"
    if not compose.is_file():
        return {"ok": False, "error": "missing compose"}
    code, out, err = _run(
        ["docker", "compose", "-f", str(compose), "down"], timeout=60.0
    )
    with _STATE.lock:
        _STATE.mode = "idle"
        _STATE.demo = None
    return {
        "ok": code == 0,
        "stdout": out[-1000:],
        "stderr": err[-1000:],
        "status": status(),
    }


def _ensure_container() -> dict[str, Any]:
    st = status()
    if st.get("running"):
        return {"ok": True, "status": st}
    return start_runtime()


def _resolve_launch(demo: str) -> tuple[str, str] | None:
    """Return (package_name, launch_file_basename) for a demo package."""
    root = DEMOS_ROOT / demo
    if not root.is_dir():
        return None
    launch_dir = root / "launch"
    if not launch_dir.is_dir():
        return None
    for name in ("sim.launch.py", "sim.launch.xml", "bringup.launch.py"):
        if (launch_dir / name).is_file():
            # ament package name usually matches folder
            pkg = demo
            xml = root / "package.xml"
            if xml.is_file():
                try:
                    import xml.etree.ElementTree as ET

                    n = ET.parse(xml).getroot().findtext("name")
                    if n:
                        pkg = n.strip()
                except Exception:  # noqa: BLE001
                    pass
            return pkg, name
    # any launch file
    for p in sorted(launch_dir.glob("*.launch.py")):
        return demo, p.name
    return None


def launch_demo(demo: str, *, ensure_up: bool = True) -> dict[str, Any]:
    """Start (or restart) ``ros2 launch`` for a demo package inside the container.

    Package sources are bind-mounted at ``/ws/src/<demo>`` so IDE file saves
    are visible to the launch without rebuilding.
    """
    demo = (demo or "").strip()
    if not demo:
        return {"ok": False, "error": "demo name required"}
    if not (DEMOS_ROOT / demo).is_dir():
        return {"ok": False, "error": f"unknown demo package: {demo}"}

    resolved = _resolve_launch(demo)
    if not resolved:
        return {
            "ok": False,
            "error": f"no launch file under packages/demos/{demo}/launch",
            "native_fallback": f"lappa sim start --demo {demo}",
        }
    pkg, launch_file = resolved
    selected = get_selected()
    distro = selected.get("id", "humble")

    if ensure_up:
        up = _ensure_container()
        if not up.get("ok") and not status().get("running"):
            return {
                "ok": False,
                "error": up.get("error") or up.get("message") or "container not up",
                "native_fallback": f"lappa sim start --demo {demo}",
                "detail": up,
            }

    stop_launch()

    # Prefer sourcing distro setup; package may not be colcon-built — run
    # launch file by path so editable sources work immediately.
    launch_path = f"/ws/src/{demo}/launch/{launch_file}"
    bash = (
        f"source /opt/ros/{distro}/setup.bash 2>/dev/null; "
        f"export ROS_DOMAIN_ID=${{ROS_DOMAIN_ID:-42}}; "
        f"echo '[lappa] launching {pkg} {launch_file} for IDE+Docker bridge'; "
        f"ros2 launch {launch_path} || "
        f"ros2 launch {pkg} {launch_file}"
    )
    cmd = [
        "docker",
        "exec",
        "-d",
        CONTAINER_NAME,
        "bash",
        "-lc",
        bash,
    ]
    code, out, err = _run(cmd, timeout=30.0)
    log = (out + "\n" + err).strip()
    with _STATE.lock:
        _STATE.demo = demo
        _STATE.started_at = time.time()
        _STATE.last_log = log or f"docker exec launch {demo} code={code}"
        _STATE.mode = "docker_launch" if code == 0 else _STATE.mode

    # Also kick a short non-detached probe for feedback
    probe_code, pout, perr = _run(
        [
            "docker",
            "exec",
            CONTAINER_NAME,
            "bash",
            "-lc",
            f"source /opt/ros/{distro}/setup.bash; test -f {launch_path} && echo LAUNCH_OK || echo LAUNCH_MISSING",
        ],
        timeout=20.0,
    )
    probe = (pout + perr).strip()

    return {
        "ok": code == 0,
        "demo": demo,
        "package": pkg,
        "launch_file": launch_file,
        "launch_path": launch_path,
        "container": CONTAINER_NAME,
        "ros2_distro": distro,
        "code": code,
        "stdout": out[-1500:],
        "stderr": err[-1500:],
        "probe": probe,
        "probe_code": probe_code,
        "message": (
            "Docker launch started — IDE package tree is mounted at /ws/src; "
            "edit files in the IDE and re-launch to pick up changes"
            if code == 0
            else "docker exec failed — try `lappa docker start` then launch again"
        ),
        "native_fallback": f"lappa sim start --demo {demo}",
        "status": status(),
    }


def stop_launch() -> dict[str, Any]:
    """Best-effort stop of ros2 launch processes inside the container."""
    with _STATE.lock:
        demo = _STATE.demo
        if _STATE.proc is not None and _STATE.proc.poll() is None:
            try:
                _STATE.proc.terminate()
            except OSError:
                pass
        _STATE.proc = None
        if _STATE.mode == "docker_launch":
            _STATE.mode = "docker_runtime"

    if not docker_available():
        return {"ok": True, "stopped": False, "reason": "no docker"}

    # Kill launch/python processes owned by prior lappa launches (best effort)
    code, out, err = _run(
        [
            "docker",
            "exec",
            CONTAINER_NAME,
            "bash",
            "-lc",
            "pkill -f 'ros2 launch' 2>/dev/null || true; "
            "pkill -f 'sim.launch' 2>/dev/null || true; "
            "echo stopped",
        ],
        timeout=15.0,
    )
    with _STATE.lock:
        _STATE.last_log = (out + err).strip() or _STATE.last_log
        if _STATE.mode == "docker_launch":
            _STATE.mode = "docker_runtime"
    return {
        "ok": True,
        "demo": demo,
        "code": code,
        "stdout": out[-500:],
        "status": status(),
    }


def launch_status() -> dict[str, Any]:
    st = status()
    return {
        "session": st.get("session"),
        "container_running": st.get("running"),
        "available": st.get("available"),
        "daemon": st.get("daemon"),
        "ros2_distro": st.get("ros2_distro"),
    }


def show_info() -> dict[str, Any]:
    selected = get_selected()
    return {
        "title": "Docker + IDE sim bridge",
        "ros2_distro": selected,
        "steps": [
            "Open a demo package in the IDE (Explorer / Qt Editor) and edit sources",
            "Pick ROS2 distro (Humble / Jazzy / …)",
            "Start Docker runtime — demos mount at /ws/src",
            "Launch sim in Docker: lappa docker launch --demo <pkg>",
            "Native sim remains the offline fallback when Docker is down",
        ],
        "status": status(),
        "compose": json.dumps({"file": str(DOCKER_DIR / "docker-compose.yml")}),
    }
