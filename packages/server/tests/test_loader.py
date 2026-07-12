from lappa.config import DEMOS_ROOT
from lappa.package_loader import list_demo_packages, read_file


def test_demos_exist():
    packs = list_demo_packages(DEMOS_ROOT)
    assert len(packs) >= 5
    names = {p.name for p in packs}
    assert "diff_drive_2w" in names
    assert "omni_3w" in names


def test_load_package_xml():
    packs = list_demo_packages(DEMOS_ROOT)
    p = packs[0]
    assert p.version
    assert p.files
    assert "package.xml" in p.files


def test_read_package_xml():
    packs = list_demo_packages(DEMOS_ROOT)
    text = read_file(packs[0], "package.xml")
    assert "<package" in text or "package" in text
