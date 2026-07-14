# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Lappa desktop / CLI binary.
# Build from packages/server:  pyinstaller lappa.spec

import sys
from pathlib import Path

block_cipher = None

SPECDIR = Path(SPECPATH)
SERVER = SPECDIR
PACKAGES = SERVER.parent
DEMOS = PACKAGES / "demos"
DOCKER = PACKAGES / "docker"

datas = []
if DEMOS.is_dir():
    datas.append((str(DEMOS), "demos"))
if DOCKER.is_dir():
    datas.append((str(DOCKER), "docker"))

hiddenimports = [
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "fastapi",
    "starlette",
    "pydantic",
    "anyio",
    "httpx",
    "watchdog",
    "watchdog.observers",
    "typer",
    "rich",
    "lappa",
    "lappa.api",
    "lappa.cli",
    "lappa.desktop",
    "lappa.paths",
    "lappa.config",
    "lappa.models3d",
    "lappa.packager",
    "lappa.ros2_versions",
    "lappa.docker_bridge",
    "lappa.package_loader",
    "lappa.sim",
    "lappa.sim.engines",
    "lappa.sim.session",
]

a = Analysis(
    [str(SERVER / "src" / "lappa" / "desktop.py")],
    pathex=[str(SERVER / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="lappa",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
