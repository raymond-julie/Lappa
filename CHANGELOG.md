# Changelog

All notable Lappa desktop IDE changes are recorded here.

## [0.4.30] - 2026-07-14

### Added

- First-run Welcome screen for opening workspaces and ROS packages.
- RViz-style native simulation view with orbit, top, and follow cameras.
- Layered Docker diagnostics for CLI, engine, Compose, image, health, and ROS2 launch.
- Text and 3D preview for OBJ, STL, DAE, and URDF files in the editor.
- Rich trajectory CSV export with velocity, acceleration, jerk, and rotation columns.
- `list-demos` compatibility command integrated into the primary Typer CLI.

### Changed

- Refined the compact VS Code-style desktop layout and resizable panes.
- Docker work now runs outside the Qt UI thread and refreshes health automatically.
- Frozen releases refresh app-managed Docker helpers while preserving the selected distro.
- Release builds now require lint and tests and publish SHA-256 checksums.

### Fixed

- Prevented splitter repaint flicker and removed the obsolete simulation renderer.
- Fixed ROS environment setup under Bash and UTF-8 BOM errors in sample packages.
- Docker launch now tracks and stops the exact ROS2 process group without broad `pkill` calls.
- Added Docker init process handling so stopped ROS2 nodes do not remain as zombies.

[0.4.30]: https://github.com/mergeos-bounties/Lappa/compare/v0.4.29...v0.4.30
