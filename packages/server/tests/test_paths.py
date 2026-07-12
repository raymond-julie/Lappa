from lappa.paths import app_home, bundle_root, ensure_runtime_layout, is_frozen


def test_not_frozen_in_dev():
    assert is_frozen() is False


def test_layout_has_demos_and_ide():
    layout = ensure_runtime_layout()
    assert layout["demos"].is_dir()
    assert layout["ide"].is_dir()
    assert (layout["ide"] / "index.html").is_file()
    assert layout["workspaces"].is_dir()
    assert app_home().is_dir()
    assert bundle_root().is_dir()
