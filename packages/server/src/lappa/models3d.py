"""Procedural 3D mesh generation (OBJ) and URDF attachment for robot packages."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from lappa.config import WORKSPACES, ensure_dirs
from lappa.package_loader import load_package
from lappa.packager import resolve_package_path

MESH_PRESETS = {
    "box": {"description": "Axis-aligned box body"},
    "cylinder": {"description": "Vertical cylinder (wheel / pillar)"},
    "sphere": {"description": "Sphere"},
    "wheel": {"description": "Thin cylinder wheel (Y-axis)"},
    "chassis": {"description": "Rounded mobile base plate"},
    "arm_link": {"description": "Elongated link for planar arm"},
    "lidar_dome": {"description": "Hemisphere sensor dome"},
}


def list_presets() -> list[dict[str, str]]:
    return [{"id": k, **v} for k, v in MESH_PRESETS.items()]


def _obj_header(name: str) -> list[str]:
    return [f"# Lappa procedural mesh: {name}", "o " + name]


def _box(sx: float, sy: float, sz: float) -> tuple[list[str], dict]:
    hx, hy, hz = sx / 2, sy / 2, sz / 2
    verts = [
        (-hx, -hy, -hz),
        (hx, -hy, -hz),
        (hx, hy, -hz),
        (-hx, hy, -hz),
        (-hx, -hy, hz),
        (hx, -hy, hz),
        (hx, hy, hz),
        (-hx, hy, hz),
    ]
    faces = [
        (1, 2, 3, 4),
        (5, 8, 7, 6),
        (1, 5, 6, 2),
        (2, 6, 7, 3),
        (3, 7, 8, 4),
        (4, 8, 5, 1),
    ]
    lines = _obj_header("box")
    for v in verts:
        lines.append(f"v {v[0]:.5f} {v[1]:.5f} {v[2]:.5f}")
    for f in faces:
        lines.append("f " + " ".join(str(i) for i in f))
    return lines, {"kind": "box", "size": [sx, sy, sz], "vertices": len(verts)}


def _cylinder(
    radius: float,
    height: float,
    segments: int = 24,
    axis: str = "z",
) -> tuple[list[str], dict]:
    lines = _obj_header("cylinder")
    segs = max(8, min(segments, 64))
    # bottom + top rings + centers
    verts: list[tuple[float, float, float]] = []
    h2 = height / 2

    def put(x: float, y: float, z: float) -> None:
        if axis == "y":
            verts.append((x, z, y))
        elif axis == "x":
            verts.append((z, y, x))
        else:
            verts.append((x, y, z))

    put(0, 0, -h2)
    put(0, 0, h2)
    for i in range(segs):
        a = 2 * math.pi * i / segs
        c, s = math.cos(a) * radius, math.sin(a) * radius
        put(c, s, -h2)
        put(c, s, h2)
    for v in verts:
        lines.append(f"v {v[0]:.5f} {v[1]:.5f} {v[2]:.5f}")
    # indices: 1 bottom center, 2 top center, then pairs
    for i in range(segs):
        b0 = 3 + i * 2
        b1 = 3 + ((i + 1) % segs) * 2
        t0 = b0 + 1
        t1 = b1 + 1
        lines.append(f"f 1 {b0} {b1}")
        lines.append(f"f 2 {t1} {t0}")
        lines.append(f"f {b0} {t0} {t1} {b1}")
    return lines, {
        "kind": "cylinder",
        "radius": radius,
        "height": height,
        "axis": axis,
        "vertices": len(verts),
    }


def _sphere(radius: float, segments: int = 16) -> tuple[list[str], dict]:
    lines = _obj_header("sphere")
    segs = max(8, min(segments, 32))
    verts: list[tuple[float, float, float]] = []
    for i in range(segs + 1):
        phi = math.pi * i / segs
        for j in range(segs):
            theta = 2 * math.pi * j / segs
            x = radius * math.sin(phi) * math.cos(theta)
            y = radius * math.sin(phi) * math.sin(theta)
            z = radius * math.cos(phi)
            verts.append((x, y, z))
    for v in verts:
        lines.append(f"v {v[0]:.5f} {v[1]:.5f} {v[2]:.5f}")
    for i in range(segs):
        for j in range(segs):
            a = i * segs + j + 1
            b = i * segs + (j + 1) % segs + 1
            c = (i + 1) * segs + (j + 1) % segs + 1
            d = (i + 1) * segs + j + 1
            if i < segs:
                lines.append(f"f {a} {b} {c} {d}")
    return lines, {"kind": "sphere", "radius": radius, "vertices": len(verts)}


def _chassis(length: float, width: float, height: float) -> tuple[list[str], dict]:
    # simple tapered box
    return _box(length, width, height)


def _arm_link(length: float, thickness: float) -> tuple[list[str], dict]:
    return _box(length, thickness, thickness)


def _lidar_dome(radius: float, segments: int = 16) -> tuple[list[str], dict]:
    lines = _obj_header("lidar_dome")
    segs = max(8, min(segments, 32))
    verts: list[tuple[float, float, float]] = [(0, 0, 0)]
    for i in range(1, segs // 2 + 1):
        phi = (math.pi / 2) * i / (segs // 2)
        for j in range(segs):
            theta = 2 * math.pi * j / segs
            x = radius * math.sin(phi) * math.cos(theta)
            y = radius * math.sin(phi) * math.sin(theta)
            z = radius * math.cos(phi)
            verts.append((x, y, max(0.0, z)))
    for v in verts:
        lines.append(f"v {v[0]:.5f} {v[1]:.5f} {v[2]:.5f}")
    # fan approx
    for j in range(segs):
        a = 2 + j
        b = 2 + (j + 1) % segs
        lines.append(f"f 1 {a} {b}")
    return lines, {"kind": "lidar_dome", "radius": radius, "vertices": len(verts)}


def generate_mesh(
    preset: str,
    *,
    sx: float = 0.4,
    sy: float = 0.3,
    sz: float = 0.15,
    radius: float = 0.08,
    height: float = 0.05,
    length: float = 0.5,
    thickness: float = 0.06,
    segments: int = 24,
) -> tuple[str, dict[str, Any]]:
    p = (preset or "box").lower()
    if p not in MESH_PRESETS:
        raise ValueError(f"unknown preset {preset}; choose {list(MESH_PRESETS)}")
    if p == "box":
        lines, meta = _box(sx, sy, sz)
    elif p == "cylinder":
        lines, meta = _cylinder(radius, height, segments, axis="z")
    elif p == "sphere":
        lines, meta = _sphere(radius, segments)
    elif p == "wheel":
        lines, meta = _cylinder(radius, height, segments, axis="y")
    elif p == "chassis":
        lines, meta = _chassis(sx, sy, sz)
    elif p == "arm_link":
        lines, meta = _arm_link(length, thickness)
    elif p == "lidar_dome":
        lines, meta = _lidar_dome(radius, segments)
    else:
        lines, meta = _box(sx, sy, sz)
    meta = {**meta, "preset": p}
    return "\n".join(lines) + "\n", meta


def _library_dir() -> Path:
    ensure_dirs()
    d = WORKSPACES / "meshes_library"
    d.mkdir(parents=True, exist_ok=True)
    return d


def create_model(
    preset: str,
    name: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    obj_text, meta = generate_mesh(preset, **kwargs)
    mid = name or f"{preset}_{meta.get('kind', 'mesh')}"
    mid = mid.replace(" ", "_")
    path = _library_dir() / f"{mid}.obj"
    path.write_text(obj_text, encoding="utf-8")
    meta_path = _library_dir() / f"{mid}.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {
        "ok": True,
        "id": mid,
        "obj_path": str(path),
        "meta_path": str(meta_path),
        "meta": meta,
        "bytes": path.stat().st_size,
    }


def list_library() -> list[dict[str, Any]]:
    root = _library_dir()
    out = []
    for p in sorted(root.glob("*.obj")):
        meta_p = p.with_suffix(".json")
        meta = {}
        if meta_p.is_file():
            try:
                meta = json.loads(meta_p.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        out.append({"id": p.stem, "obj_path": str(p), "meta": meta, "bytes": p.stat().st_size})
    return out


def attach_model_to_package(
    package: str,
    model_id: str,
    link_name: str = "base_link",
    xyz: str = "0 0 0.05",
    rpy: str = "0 0 0",
    scale: str = "1 1 1",
) -> dict[str, Any]:
    """Copy mesh into package meshes/ and patch/create urdf visual."""
    pkg_path = resolve_package_path(package)
    lib = _library_dir()
    obj = lib / f"{model_id}.obj"
    if not obj.is_file():
        raise FileNotFoundError(f"model {model_id} not in library — create_model first")

    meshes = pkg_path / "meshes"
    meshes.mkdir(parents=True, exist_ok=True)
    dest = meshes / f"{model_id}.obj"
    dest.write_text(obj.read_text(encoding="utf-8"), encoding="utf-8")
    meta_src = lib / f"{model_id}.json"
    if meta_src.is_file():
        (meshes / f"{model_id}.json").write_text(meta_src.read_text(encoding="utf-8"), encoding="utf-8")

    urdf_dir = pkg_path / "urdf"
    urdf_dir.mkdir(parents=True, exist_ok=True)
    urdf_path = urdf_dir / "robot.urdf"
    pkg = load_package(pkg_path)
    mesh_uri = f"package://{pkg.name}/meshes/{model_id}.obj"

    visual_block = f"""
  <link name="{link_name}">
    <visual>
      <origin xyz="{xyz}" rpy="{rpy}"/>
      <geometry>
        <mesh filename="{mesh_uri}" scale="{scale}"/>
      </geometry>
      <material name="lappa_mesh">
        <color rgba="0.2 0.55 0.95 1"/>
      </material>
    </visual>
    <collision>
      <origin xyz="{xyz}" rpy="{rpy}"/>
      <geometry>
        <mesh filename="{mesh_uri}" scale="{scale}"/>
      </geometry>
    </collision>
  </link>
