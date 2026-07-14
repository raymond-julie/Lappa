# Lappa server

Python **CLI + FastAPI automation API** for the Lappa ROS2 package IDE (v0.4).

Full product documentation: **[../../README.md](../../README.md)** (architecture, 3D fit, API, demos, releases).

## Install

```bash
pip install -e ".[dev,gui,api]"
lappa version   # 0.4.25
lappa demo
lappa-gui
```

## Essentials

| Command | Purpose |
| --- | --- |
| `lappa demo` | Offline smoke (sim + 3D robot + bundle) |
| `lappa-gui` / `lappa desktop` | Qt desktop package IDE |
| `lappa serve` | Optional local automation API |
| `lappa model build-robot <demo>` | Full aligned multi-link URDF + meshes |
| `lappa model fit` / `attach` | AABB auto-fit and safe URDF upsert |
| `lappa model scene <demo>` | scene3d JSON for automation/tools |

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
