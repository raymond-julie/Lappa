"""Docker launch bridge unit tests (no Docker daemon required)."""

import json
from pathlib import Path

from lappa import docker_bridge
from lappa.config import DEMOS_ROOT, DOCKER_DIR


def test_resolve_launch_diff_drive():
    resolved = docker_bridge._resolve_launch("diff_drive_2w")
    assert resolved is not None
    pkg, launch = resolved
    assert pkg == "diff_drive_2w"
    assert launch.endswith(".launch.py")
    assert (DEMOS_ROOT / "diff_drive_2w" / "launch" / launch).is_file()


def test_resolve_launch_unknown():
    assert docker_bridge._resolve_launch("no_such_demo_xyz") is None


def test_launch_demo_missing_returns_error():
    r = docker_bridge.launch_demo("no_such_demo_xyz", ensure_up=False)
    assert r["ok"] is False
    assert "unknown" in r.get("error", "").lower() or "error" in r


def test_launch_status_shape():
    st = docker_bridge.launch_status()
    assert "session" in st
    assert "available" in st


def test_status_includes_session():
    st = docker_bridge.status()
    assert "session" in st
    assert st["session"]["mode"] in ("idle", "docker_runtime", "docker_launch")
    assert "launch" in st
    assert "native_fallback" in st["launch"]


def test_show_info_mentions_ros2_colcon_pipeline():
    info = docker_bridge.show_info()
    steps = " ".join(info.get("steps") or [])
    assert "colcon" in steps.lower() or "ros2 launch" in steps.lower()
    assert "ROS2" in steps or "ros2" in steps.lower()


def test_dockerfile_includes_colcon_and_rclpy():
    from lappa.ros2_versions import dockerfile_for

    df = dockerfile_for("humble")
    assert "colcon" in df
    assert "rclpy" in df
    assert "ros:humble" in df
    assert "ros2_ws.sh" in df
    assert "ros-humble-tf2-ros" in df
    assert "ros-humble-slam-toolbox" in df
    assert "ros-humble-robot-state-publisher" in df
    assert "ros-humble-xacro" in df
    assert "sed -i 's/\\r$//'" in df


def test_ros2_helper_stops_the_recorded_process_group():
    helper = (DOCKER_DIR / "ros2_ws.sh").read_text(encoding="utf-8")
    compose = (DOCKER_DIR / "docker-compose.yml").read_text(encoding="utf-8")

    assert "setsid ros2 launch" in helper
    assert "lappa_ros2_launch.pgid" in helper
    assert 'kill -TERM -- "-${launch_pgid}"' in helper
    assert "ros2 topic pub --once /cmd_vel" in helper
    assert "ros2 topic pub --once /lappa/auto_explore" in helper
    assert "init: true" in compose


def test_publish_twist_uses_active_ros2_helper(monkeypatch):
    monkeypatch.setattr(
        docker_bridge,
        "status",
        lambda: {
            "running": True,
            "session": {"running": True, "demo": "tricycle_3w"},
        },
    )
    captured = {}

    def fake_exec(args, timeout=30.0):
        captured["args"] = args
        captured["timeout"] = timeout
        return 0, "published", ""

    monkeypatch.setattr(docker_bridge, "_exec_ros2_ws", fake_exec)

    result = docker_bridge.publish_twist(0.65, 0.0, 0.55)

    assert result["ok"] is True
    assert captured["args"] == ["twist", "0.6500", "0.0000", "0.5500"]
    assert captured["timeout"] == 15.0


def test_auto_explore_uses_active_ros2_helper(monkeypatch):
    monkeypatch.setattr(
        docker_bridge,
        "status",
        lambda: {
            "running": True,
            "session": {"running": True, "demo": "tricycle_3w"},
        },
    )
    captured = {}

    def fake_exec(args, timeout=30.0):
        captured["args"] = args
        captured["timeout"] = timeout
        return 0, "published", ""

    monkeypatch.setattr(docker_bridge, "_exec_ros2_ws", fake_exec)

    result = docker_bridge.set_auto_explore(True)

    assert result["ok"] is True
    assert result["control"] == "auto_explore"
    assert captured["args"] == ["auto-map", "on"]
    assert captured["timeout"] == 15.0


