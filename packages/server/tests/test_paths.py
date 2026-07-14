import tomllib
from pathlib import Path

from lappa import __version__
from lappa.paths import (
    _sync_managed_tree,
    app_home,
    bundle_root,
    ensure_runtime_layout,
    is_frozen,
)


def test_not_frozen_in_dev():
    assert is_frozen() is False


def test_layout_has_demos_and_docker():
    layout = ensure_runtime_layout()
    assert layout["demos"].is_dir()
    assert layout["docker"].is_dir()
    assert layout["workspaces"].is_dir()
    assert app_home().is_dir()
    assert bundle_root().is_dir()


def test_managed_docker_files_refresh_without_replacing_user_state(tmp_path):
    source = tmp_path / "bundle"
    target = tmp_path / "runtime"
    source.mkdir()
    target.mkdir()
    (source / "ros2_ws.sh").write_text("new helper", encoding="utf-8")
    (source / "Dockerfile").write_text("bundled dockerfile", encoding="utf-8")
    (source / "ros2_distro.txt").write_text("humble", encoding="utf-8")
    (target / "ros2_ws.sh").write_text("old helper", encoding="utf-8")
    (target / "Dockerfile").write_text("generated dockerfile", encoding="utf-8")
    (target / "ros2_distro.txt").write_text("jazzy", encoding="utf-8")

    _sync_managed_tree(
        source,
        target,
        preserve={"Dockerfile", "ros2_distro.txt"},
    )

    assert (target / "ros2_ws.sh").read_text(encoding="utf-8") == "new helper"
    assert (target / "Dockerfile").read_text(encoding="utf-8") == "generated dockerfile"
    assert (target / "ros2_distro.txt").read_text(encoding="utf-8") == "jazzy"


def test_package_metadata_matches_runtime_version():
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    metadata = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    assert metadata["project"]["version"] == __version__
