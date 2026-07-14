from pathlib import Path

import pytest

from lappa.package_loader import RosPackage, read_file, write_file


def test_read_file_blocks_sibling_prefix_escape(tmp_path: Path):
    root = tmp_path / "pkg"
    sibling = tmp_path / "pkg_evil"
    root.mkdir()
    sibling.mkdir()
    (sibling / "secret.txt").write_text("outside", encoding="utf-8")

    pkg = RosPackage(name="pkg", path=root)
    with pytest.raises(ValueError, match="path escapes package root"):
        read_file(pkg, "../pkg_evil/secret.txt")


def test_write_file_blocks_sibling_prefix_escape(tmp_path: Path):
    root = tmp_path / "pkg"
    sibling = tmp_path / "pkg_evil"
    root.mkdir()
    sibling.mkdir()

    pkg = RosPackage(name="pkg", path=root)
    with pytest.raises(ValueError, match="path escapes package root"):
        write_file(pkg, "../pkg_evil/written.txt", "escaped")

    assert not (sibling / "written.txt").exists()
