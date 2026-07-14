"""Path resolution for source installs and frozen PyInstaller builds."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False)) or hasattr(sys, "_MEIPASS")


def bundle_root() -> Path:
    """Read-only resources packaged inside the binary (PyInstaller)."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    # packages/server/src/lappa → packages/server → packages
    return Path(__file__).resolve().parents[2].parent


def app_home() -> Path:
    """Writable directory next to the executable (or server package root)."""
    env = os.environ.get("LAPPA_HOME")
    if env:
        p = Path(env)
        p.mkdir(parents=True, exist_ok=True)
        return p
    if is_frozen():
        p = Path(sys.executable).resolve().parent / "lappa_data"
        p.mkdir(parents=True, exist_ok=True)
        return p
    # packages/server
    return Path(__file__).resolve().parents[2]


def _copy_tree_if_needed(src: Path, dst: Path) -> None:
    if not src.is_dir():
        return
    if dst.is_dir() and any(dst.iterdir()):
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def ensure_runtime_layout() -> dict[str, Path]:
    """
    Resolve demos / docker / workspaces.

    Frozen builds ship demos+docker under _MEIPASS; demos & docker are
    copied once into a writable lappa_data folder beside the executable.
    """
    bundle = bundle_root()
    home = app_home()

    if is_frozen():
        bundled_demos = bundle / "demos"
        bundled_docker = bundle / "docker"
        demos = home / "demos"
        docker = home / "docker"
        _copy_tree_if_needed(bundled_demos, demos)
        _copy_tree_if_needed(bundled_docker, docker)
        workspaces = home / "workspaces"
    else:
        packages = bundle  # packages/
        demos = packages / "demos"
        docker = packages / "docker"
        workspaces = home / ".workspaces"

    workspaces.mkdir(parents=True, exist_ok=True)
    return {
        "bundle": bundle,
        "home": home,
        "demos": demos,
        "docker": docker,
        "workspaces": workspaces,
        "frozen": is_frozen(),  # type: ignore[dict-item]
    }
