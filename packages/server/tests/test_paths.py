from lappa.paths import app_home, bundle_root, ensure_runtime_layout, is_frozen


def test_not_frozen_in_dev():
    assert is_frozen() is False


def test_layout_has_demos_and_docker():
    layout = ensure_runtime_layout()
    assert layout["demos"].is_dir()
    assert layout["docker"].is_dir()
    assert layout["workspaces"].is_dir()
    assert app_home().is_dir()
    assert bundle_root().is_dir()
