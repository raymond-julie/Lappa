# Lappa

**Lappa** is a **ROS2 package IDE** for Windows-first workflows: open a package, edit, **hot-reload**, and **simulate** without installing a full ROS2 desktop on the host.

| Layer | Role |
| --- | --- |
| **Lappa IDE** | Professional browser IDE (editor, explorer, sim viewport, topics, console) |
| **Lappa Server** | Workspace API, package loader, sim engine, Docker bridge, hot-reload |
| **Demos** | Ready ROS2-style packages: 2-wheel, 3-wheel omni, ackermann, arm base |
| **Docker runtime** | Optional ROS2 Humble container for “real” `ros2` runs + show mode |

Org: [mergeos-bounties](https://github.com/mergeos-bounties) · MergeOS MRG bounties · Project `prj_0352`.

## Screenshots

Live capture from `lappa serve` (native sim, no host ROS2):

### IDE overview — robot demos

![Lappa IDE overview with demo list](docs/screenshots/ide-overview.png)

### Differential drive (2-wheel)

![Diff drive 2w sim with trail](docs/screenshots/sim-diff-drive.png)

### Omnidirectional 3-wheel

![Omni 3w holonomic sim](docs/screenshots/sim-omni-3w.png)

### Planar arm (2-DOF)

![Simple arm kinematics](docs/screenshots/sim-arm.png)

### Docker show mode panel

![Docker show mode status](docs/screenshots/docker-panel.png)

### Tricycle 3-wheel

![Tricycle steered base](docs/screenshots/sim-tricycle.png)

Re-capture locally:

```powershell
# terminal 1
cd packages/server
lappa serve --port 8840

# terminal 2
python scripts/capture_screenshots.py
```

## Why Lappa

- **No host ROS2 required** for demos — built-in kinematics sim streams pose / twist / laser to the IDE.
- **Docker show mode** when Docker Desktop is available — mount the package, run nodes, hot-reload sources.
- **Hot reload** watches package files and restarts or patches the active sim session.
- **Professional IDE chrome** — activity bar, split panes, Monaco editor, dark theme, robot canvas.

## Quick start (Windows, offline)

```powershell
cd D:\ThanhTrucSolutions\Lappa\packages\server
python -m venv .venv
.\.venv\Scripts\activate
pip install -e ".[dev,api]"

lappa demo
lappa serve --port 8840
```

Open **http://127.0.0.1:8840** — IDE loads with demo packages.

```powershell
# CLI
lappa demos list
lappa workspace open demos/diff_drive_2w
lappa sim start --demo diff_drive_2w
lappa sim status
lappa docker status
```

### CLI demo output (offline)

```text
demos: 5  (ackermann_4w, diff_drive_2w, omni_3w, simple_arm, tricycle_3w)
  ackermann_4w: x=0.1  theta≈0.04
  diff_drive_2w: x=0.1  theta≈0.05
  omni_3w: strafe y>0
  simple_arm: FK tip updates
  tricycle_3w: steered arc
docker available=true  daemon=false  (native sim still runs)
Lappa demo complete (offline native sim).
```

## Docker sim (optional)

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```powershell
# From repo root
docker compose -f packages/docker/docker-compose.yml up --build
# or from IDE: Docker → Start runtime
```

The container mounts the active workspace and can run `ros2 launch` for demos. Without Docker, the **native sim** still runs fully offline.

## Demos

| Id | Robot | Notes |
| --- | --- | --- |
| `diff_drive_2w` | Differential 2-wheel | Classic mobile base + lidar rays |
| `omni_3w` | Holonomic 3-wheel | Strafe + rotate |
| `tricycle_3w` | Tricycle / 3-wheel | Steering geometry |
| `ackermann_4w` | Ackermann car-like | Steering angle + wheelbase |
| `simple_arm` | Planar 2-DOF arm | Joint angles (sim) |

Each demo is a ROS2-style package under `packages/demos/` (`package.xml`, `launch/`, `urdf/`, Python nodes).

## Layout

```
packages/
  server/     # Python CLI + FastAPI
  ide/        # Static professional IDE (served by server)
  demos/      # Sample ROS2 packages
  docker/     # ROS2 Humble runtime image + compose
docs/screenshots/
docs/BOUNTY.md
scripts/capture_screenshots.py
```

## MergeOS bounties

1. Star this repo + [mergeos](https://github.com/mergeos-bounties/mergeos)
2. Claim a `bounty` issue
3. Claim on MergeOS [issue #1](https://github.com/mergeos-bounties/mergeos/issues/1)
4. PR to **Lappa** `master` with tests / screenshots
5. Credit MRG 25 / 50 / 100 / 200

See [docs/BOUNTY.md](docs/BOUNTY.md).

## License

MIT
