from __future__ import annotations

from pathlib import Path

from lappa.paths import app_home, ensure_runtime_layout, is_frozen

_layout = ensure_runtime_layout()

SERVER_ROOT = app_home() if is_frozen() else Path(__file__).resolve().parents[2]
PACKAGES_ROOT = _layout["demos"].parent if is_frozen() else SERVER_ROOT.parent
REPO_ROOT = PACKAGES_ROOT.parent if not is_frozen() else SERVER_ROOT
DEMOS_ROOT: Path = _layout["demos"]  # type: ignore[assignment]
IDE_ROOT: Path = _layout["ide"]  # type: ignore[assignment]
DOCKER_DIR: Path = _layout["docker"]  # type: ignore[assignment]
WORKSPACES: Path = _layout["workspaces"]  # type: ignore[assignment]


def ensure_dirs() -> None:
    global _layout, DEMOS_ROOT, IDE_ROOT, DOCKER_DIR, WORKSPACES
    _layout = ensure_runtime_layout()
    DEMOS_ROOT = _layout["demos"]  # type: ignore[assignment]
    IDE_ROOT = _layout["ide"]  # type: ignore[assignment]
    DOCKER_DIR = _layout["docker"]  # type: ignore[assignment]
    WORKSPACES = _layout["workspaces"]  # type: ignore[assignment]
    WORKSPACES.mkdir(parents=True, exist_ok=True)