def test_tricycle_launch_includes_slam_toolbox_and_mapping_params():
    root = DEMOS_ROOT / "tricycle_3w"
    launch = (root / "launch" / "sim.launch.py").read_text(encoding="utf-8")
    params = (root / "config" / "params.yaml").read_text(encoding="utf-8")

    assert 'package="slam_toolbox"' in launch
    assert 'executable="async_slam_toolbox_node"' in launch
    assert 'executable="slam_bridge"' in launch
    assert 'package="robot_state_publisher"' in launch
    assert 'FindExecutable(name="xacro")' in launch
    assert "ParameterValue(" in launch
    assert "map_frame: map" in params
    assert "base_frame: base_link" in params
    assert "lidar_rays: 180" in params
    assert "snapshot_path:" in params

    setup = (root / "setup.py").read_text(encoding="utf-8")
    assert "slam_bridge = tricycle_3w.slam_bridge:main" in setup
    assert 'glob("urdf/*")' in setup
    assert 'glob("worlds/*")' in setup

    xacro = (root / "urdf" / "robot.urdf.xacro").read_text(encoding="utf-8")
    assert 'name="chassis_length" value="0.40"' in xacro
    assert 'name="chassis_width" value="0.26"' in xacro
    assert 'name="chassis_height" value="0.15"' in xacro
    assert "TUPM96/xe_tham_do" in xacro
    assert '<link name="base_footprint"/>' in xacro
    assert 'name="laser_joint" type="fixed"' in xacro

    teleop = (root / "tricycle_3w" / "teleop.py").read_text(encoding="utf-8")
    assert 'transform.child_frame_id = "base_footprint"' in teleop
    assert 'self.declare_parameter("world_map", "warehouse")' in teleop


def test_stop_launch_without_docker_ok(monkeypatch):
    monkeypatch.setattr(docker_bridge, "docker_available", lambda: False)
    r = docker_bridge.stop_launch()
    assert r.get("ok") is True


def test_ensure_container_rejects_unhealthy_runtime(monkeypatch):
    unhealthy = {"running": True, "container_health": "unhealthy"}
    monkeypatch.setattr(docker_bridge, "status", lambda: unhealthy)

    result = docker_bridge._ensure_container()

    assert result["ok"] is False
    assert "unhealthy" in result["error"]


def test_status_explains_when_docker_is_not_installed(monkeypatch):
    monkeypatch.setattr(docker_bridge.shutil, "which", lambda _name: None)
    monkeypatch.setattr(docker_bridge, "docker_desktop_path", lambda: None)

    result = docker_bridge.status()

    assert result["state"] == "not_installed"
    assert result["available"] is False
    assert result["ready_for_start"] is False
    assert "Install Docker Desktop" in result["message"]


def test_status_distinguishes_installed_cli_from_stopped_engine(monkeypatch):
    monkeypatch.setattr(docker_bridge.shutil, "which", lambda _name: "C:/docker.exe")
    monkeypatch.setattr(
        docker_bridge,
        "docker_desktop_path",
        lambda: Path("C:/Program Files/Docker/Docker/Docker Desktop.exe"),
    )

    def fake_run(args, timeout=20.0, *, env=None):
        del timeout, env
        command = " ".join(args)
        if "--version" in command:
            return 0, "Docker version 28.5.1", ""
        if "compose version" in command:
            return 0, "2.40.0", ""
        if "context show" in command:
            return 0, "desktop-linux", ""
        return 1, "", "engine pipe missing"

    monkeypatch.setattr(docker_bridge, "_run", fake_run)
    result = docker_bridge.status()

    assert result["state"] == "engine_stopped"
    assert result["available"] is True
    assert result["daemon"] is False
    assert result["compose_available"] is True
    assert result["docker_desktop_path"].endswith("Docker Desktop.exe")


