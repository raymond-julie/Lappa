"""Docker show-mode bridge (optional; never required for demos)."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from lappa.config import DOCKER_DIR


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


def status() -> dict[str, Any]:
    if not docker_available():
        return {
            "available": False,
            "daemon": False,
            "message": "Docker CLI not found — use native sim on Windows",
            "compose_file": str(DOCKER_DIR / "docker-compose.yml"),
        }
    code, out, err = _run(["docker", "info", "--format", "{{json .ServerVersion}}"])
    daemon = code == 0
    # running container?
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
        "image": "lappa-ros2:humble",
    }


def start_runtime(workspace: Path | None = None) -> dict[str, Any]:
    st = status()
    if not st["available"]:
        return {"ok": False, **st}
    if not st["daemon"]:
        return {"ok": False, "error": "Docker daemon not running", **st}
    compose = DOCKER_DIR / "docker-compose.yml"
    if not compose.is_file():
        return {"ok": False, "error": f"missing {compose}"}
    code, out, err = _run(
        ["docker", "compose", "-f", str(compose), "up", "-d", "--build"],
        timeout=180.0,
    )
    return {
        "ok": code == 0,
        "code": code,
        "stdout": out[-2000:],
        "stderr": err[-2000:],
        "status": status(),
    }


def stop_runtime() -> dict[str, Any]:
    compose = DOCKER_DIR / "docker-compose.yml"
    if not compose.is_file():
        return {"ok": False, "error": "missing compose"}
    code, out, err = _run(["docker", "compose", "-f", str(compose), "down"], timeout=60.0)
    return {"ok": code == 0, "stdout": out[-1000:], "stderr": err[-1000:], "status": status()}


def show_info() -> dict[str, Any]:
    """Human-oriented show-mode description for IDE."""
    return {
        "title": "Docker show mode",
        "steps": [
            "Install Docker Desktop on Windows",
            "Open a demo package in Lappa",
            "Start Docker runtime from IDE or `docker compose up`",
            "Package sources mount into container; hot-reload syncs edits",
            "Native sim still runs if Docker is offline",
        ],
        "status": status(),
        "compose": json.dumps({"file": str(DOCKER_DIR / "docker-compose.yml")}),
    }
