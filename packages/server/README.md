# Lappa server

Python **CLI + FastAPI** backend for the Lappa ROS2 package IDE (v0.3).

Full product documentation: **[../../README.md](../../README.md)** (architecture, 3D fit, API, demos, releases).

## Install

```bash
pip install -e ".[dev,api]"
lappa version   # 0.3.0+
lappa demo
lappa serve --port 8840
```

## Essentials

| Command | Purpose |
| --- | --- |
| `lappa demo` | Offline smoke (sim + 3D robot + bundle) |
| `lappa serve` / `lappa desktop` | IDE at http://127.0.0.1:8840 |
| `lappa model build-robot <demo>` | Full aligned multi-link URDF + meshes |
| `lappa model fit` / `attach` | AABB auto-fit and safe URDF upsert |
| `lappa model scene <demo>` | scene3d JSON for WebGL |

## Quality

```bash
pytest -q
ruff check src tests
```

## Package layout

```text
src/lappa/
  api.py          # FastAPI routes
  models3d.py     # mesh gen, fit, build-robot, scene3d
  sim/engines.py  # native kinematics + joints
  packager.py     # ROS2 zip bundles
  docker_bridge.py
  cli.py
```
