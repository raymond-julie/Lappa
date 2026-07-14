"""Load and inspect ROS2-style packages (package.xml + tree)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RosPackage:
    name: str
    path: Path
    description: str = ""
    version: str = "0.0.0"
    build_type: str = "ament_python"
    files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": str(self.path),
            "description": self.description,
            "version": self.version,
            "build_type": self.build_type,
            "files": self.files,
        }


def _list_files(root: Path, limit: int = 500) -> list[str]:
    out: list[str] = []
    if not root.is_dir():
        return out
    for p in sorted(root.rglob("*")):
        if p.is_file():
            rel = p.relative_to(root).as_posix()
            if any(part.startswith(".") for part in rel.split("/")):
                continue
            out.append(rel)
            if len(out) >= limit:
                break
    return out


def parse_package_xml(path: Path) -> tuple[str, str, str, str]:
    xml = path / "package.xml"
    if not xml.is_file():
        return path.name, "", "0.0.0", "ament_python"
    try:
        root = ET.parse(xml).getroot()
        name = (root.findtext("name") or path.name).strip()
        desc = (root.findtext("description") or "").strip()
        ver = (root.findtext("version") or "0.0.0").strip()
        build = "ament_python"
        for exp in root.findall("export"):
            bt = exp.find("build_type")
            if bt is not None and (bt.text or "").strip():
                build = bt.text.strip()
        return name, desc, ver, build
    except ET.ParseError:
        return path.name, "", "0.0.0", "ament_python"


def load_package(path: Path) -> RosPackage:
    path = path.resolve()
    name, desc, ver, build = parse_package_xml(path)
    return RosPackage(
        name=name,
        path=path,
        description=desc,
        version=ver,
        build_type=build,
        files=_list_files(path),
    )


def list_demo_packages(demos_root: Path) -> list[RosPackage]:
    if not demos_root.is_dir():
        return []
    packs: list[RosPackage] = []
    for child in sorted(demos_root.iterdir()):
        if child.is_dir() and (child / "package.xml").is_file():
            packs.append(load_package(child))
    return packs


def read_file(package: RosPackage, rel: str) -> str:
    root = package.path.resolve()
    target = (root / rel).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        raise ValueError("path escapes package root")
    if not target.is_file():
        raise FileNotFoundError(rel)
    return target.read_text(encoding="utf-8")


def write_file(package: RosPackage, rel: str, content: str) -> None:
    root = package.path.resolve()
    target = (root / rel).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        raise ValueError("path escapes package root")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
