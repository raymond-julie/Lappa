# Lappa roadmap

## v0.1 (shipped)

- Qt desktop package IDE (editor, sim, demos, Docker controls)
- Native kinematics sim (2w / 3w omni / tricycle / ackermann / arm)
- Demo ROS2-style packages
- Hot-reload file watch
- Docker status + compose scaffold (Humble)

## v0.2 (shipped)

- Multi-distro ROS2 picker + packager bundles
- Procedural OBJ mesh library + attach to package
- Trajectory CSV export
- Windows/Linux release builds

## v0.3 (shipped — full 3D)

- [x] Mesh AABB parse + auto-fit (`fit_obj_to_box`, `lappa model fit`)
- [x] Safe URDF visual upsert (no duplicate `base_link_mesh` spam)
- [x] `build_aligned_robot` — multi-link chassis + wheels + lidar with kinematic offsets
- [x] Continuous wheel joints + sim joint odometry for spin
- [x] `scene3d` API + package mesh serving
- [x] 3D robot build workflow for package URDF/OBJ assets

## v0.4

- [x] Live Docker `ros2 launch` session bridge (IDE mount + launch_demo) — 2026-07-13
- [x] Qt Editor page open/edit/save package sources — 2026-07-13
- Topic graph panel (nodes / topics)
- Import external OBJ/STL with material colors
- Multi-package workspaces

## Later

- Gazebo / Ignition show mode via Docker
- RViz2/Foxglove bridge
- Colcon build inside container with cache
- Native installer packaging
- Multi-robot fleets
