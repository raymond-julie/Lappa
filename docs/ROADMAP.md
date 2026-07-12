# Lappa roadmap

## v0.1 (shipped)

- Professional web IDE shell (Monaco, explorer, sim, console)
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
- [x] IDE WebGL 3D viewer (Three.js), 2D/3D toggle, orbit camera

## v0.4

- Live Docker `ros2 launch` session bridge
- Topic graph panel (nodes / topics)
- Import external OBJ/STL with material colors
- Multi-package workspaces

## Later

- Gazebo / Ignition show mode via Docker
- RViz2 web bridge (Foxglove / rosbridge)
- Colcon build inside container with cache
- Electron / Tauri desktop shell
- Multi-robot fleets