"""

    if urdf_path.is_file():
        text = urdf_path.read_text(encoding="utf-8")
        if f'name="{link_name}"' in text and "<mesh" in text:
            # append a second visual link variant
            link_name2 = f"{link_name}_mesh"
            visual_block = visual_block.replace(f'name="{link_name}"', f'name="{link_name2}"', 1)
            link_name = link_name2
        if "</robot>" in text:
            text = text.replace("</robot>", visual_block + "\n</robot>")
        else:
            text = text + visual_block
        urdf_path.write_text(text, encoding="utf-8")
    else:
        urdf_path.write_text(
            f"""<?xml version="1.0"?>
<robot name="{pkg.name}">
{visual_block}
</robot>
""",
            encoding="utf-8",
        )

    # attachment registry
    reg = pkg_path / "meshes" / "attachments.json"
    attachments: list[dict[str, Any]] = []
    if reg.is_file():
        try:
            attachments = json.loads(reg.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            attachments = []
    entry = {
        "model_id": model_id,
        "link": link_name,
        "mesh": f"meshes/{model_id}.obj",
        "xyz": xyz,
        "rpy": rpy,
        "scale": scale,
    }
    attachments.append(entry)
    reg.write_text(json.dumps(attachments, indent=2), encoding="utf-8")

    return {
        "ok": True,
        "package": pkg.name,
        "package_path": str(pkg_path),
        "mesh": str(dest),
        "urdf": str(urdf_path),
        "attachment": entry,
        "attachments": attachments,
    }


def package_attachments(package: str) -> list[dict[str, Any]]:
    pkg_path = resolve_package_path(package)
    reg = pkg_path / "meshes" / "attachments.json"
    if not reg.is_file():
        return []
    try:
        return json.loads(reg.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
