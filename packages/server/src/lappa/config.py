from __future__ import annotations

from pathlib import Path

# packages/server → packages → Lappa root
SERVER_ROOT = Path(__file__).resolve().parents[2]
PACKAGES_ROOT = SERVER_ROOT.parent
REPO_ROOT = PACKAGES_ROOT.parent
DEMOS_ROOT = PACKAGES_ROOT / "demos"
IDE_ROOT = PACKAGES_ROOT / "ide"
DOCKER_DIR = PACKAGES_ROOT / "docker"
WORKSPACES = SERVER_ROOT / ".workspaces"


def ensure_dirs() -> None:
    WORKSPACES.mkdir(parents=True, exist_ok=True)
