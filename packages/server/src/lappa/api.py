from __future__ import annotations

from pathlib import Path
from typing import Any

from lappa import __version__, docker_bridge
from lappa.config import DEMOS_ROOT, IDE_ROOT, ensure_dirs
from lappa.package_loader import list_demo_packages, load_package, read_file, write_file
from lappa.sim.session import SESSION

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel
except ImportError as exc:  # pragma: no cover
    raise ImportError('pip install -e ".[api]"') from exc

ensure_dirs()
app = FastAPI(title="Lappa", version=__version__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active workspace package path (default first demo)
_active: Path | None = None


def _active_package():
    global _active
    if _active and _active.is_dir():
        return load_package(_active)
    packs = list_demo_packages(DEMOS_ROOT)
    if packs:
        _active = packs[0].path
        return packs[0]
    raise HTTPException(404, "no packages")


class FileBody(BaseModel):
    path: str
    content: str


class CmdBody(BaseModel):
    linear_x: float = 0.0
    linear_y: float = 0.0
    angular_z: float = 0.0


class StartBody(BaseModel):
    demo: str = "diff_drive_2w"
    package: str | None = None


class HotReloadBody(BaseModel):
    enabled: bool = True


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "lappa",
        "version": __version__,
        "demos": [p.name for p in list_demo_packages(DEMOS_ROOT)],
        "docker": docker_bridge.status().get("available"),
    }


@app.get("/api/demos")
def api_demos() -> list[dict]:
    return [p.to_dict() for p in list_demo_packages(DEMOS_ROOT)]


@app.post("/api/workspace/open")
def api_open(body: dict[str, str]) -> dict:
    global _active
    raw = body.get("path") or body.get("demo") or ""
    path = Path(raw)
    if not path.is_absolute():
        cand = DEMOS_ROOT / raw
        if cand.is_dir():
            path = cand
        else:
            path = DEMOS_ROOT / raw
    if not path.is_dir():
        raise HTTPException(404, f"not found: {raw}")
    _active = path.resolve()
    pkg = load_package(_active)
    return pkg.to_dict()


@app.get("/api/workspace")
def api_workspace() -> dict:
    return _active_package().to_dict()


@app.get("/api/files")
def api_read(path: str) -> dict:
    pkg = _active_package()
    try:
        content = read_file(pkg, path)
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(400, str(e)) from e
    return {"path": path, "content": content}


@app.put("/api/files")
def api_write(body: FileBody) -> dict:
    pkg = _active_package()
    try:
        write_file(pkg, body.path, body.content)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    SESSION.notify_file_change(body.path)
    return {"ok": True, "path": body.path}


@app.post("/api/sim/start")
def api_sim_start(body: StartBody) -> dict:
    path = Path(body.package) if body.package else DEMOS_ROOT / body.demo
    if not path.is_dir():
        path = DEMOS_ROOT / body.demo
    return SESSION.start(body.demo, path if path.is_dir() else None)


@app.post("/api/sim/stop")
def api_sim_stop() -> dict:
    return SESSION.stop()


@app.get("/api/sim/state")
def api_sim_state() -> dict:
    return SESSION.tick()


@app.get("/api/sim/status")
def api_sim_status() -> dict:
    return SESSION.status()


@app.post("/api/sim/cmd")
def api_sim_cmd(body: CmdBody) -> dict:
    return SESSION.cmd(body.linear_x, body.linear_y, body.angular_z)


@app.post("/api/hot-reload")
def api_hot_reload(body: HotReloadBody) -> dict:
    SESSION.hot_reload = body.enabled
    return {"hot_reload": SESSION.hot_reload}


@app.get("/api/docker/status")
def api_docker_status() -> dict:
    return docker_bridge.status()


@app.get("/api/docker/show")
def api_docker_show() -> dict:
    return docker_bridge.show_info()


@app.post("/api/docker/start")
def api_docker_start() -> dict:
    return docker_bridge.start_runtime()


@app.post("/api/docker/stop")
def api_docker_stop() -> dict:
    return docker_bridge.stop_runtime()


# Static IDE
if IDE_ROOT.is_dir():
    app.mount("/assets", StaticFiles(directory=str(IDE_ROOT / "assets")), name="assets")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(IDE_ROOT / "index.html")