def test_status_reports_image_container_health_and_launch_readiness(monkeypatch):
    monkeypatch.setattr(docker_bridge.shutil, "which", lambda _name: "/usr/bin/docker")
    monkeypatch.setattr(docker_bridge, "docker_desktop_path", lambda: None)

    def fake_run(args, timeout=20.0, *, env=None):
        del timeout, env
        command = " ".join(args)
        if "--version" in command:
            return 0, "Docker version 28.5.1", ""
        if "compose version" in command:
            return 0, "2.40.0", ""
        if "context show" in command:
            return 0, "desktop-linux", ""
        if " info " in f" {command} ":
            return 0, '"28.5.1"', ""
        if "image inspect" in command:
            return 0, "sha256:test", ""
        if "inspect lappa-ros2" in command:
            state = {"Status": "running", "Health": {"Status": "healthy"}}
            return 0, json.dumps(state), ""
        if "exec lappa-ros2" in command:
            return 0, "running|100|diff_drive_2w", ""
        raise AssertionError(command)

    monkeypatch.setattr(docker_bridge, "_run", fake_run)
    result = docker_bridge.status()

    assert result["state"] == "ready"
    assert result["image_present"] is True
    assert result["running"] is True
    assert result["container_health"] == "healthy"
    assert result["ready_for_launch"] is True
    assert result["session"]["demo"] == "diff_drive_2w"
    assert result["session"]["running"] is True


def test_status_waits_for_container_health_before_launch(monkeypatch):
    monkeypatch.setattr(docker_bridge.shutil, "which", lambda _name: "/usr/bin/docker")
    monkeypatch.setattr(docker_bridge, "docker_desktop_path", lambda: None)

    def fake_run(args, timeout=20.0, *, env=None):
        del timeout, env
        command = " ".join(args)
        if "--version" in command:
            return 0, "Docker version 28.5.1", ""
        if "compose version" in command:
            return 0, "2.40.0", ""
        if "context show" in command:
            return 0, "desktop-linux", ""
        if " info " in f" {command} ":
            return 0, '"28.5.1"', ""
        if "image inspect" in command:
            return 0, "sha256:test", ""
        if "inspect lappa-ros2" in command:
            state = {"Status": "running", "Health": {"Status": "starting"}}
            return 0, json.dumps(state), ""
        if "exec lappa-ros2" in command:
            return 0, "idle||", ""
        raise AssertionError(command)

    monkeypatch.setattr(docker_bridge, "_run", fake_run)
    result = docker_bridge.status()

    assert result["state"] == "container_starting"
    assert result["ready_for_launch"] is False


def test_start_runtime_passes_selected_distro_to_compose(monkeypatch):
    ready = {
        "available": True,
        "daemon": True,
        "compose_available": True,
        "compose_file_exists": True,
        "running": False,
    }
    monkeypatch.setattr(docker_bridge, "status", lambda: ready)
    monkeypatch.setattr(
        docker_bridge,
        "apply_ros2_dockerfile",
        lambda: {"distro": "jazzy", "image_tag": "lappa-ros2:jazzy"},
    )
    captured = {}

    def fake_run(args, timeout=20.0, *, env=None):
        captured["args"] = args
        captured["timeout"] = timeout
        captured["env"] = env
        return 0, "started", ""

    monkeypatch.setattr(docker_bridge, "_run", fake_run)
    result = docker_bridge.start_runtime()

    assert result["ok"] is True
    assert captured["env"]["LAPPA_ROS2_IMAGE"] == "lappa-ros2:jazzy"
    assert captured["env"]["LAPPA_ROS_DISTRO"] == "jazzy"
