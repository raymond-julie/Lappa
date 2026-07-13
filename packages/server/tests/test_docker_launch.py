"""Docker launch bridge unit tests (no Docker daemon required)."""

from lappa import docker_bridge
from lappa.config import DEMOS_ROOT


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


def test_show_info_mentions_ide_bridge():
    info = docker_bridge.show_info()
    steps = " ".join(info.get("steps") or [])
    assert "IDE" in steps or "edit" in steps.lower()


def test_stop_launch_without_docker_ok():
    r = docker_bridge.stop_launch()
    assert r.get("ok") is True
