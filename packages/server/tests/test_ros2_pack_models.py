from pathlib import Path

from lappa import models3d, packager, ros2_versions
from lappa.config import DEMOS_ROOT


def test_ros2_versions_list_and_set():
    versions = ros2_versions.list_versions()
    ids = {v["id"] for v in versions}
    assert "humble" in ids
    assert "jazzy" in ids
    assert "rolling" in ids
    prev = ros2_versions.get_selected()["id"]
    sel = ros2_versions.set_selected("jazzy")
    assert sel["id"] == "jazzy"
    assert "docker_image" in sel
    ros2_versions.set_selected(prev)


def test_package_bundle_zip():
    result = packager.package_bundle(["diff_drive_2w"], distro="humble", out_name="test_bundle_unit")
    assert result["ok"] is True
    path = Path(result["path"])
    assert path.is_file()
    assert path.stat().st_size > 100
    assert result["ros2_distro"] == "humble"
    bundles = packager.list_bundles()
    assert any(b["filename"] == result["filename"] for b in bundles)


def test_mesh_create_and_attach():
    mesh = models3d.create_model("wheel", name="unit_wheel", radius=0.06, height=0.03)
    assert mesh["ok"]
    assert Path(mesh["obj_path"]).is_file()
    assert "v " in Path(mesh["obj_path"]).read_text(encoding="utf-8")
    att = models3d.attach_model_to_package("diff_drive_2w", mesh["id"])
    assert att["ok"]
    assert Path(att["mesh"]).is_file()
    urdf = Path(att["urdf"]).read_text(encoding="utf-8")
    assert "mesh" in urdf
    assert mesh["id"] in urdf
    attachments = models3d.package_attachments("diff_drive_2w")
    assert any(a["model_id"] == mesh["id"] for a in attachments)


def test_all_mesh_presets_generate():
    for preset in models3d.MESH_PRESETS:
        text, meta = models3d.generate_mesh(preset)
        assert text.startswith("#")
        assert "v " in text
        assert meta["preset"] == preset


def test_demos_still_present():
    assert (DEMOS_ROOT / "diff_drive_2w" / "package.xml").is_file()
