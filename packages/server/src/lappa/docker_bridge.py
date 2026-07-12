"""Docker show-mode bridge (optional; never required for demos)."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from lappa.config import DOCKER_DIR
from lappa.ros2_versions import dockerfile_for, get_selected


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
    # stamp
    stamp = DOCKER_DIR / "ros2_distro.txt"
    stamp.write_text(code + "\n", encoding="utf-8")
    return {"ok": True, "distro": code, "dockerfile": str(path), "image_tag": f"lappa-ros2:{code}"}


def status() -> dict[str, Any]:
    selected = get_selected()
    distro = selected.get("id", "humble")
    image = f"lappa-ros2:{distro}"
    launch_hint = {
        "compose": str(DOCKER_DIR / "docker-compose.yml"),
        "suggested": [
            f"docker compose -f {DOCKER_DIR / 'docker-compose.yml'} up --build",
            f"# ros2 launch after shell: source /opt/ros/{distro}/setup.bash",
        ],
        "native_fallback": "lappa sim start --demo diff_drive_2w",
    }
    if not docker_available():
        return {
            "available": False,
            "daemon": False,
            "message": "Docker CLI not found — use native sim on Windows",
            "compose_file": str(DOCKER_DIR / "docker-compose.yml"),
            "ros2_distro": distro,
            "image": image,
            "launch": launch_hint,
        }
    code, out, err = _run(["docker", "info", "--format", "{{json .ServerVersion}}"])
    daemon = code == 0
    ccode, cout, _ = _run(
        ["docker", "ps", "--filter", "name=lappa-ros2", "--format", "{{.Names}} {{.Status}}"]
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
    # pass image tag via env if compose supports it
    code, out, err = _run(
        ["docker", "compose", "-f", str(compose), "up", "-d", "--build"],
        timeout=180.0,
    )
    return {
        "ok": code == 0,
        "code": code,
        "stdout": out[-2000:],
        "stderr": err[-2000:],
        "dockerfile": applied,
        "status": status(),
    }


def stop_runtime() -> dict[str, Any]:
    compose = DOCKER_DIR / "docker-compose.yml"
    if not compose.is_file():
        return {"ok": False, "error": "missing compose"}
    code, out, err = _run(["docker", "compose", "-f", str(compose), "down"], timeout=60.0)
    return {"ok": code == 0, "stdout": out[-1000:], "stderr": err[-1000:], "status": status()}


def show_info() -> dict[str, Any]:
    selected = get_selected()
    return {
        "title": "Docker show mode",
        "ros2_distro": selected,
        "steps": [
            "Pick ROS2 version in the title bar (Humble / Jazzy / …)",
            "Install Docker Desktop on Windows",
            "Open a demo package in Lappa",
            "Start Docker runtime — Dockerfile is regenerated for that distro",
            "Package sources mount into container; hot-reload syncs edits",
            "Native sim still runs if Docker is offline",
        ],
        "status": status(),
        "compose": json.dumps({"file": str(DOCKER_DIR / "docker-compose.yml")}),
    }
