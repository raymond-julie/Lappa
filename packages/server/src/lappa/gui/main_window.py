"""Lappa Qt desktop IDE: package editor with live native simulation."""

from __future__ import annotations

import json
import math
import threading
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QPointF, QSettings, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QDesktopServices,
    QFont,
    QFontDatabase,
    QIcon,
    QKeySequence,
    QPainter,
    QPen,
    QPixmap,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QComboBox,
    QCheckBox,
    QApplication,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QTabWidget,
    QTextEdit,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from lappa import __version__, docker_bridge, models3d, packager, ros2_versions, workspace
from lappa.config import DEMOS_ROOT, ensure_dirs
from lappa.gui.styles import STYLESHEET
from lappa.package_loader import RosPackage, load_package, read_file, write_file
from lappa.sim.engines import DEFAULT_OBSTACLES
from lappa.sim.session import SESSION


WELCOME_SETTINGS_KEY = "onboarding/welcome_seen"


def _button(text: str, *, primary: bool = False, compact: bool = False) -> QPushButton:
    b = QPushButton(text)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setProperty("primary", primary)
    b.setProperty("compact", compact)
    return b


def _icon(name: str, color: str = "#c9d1d9", accent: str = "#58a6ff") -> QIcon:
    pix = QPixmap(24, 24)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), 2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    if name == "explorer":
        painter.drawRoundedRect(6, 4, 11, 16, 2, 2)
        painter.drawLine(9, 8, 15, 8)
        painter.drawLine(9, 12, 15, 12)
        painter.drawLine(9, 16, 13, 16)
    elif name == "folder":
        painter.drawRoundedRect(3, 7, 18, 12, 2, 2)
        painter.drawLine(4, 7, 9, 7)
        painter.drawLine(9, 7, 11, 5)
        painter.drawLine(11, 5, 17, 5)
    elif name == "file":
        painter.drawRoundedRect(7, 4, 11, 16, 2, 2)
        painter.drawLine(14, 4, 18, 8)
        painter.drawLine(14, 4, 14, 8)
        painter.drawLine(14, 8, 18, 8)
    elif name == "file-plus":
        painter.drawRoundedRect(7, 4, 11, 16, 2, 2)
        painter.drawLine(12, 11, 12, 17)
        painter.drawLine(9, 14, 15, 14)
    elif name == "folder-plus":
        painter.drawRoundedRect(3, 7, 18, 12, 2, 2)
        painter.drawLine(5, 7, 10, 7)
        painter.drawLine(10, 7, 12, 5)
        painter.drawLine(12, 5, 17, 5)
        painter.drawLine(12, 10, 12, 16)
        painter.drawLine(9, 13, 15, 13)
    elif name == "refresh":
        painter.drawArc(5, 5, 14, 14, 30 * 16, 285 * 16)
        painter.drawLine(17, 5, 19, 10)
        painter.drawLine(17, 5, 12, 6)
    elif name == "play":
        painter.setBrush(QColor(accent))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon([QPointF(8, 5), QPointF(19, 12), QPointF(8, 19)])
    elif name == "stop":
        painter.setBrush(QColor("#0b0f17"))
        painter.setPen(QPen(QColor(color), 2))
        painter.drawRoundedRect(7, 7, 10, 10, 2, 2)
    elif name == "save":
        painter.drawRoundedRect(5, 4, 14, 16, 2, 2)
        painter.drawRect(8, 4, 7, 5)
        painter.drawLine(8, 16, 16, 16)
    elif name == "ai":
        painter.setPen(QPen(QColor(accent), 2))
        painter.drawEllipse(5, 5, 14, 14)
        painter.drawLine(12, 3, 12, 6)
        painter.drawLine(12, 18, 12, 21)
        painter.drawLine(3, 12, 6, 12)
        painter.drawLine(18, 12, 21, 12)
        painter.drawPoint(10, 11)
        painter.drawPoint(14, 11)
    elif name == "cube":
        painter.drawPolygon([QPointF(12, 4), QPointF(20, 8), QPointF(12, 12), QPointF(4, 8)])
        painter.drawLine(4, 8, 4, 16)
        painter.drawLine(20, 8, 20, 16)
        painter.drawLine(12, 12, 12, 21)
        painter.drawLine(4, 16, 12, 21)
        painter.drawLine(20, 16, 12, 21)
    elif name == "docker":
        painter.drawRoundedRect(4, 8, 16, 10, 2, 2)
        painter.drawRect(7, 5, 4, 3)
        painter.drawRect(12, 5, 4, 3)
        painter.drawLine(6, 18, 18, 18)
    elif name == "reset":
        painter.drawArc(5, 5, 14, 14, 70 * 16, 250 * 16)
        painter.drawLine(6, 8, 6, 3)
        painter.drawLine(6, 8, 11, 8)
    else:
        painter.drawEllipse(7, 7, 10, 10)

    painter.end()
    return QIcon(pix)


def _tool_button(
    icon: str,
    tooltip: str = "",
) -> QToolButton:
    b = QToolButton()
    b.setIcon(_icon(icon))
    b.setIconSize(QSize(18, 18))
    b.setToolTip(tooltip)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
    b.setFixedSize(QSize(42, 34))
    return b


def _toolbar_button(
    icon: str,
    tooltip: str = "",
    width: int = 30,
) -> QToolButton:
    b = QToolButton()
    b.setIcon(_icon(icon))
    b.setIconSize(QSize(17, 17))
    b.setToolTip(tooltip)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
    b.setFixedSize(QSize(width, 28))
    return b


def _section(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("sectionTitle")
    return label


def _metric(title: str) -> tuple[QFrame, QLabel]:
    card = QFrame()
    card.setObjectName("metricCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(8, 5, 8, 5)
    layout.setSpacing(2)
    t = QLabel(title)
    t.setObjectName("metricTitle")
    value = QLabel("-")
    value.setObjectName("metricValue")
    layout.addWidget(t)
    layout.addWidget(value)
    return card, value


class SimCanvas(QWidget):
    """Interactive RViz-style viewport for the native simulator."""

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumSize(360, 300)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.state: dict = {
            "x": 0.0,
            "y": 0.0,
            "theta": 0.0,
            "kind": "diff_drive_2w",
            "lidar": [],
            "running": False,
        }
        self.trail: list[tuple[float, float]] = []
        self.view_mode = "Orbit"
        self.camera_yaw = math.radians(-42)
        self.zoom = 1.0
        self.show_grid = True
        self.show_laser = True
        self.show_trail = True
        self._drag_position: QPointF | None = None
        self.setMouseTracking(True)

    def set_state(self, st: dict) -> None:
        self.state = st or self.state
        if st:
            x, y = float(st.get("x") or 0.0), float(st.get("y") or 0.0)
            self.trail.append((x, y))
            if len(self.trail) > 260:
                self.trail = self.trail[-260:]
        self.update()

    def clear_trail(self) -> None:
        self.trail.clear()
        self.update()

    def set_view_mode(self, mode: str) -> None:
        self.view_mode = mode if mode in {"Orbit", "Top", "Follow"} else "Orbit"
        if self.view_mode == "Top":
            self.camera_yaw = 0.0
        elif self.view_mode == "Orbit":
            self.camera_yaw = math.radians(-42)
        self.update()

    def reset_view(self) -> None:
        self.zoom = 1.0
        self.camera_yaw = 0.0 if self.view_mode == "Top" else math.radians(-42)
        self.update()

    def set_grid_visible(self, visible: bool) -> None:
        self.show_grid = visible
        self.update()

    def set_laser_visible(self, visible: bool) -> None:
        self.show_laser = visible
        self.update()

    def set_trail_visible(self, visible: bool) -> None:
        self.show_trail = visible
        self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self.view_mode != "Top":
            self._drag_position = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_position is not None:
            delta = event.position() - self._drag_position
            self.camera_yaw += delta.x() * 0.008
            self._drag_position = event.position()
            self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self._drag_position is not None:
            self._drag_position = None
            self.unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event) -> None:  # noqa: N802
        factor = 1.1 if event.angleDelta().y() > 0 else 1 / 1.1
        self.zoom = min(2.4, max(0.55, self.zoom * factor))
        self.update()
        event.accept()

    def _project(self, x: float, y: float, z: float = 0.0) -> QPointF:
        focus_x = float(self.state.get("x") or 0.0) if self.view_mode == "Follow" else 0.0
        focus_y = float(self.state.get("y") or 0.0) if self.view_mode == "Follow" else 0.0
        dx, dy = x - focus_x, y - focus_y
        scale = min(self.width(), self.height()) / 8.2 * self.zoom
        cx = self.width() * 0.5
        if self.view_mode == "Top":
            cy = self.height() * 0.52
            return QPointF(cx + dx * scale, cy - dy * scale - z * scale * 0.12)
        side = dx * math.cos(self.camera_yaw) - dy * math.sin(self.camera_yaw)
        depth = dx * math.sin(self.camera_yaw) + dy * math.cos(self.camera_yaw)
        return QPointF(
            cx + side * scale,
            self.height() * 0.56 + depth * scale * 0.48 - z * scale * 0.92,
        )

    @staticmethod
    def _shade(color: QColor, factor: float) -> QColor:
        return QColor(
            max(0, min(255, int(color.red() * factor))),
            max(0, min(255, int(color.green() * factor))),
            max(0, min(255, int(color.blue() * factor))),
            color.alpha(),
        )

    def _draw_world_box(
        self,
        painter: QPainter,
        cx: float,
        cy: float,
        half_w: float,
        half_h: float,
        height: float,
        color: QColor,
    ) -> None:
        bottom = [
            self._project(cx - half_w, cy - half_h),
            self._project(cx + half_w, cy - half_h),
            self._project(cx + half_w, cy + half_h),
            self._project(cx - half_w, cy + half_h),
        ]
        top = [
            self._project(cx - half_w, cy - half_h, height),
            self._project(cx + half_w, cy - half_h, height),
            self._project(cx + half_w, cy + half_h, height),
            self._project(cx - half_w, cy + half_h, height),
        ]
        painter.setPen(QPen(self._shade(color, 1.25), 1))
        for index in range(4):
            face = QPolygonF(
                [bottom[index], bottom[(index + 1) % 4], top[(index + 1) % 4], top[index]]
            )
            painter.setBrush(self._shade(color, 0.62 + index * 0.07))
            painter.drawPolygon(face)
        painter.setBrush(color)
        painter.drawPolygon(QPolygonF(top))

    @staticmethod
    def _robot_world_point(
        x: float,
        y: float,
        theta: float,
        local_x: float,
        local_y: float,
    ) -> tuple[float, float]:
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        return (
            x + local_x * cos_t - local_y * sin_t,
            y + local_x * sin_t + local_y * cos_t,
        )

    def _draw_robot_box(
        self,
        painter: QPainter,
        x: float,
        y: float,
        theta: float,
        color: QColor,
    ) -> None:
        locals_ = [(-0.34, -0.23), (0.34, -0.23), (0.34, 0.23), (-0.34, 0.23)]
        world = [self._robot_world_point(x, y, theta, px, py) for px, py in locals_]
        bottom = [self._project(px, py, 0.05) for px, py in world]
        top = [self._project(px, py, 0.32) for px, py in world]
        painter.setPen(QPen(self._shade(color, 1.28), 1))
        for index in range(4):
            painter.setBrush(self._shade(color, 0.58 + index * 0.08))
            painter.drawPolygon(
                QPolygonF(
                    [bottom[index], bottom[(index + 1) % 4], top[(index + 1) % 4], top[index]]
                )
            )
        painter.setBrush(color)
        painter.drawPolygon(QPolygonF(top))
        nose = self._robot_world_point(x, y, theta, 0.52, 0.0)
        painter.setPen(QPen(QColor("#d7f2ff"), 2))
        painter.drawLine(self._project(x, y, 0.36), self._project(*nose, 0.36))
        painter.setBrush(QColor("#d7f2ff"))
        painter.drawEllipse(self._project(*nose, 0.36), 2.5, 2.5)

    def _draw_arm_3d(self, painter: QPainter) -> None:
        joints = self.state.get("joints") or [0.4, -0.6]
        j0 = float(joints[0]) if joints else 0.4
        j1 = float(joints[1]) if len(joints) > 1 else -0.6
        base = (0.0, 0.0, 0.26)
        elbow = (0.64 * math.cos(j0), 0.0, 0.34 + 0.64 * math.sin(j0))
        tool = (
            elbow[0] + 0.48 * math.cos(j0 + j1),
            0.0,
            elbow[2] + 0.48 * math.sin(j0 + j1),
        )
        self._draw_world_box(painter, 0.0, 0.0, 0.28, 0.28, 0.24, QColor("#3e7cb8"))
        painter.setPen(QPen(QColor("#a987e8"), 7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(self._project(*base), self._project(*elbow))
        painter.drawLine(self._project(*elbow), self._project(*tool))
        painter.setBrush(QColor("#65b7ef"))
        painter.setPen(QPen(QColor("#d7f2ff"), 1))
        for point in (base, elbow, tool):
            painter.drawEllipse(self._project(*point), 5, 5)

    def _draw_overlay(self, painter: QPainter) -> None:
        kind = str(self.state.get("kind") or "diff_drive_2w")
        x = float(self.state.get("x") or 0.0)
        y = float(self.state.get("y") or 0.0)
        theta = float(self.state.get("theta") or 0.0)
        painter.setFont(QFont("Segoe UI", 9))
        painter.setPen(QColor("#b7c8da"))
        painter.setBrush(QColor(8, 15, 27, 220))
        painter.drawRoundedRect(10, 10, 210, 48, 4, 4)
        painter.drawText(20, 30, f"Fixed Frame: map    View: {self.view_mode}")
        painter.setPen(QColor("#7f94aa"))
        painter.drawText(20, 49, "Native kinematics | 1 m grid")

        pose_text = f"{kind}   x {x:.2f}   y {y:.2f}   yaw {theta:.2f}"
        text_width = painter.fontMetrics().horizontalAdvance(pose_text) + 20
        painter.setBrush(QColor(8, 15, 27, 220))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(10, self.height() - 38, text_width, 28, 4, 4)
        painter.setPen(QColor("#b7c8da"))
        painter.drawText(20, self.height() - 19, pose_text)

        origin = QPointF(self.width() - 48, self.height() - 42)
        painter.setPen(QPen(QColor("#ff6b6b"), 2))
        painter.drawLine(origin, origin + QPointF(22, 0))
        painter.drawText(origin + QPointF(25, 4), "X")
        painter.setPen(QPen(QColor("#55d187"), 2))
        painter.drawLine(origin, origin + QPointF(-12, -16))
        painter.drawText(origin + QPointF(-21, -18), "Y")
        painter.setPen(QPen(QColor("#58a6ff"), 2))
        painter.drawLine(origin, origin + QPointF(0, -24))
        painter.drawText(origin + QPointF(4, -25), "Z")

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#07101c"))
        painter.fillRect(0, int(self.height() * 0.43), self.width(), self.height(), QColor("#0a1624"))

        if self.show_grid:
            for grid_value in range(-6, 7):
                major = grid_value == 0
                color = QColor("#31455d") if major else QColor("#17283a")
                painter.setPen(QPen(color, 2 if major else 1))
                painter.drawLine(
                    self._project(grid_value, -6), self._project(grid_value, 6)
                )
                painter.drawLine(
                    self._project(-6, grid_value), self._project(6, grid_value)
                )

        axis_origin = self._project(0, 0, 0.02)
        painter.setPen(QPen(QColor("#d75a64"), 2))
        painter.drawLine(axis_origin, self._project(1.0, 0, 0.02))
        painter.setPen(QPen(QColor("#4cb879"), 2))
        painter.drawLine(axis_origin, self._project(0, 1.0, 0.02))
        painter.setPen(QPen(QColor("#4f91d9"), 2))
        painter.drawLine(axis_origin, self._project(0, 0, 1.0))

        if self.show_trail and len(self.trail) > 1:
            painter.setPen(QPen(QColor(77, 157, 224, 180), 2))
            for previous, current in zip(self.trail, self.trail[1:]):
                painter.drawLine(
                    self._project(previous[0], previous[1], 0.035),
                    self._project(current[0], current[1], 0.035),
                )

        obstacles = self.state.get("obstacles") or DEFAULT_OBSTACLES
        for obstacle in sorted(obstacles, key=lambda item: item[0] + item[1]):
            ox, oy, half_w, half_h = [float(value) for value in obstacle]
            self._draw_world_box(
                painter, ox, oy, half_w, half_h, 0.42, QColor("#354960")
            )

        x = float(self.state.get("x") or 0.0)
        y = float(self.state.get("y") or 0.0)
        theta = float(self.state.get("theta") or 0.0)
        lidar = self.state.get("lidar") or []
        if self.show_laser and lidar:
            sensor = self._project(x, y, 0.38)
            painter.setPen(QPen(QColor(70, 210, 130, 68), 1))
            for index, distance in enumerate(lidar):
                angle = theta + index / len(lidar) * math.tau
                endpoint = (
                    x + math.cos(angle) * float(distance),
                    y + math.sin(angle) * float(distance),
                )
                projected = self._project(*endpoint, 0.05)
                painter.drawLine(sensor, projected)
                painter.setBrush(QColor("#4bd487"))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(projected, 1.8, 1.8)
                painter.setPen(QPen(QColor(70, 210, 130, 68), 1))

        kind = str(self.state.get("kind") or "diff_drive_2w")
        if kind == "simple_arm":
            self._draw_arm_3d(painter)
        else:
            colors = {
                "diff_drive_2w": QColor("#4da86d"),
                "omni_3w": QColor("#3f83cc"),
                "mecanum_4w": QColor("#4f8fcf"),
                "ackermann_4w": QColor("#c49a45"),
                "tricycle_3w": QColor("#8f70c5"),
            }
            self._draw_robot_box(painter, x, y, theta, colors.get(kind, QColor("#4da86d")))
        self._draw_overlay(painter)


class ModelPreview(QWidget):
    """Lightweight 3D/wireframe preview for mesh-like files."""

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumSize(280, 220)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.vertices: list[tuple[float, float, float]] = []
        self.edges: list[tuple[int, int]] = []
        self.summary = "No 3D file"

    def load_text(self, rel: str, text: str) -> None:
        suffix = Path(rel).suffix.lower()
        if suffix == ".obj":
            self._load_obj(text)
        elif suffix == ".stl":
            self._load_stl(text)
        elif suffix == ".dae":
            self._load_dae(text)
        elif suffix in {".urdf", ".xml"}:
            self._load_urdf(text)
        else:
            self.vertices = []
            self.edges = []
            self.summary = f"{suffix or 'file'} preview"
        self.update()

    def _load_obj(self, text: str) -> None:
        vertices: list[tuple[float, float, float]] = []
        edges: set[tuple[int, int]] = set()
        for line in text.splitlines():
            parts = line.strip().split()
            if not parts:
                continue
            if parts[0] == "v" and len(parts) >= 4:
                try:
                    vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
                except ValueError:
                    continue
            elif parts[0] == "f" and len(parts) >= 3:
                face: list[int] = []
                for raw in parts[1:]:
                    try:
                        idx = int(raw.split("/")[0])
                    except ValueError:
                        continue
                    if idx < 0:
                        idx = len(vertices) + idx + 1
                    face.append(idx - 1)
                for a, b in zip(face, face[1:] + face[:1]):
                    if a >= 0 and b >= 0:
                        edges.add(tuple(sorted((a, b))))
        self.vertices = vertices[:3000]
        self.edges = [(a, b) for a, b in edges if a < len(self.vertices) and b < len(self.vertices)]
        self.summary = f"OBJ  {len(vertices)} vertices  {len(edges)} edges"

    def _load_stl(self, text: str) -> None:
        vertices: list[tuple[float, float, float]] = []
        edges: set[tuple[int, int]] = set()
        face: list[int] = []
        for line in text.splitlines():
            parts = line.strip().split()
            if len(parts) == 4 and parts[0].lower() == "vertex":
                try:
                    vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
                    face.append(len(vertices) - 1)
                    if len(face) == 3:
                        for a, b in zip(face, face[1:] + face[:1]):
                            edges.add(tuple(sorted((a, b))))
                        face = []
                except ValueError:
                    continue
        self.vertices = vertices[:3000]
        self.edges = [(a, b) for a, b in edges if a < len(self.vertices) and b < len(self.vertices)]
        self.summary = f"STL  {len(vertices)} vertices  {len(edges)} edges"

    def _load_urdf(self, text: str) -> None:
        import re

        meshes = re.findall(r'filename=["\']([^"\']+)["\']', text)
        joints = re.findall(r"<joint\b", text)
        links = re.findall(r"<link\b", text)
        self.vertices = []
        self.edges = []
        self.summary = f"URDF  {len(links)} links  {len(joints)} joints  {len(meshes)} mesh refs"

    def _load_dae(self, text: str) -> None:
        import re

        geometries = re.findall(r"<geometry\b", text)
        sources = re.findall(r"<source\b", text)
        triangles = re.findall(r"<triangles\b", text)
        self.vertices = []
        self.edges = []
        self.summary = (
            f"DAE  {len(geometries)} geometries  {len(sources)} sources  "
            f"{len(triangles)} triangle sets"
        )

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QColor("#080d18"))

        painter.setPen(QPen(QColor("#1d2b3d"), 1))
        for x in range(0, w, 32):
            painter.drawLine(x, 0, x, h)
        for y in range(0, h, 32):
            painter.drawLine(0, y, w, y)

        painter.setPen(QColor("#9fb3c8"))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(12, 22, self.summary)

        if not self.vertices:
            painter.setPen(QColor("#5f7390"))
            painter.drawText(12, 48, "3D preview appears here for OBJ/STL. URDF shows structure summary.")
            return

        xs = [v[0] for v in self.vertices]
        ys = [v[1] for v in self.vertices]
        zs = [v[2] for v in self.vertices]
        cx, cy, cz = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2
        span = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs), 1e-6)
        scale = min(w, h) * 0.62 / span

        def project(v: tuple[float, float, float]) -> QPointF:
            x, y, z = v[0] - cx, v[1] - cy, v[2] - cz
            px = (x - y) * 0.78
            py = (x + y) * 0.34 - z
            return QPointF(w / 2 + px * scale, h / 2 + py * scale)

        painter.setPen(QPen(QColor("#58a6ff"), 1))
        for a, b in self.edges[:8000]:
            painter.drawLine(project(self.vertices[a]), project(self.vertices[b]))
        painter.setPen(QPen(QColor("#7dd3fc"), 3))
        for vertex in self.vertices[:120]:
            painter.drawPoint(project(vertex))


class WelcomePage(QFrame):
    """First-run entry point for opening a ROS workspace."""

    open_workspace_requested = Signal()
    open_package_requested = Signal()
    new_workspace_requested = Signal()
    continue_requested = Signal()
    package_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("welcomePage")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(44, 32, 44, 32)
        outer.setSpacing(0)
        outer.addStretch(1)

        stage = QFrame()
        stage.setObjectName("welcomeStage")
        stage.setMaximumWidth(980)
        stage_layout = QVBoxLayout(stage)
        stage_layout.setContentsMargins(0, 0, 0, 0)
        stage_layout.setSpacing(24)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(12)
        icon_label = QLabel()
        icon_label.setObjectName("welcomeIcon")
        icon_label.setFixedSize(48, 48)
        app = QApplication.instance()
        icon = app.windowIcon() if app else QIcon()
        if not icon.isNull():
            icon_label.setPixmap(icon.pixmap(48, 48))
        brand_row.addWidget(icon_label)

        brand_stack = QVBoxLayout()
        brand_stack.setSpacing(0)
        brand = QLabel("Lappa")
        brand.setObjectName("welcomeBrand")
        product = QLabel("ROS2 PACKAGE IDE")
        product.setObjectName("welcomeProduct")
        brand_stack.addWidget(brand)
        brand_stack.addWidget(product)
        brand_row.addLayout(brand_stack)
        brand_row.addStretch(1)
        version = QLabel(f"Version {__version__}")
        version.setObjectName("welcomeVersion")
        brand_row.addWidget(version, 0, Qt.AlignmentFlag.AlignTop)
        stage_layout.addLayout(brand_row)

        headline = QLabel("Start with a ROS2 workspace")
        headline.setObjectName("welcomeTitle")
        subtitle = QLabel(
            "Open package source, inspect robot models, and run simulation in one workbench."
        )
        subtitle.setObjectName("welcomeSubtitle")
        subtitle.setWordWrap(True)
        stage_layout.addWidget(headline)
        stage_layout.addWidget(subtitle)

        columns = QHBoxLayout()
        columns.setSpacing(34)

        actions = QFrame()
        actions.setObjectName("welcomeActions")
        actions.setMinimumWidth(330)
        actions_layout = QVBoxLayout(actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(9)
        actions_layout.addWidget(_section("Start"))

        open_workspace = self._action_button("Open Workspace", "folder", primary=True)
        open_workspace.setToolTip("Add a folder containing one or more ROS2 packages")
        open_workspace.clicked.connect(lambda: self.open_workspace_requested.emit())
        actions_layout.addWidget(open_workspace)

        open_package = self._action_button("Open ROS Package", "cube")
        open_package.setToolTip("Open a folder that contains package.xml")
        open_package.clicked.connect(lambda: self.open_package_requested.emit())
        actions_layout.addWidget(open_package)

        new_workspace = self._action_button("New Empty Workspace", "folder-plus")
        new_workspace.clicked.connect(lambda: self.new_workspace_requested.emit())
        actions_layout.addWidget(new_workspace)

        continue_button = self._action_button("Continue to IDE", "explorer")
        continue_button.clicked.connect(lambda: self.continue_requested.emit())
        actions_layout.addWidget(continue_button)
        actions_layout.addStretch(1)
        columns.addWidget(actions, 4)

        workspace_panel = QFrame()
        workspace_panel.setObjectName("welcomeWorkspacePanel")
        workspace_layout = QVBoxLayout(workspace_panel)
        workspace_layout.setContentsMargins(18, 16, 18, 16)
        workspace_layout.setSpacing(8)
        workspace_layout.addWidget(_section("Current Workspace"))
        self.workspace_name = QLabel("Workspace")
        self.workspace_name.setObjectName("welcomeWorkspaceName")
        workspace_layout.addWidget(self.workspace_name)
        self.workspace_meta = QLabel("No folders added")
        self.workspace_meta.setObjectName("welcomeMeta")
        workspace_layout.addWidget(self.workspace_meta)
        self.workspace_root = QLabel("Open a workspace folder to discover ROS2 packages.")
        self.workspace_root.setObjectName("welcomeRoot")
        self.workspace_root.setWordWrap(True)
        workspace_layout.addWidget(self.workspace_root)

        self.package_list = QListWidget()
        self.package_list.setObjectName("welcomePackageList")
        self.package_list.setUniformItemSizes(True)
        self.package_list.itemActivated.connect(self._activate_package)
        workspace_layout.addWidget(self.package_list, 1)
        columns.addWidget(workspace_panel, 6)

        stage_layout.addLayout(columns, 1)
        outer.addWidget(stage, 0, Qt.AlignmentFlag.AlignHCenter)
        outer.addStretch(1)

    @staticmethod
    def _action_button(text: str, icon_name: str, *, primary: bool = False) -> QPushButton:
        button = _button(text, primary=primary)
        button.setObjectName("welcomeAction")
        button.setIcon(_icon(icon_name))
        button.setIconSize(QSize(18, 18))
        button.setMinimumHeight(44)
        return button

    def set_workspace(self, state: dict, packages: list[RosPackage]) -> None:
        roots = [str(root) for root in state.get("roots") or []]
        self.workspace_name.setText(str(state.get("name") or "Workspace"))
        package_count = len(packages)
        root_count = len(roots)
        package_word = "package" if package_count == 1 else "packages"
        root_word = "folder" if root_count == 1 else "folders"
        self.workspace_meta.setText(
            f"{package_count} {package_word} in {root_count} {root_word}"
        )
        if roots:
            extra = f"\n+ {root_count - 1} more" if root_count > 1 else ""
            root_path = Path(roots[0])
            root_parts = root_path.parts
            compact_root = str(root_path)
            if len(root_parts) > 4:
                compact_root = str(Path(root_parts[0], "...", *root_parts[-3:]))
            self.workspace_root.setText(f"{compact_root}{extra}")
            self.workspace_root.setToolTip(roots[0])
        else:
            self.workspace_root.setText("Open a workspace folder to discover ROS2 packages.")
            self.workspace_root.setToolTip("")

        self.package_list.clear()
        if not packages:
            empty = QListWidgetItem("No ROS2 packages detected")
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            empty.setForeground(QBrush(QColor("#708198")))
            self.package_list.addItem(empty)
            return
        for package in packages:
            item = QListWidgetItem(package.name)
            item.setIcon(_icon("cube"))
            item.setData(Qt.ItemDataRole.UserRole, str(package.path.resolve()))
            item.setToolTip(str(package.path))
            self.package_list.addItem(item)

    def _activate_package(self, item: QListWidgetItem) -> None:
        package_path = item.data(Qt.ItemDataRole.UserRole)
        if package_path:
            self.package_requested.emit(str(package_path))


class MainWindow(QMainWindow):
    docker_operation_finished = Signal(str, object, object)

    def __init__(
        self,
        *,
        show_welcome: bool | None = None,
        settings: QSettings | None = None,
    ) -> None:
        super().__init__()
        ensure_dirs()
        self._settings = settings if settings is not None else QSettings("MergeOS", "Lappa")
        self._show_welcome_override = show_welcome
        self.packages = workspace.workspace_packages()
        self._package_by_path: dict[str, RosPackage] = {}
        self._package_labels: dict[str, str] = {}
        self._editor_pkg: RosPackage | None = None
        self._editor_rel: str | None = None
        self._editor_dirty = False
        self._all_files: list[str] = []
        self._all_dirs: list[str] = []
        self._ai_turns: list[tuple[str, str]] = []
        self._sim_running = False
        self._resize_active = False
        self._docker_busy = False
        self._docker_last_result: dict | None = None
        self.docker_operation_finished.connect(self._finish_docker_operation)
        self.setAcceptDrops(True)

        self.setWindowTitle(f"Lappa - ROS2 Package IDE - v{__version__}")
        self.resize(1460, 860)
        self.setMinimumSize(1180, 720)
        self.setStyleSheet(STYLESHEET)

        central = QWidget()
        central.setObjectName("central")
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.setCentralWidget(central)

        self.page_stack = QStackedWidget()
        self.page_stack.setObjectName("pageStack")
        self.welcome_page = WelcomePage()
        self.welcome_page.open_workspace_requested.connect(self._welcome_open_workspace)
        self.welcome_page.open_package_requested.connect(self._welcome_open_package)
        self.welcome_page.new_workspace_requested.connect(self._welcome_new_workspace)
        self.welcome_page.continue_requested.connect(self._enter_workbench)
        self.welcome_page.package_requested.connect(self._welcome_select_package)
        self.page_stack.addWidget(self.welcome_page)

        self.workbench_page = QWidget()
        self.workbench_page.setObjectName("workbenchPage")
        workbench_layout = QVBoxLayout(self.workbench_page)
        workbench_layout.setContentsMargins(0, 0, 0, 0)
        workbench_layout.setSpacing(0)
        workbench_layout.addWidget(self._build_topbar())
        workbench_layout.addWidget(self._build_workspace(), 1)
        self.page_stack.addWidget(self.workbench_page)
        root.addWidget(self.page_stack, 1)

        self.setStatusBar(QStatusBar())
        self.cursor_label = QLabel("Ln 1, Col 1 | Saved")
        self.cursor_label.setObjectName("statusInfo")
        self.statusBar().addPermanentWidget(self.cursor_label)
        self._install_shortcuts()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick_sim)
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._finish_resize)

        self._reload_workspace_packages(open_active=False)
        self.pkg_combo.currentIndexChanged.connect(self._editor_load_current_package)
        self.file_filter.textChanged.connect(self._refresh_file_list)
        if self.pkg_combo.count():
            self._editor_load_current_package()

        self._refresh_welcome_workspace()
        if self._should_show_welcome():
            self._show_welcome()
        else:
            self._enter_workbench(mark_seen=False)

        self._status("Ready. Workspace packages are editable and simulatable side by side.")

    def _should_show_welcome(self) -> bool:
        if self._show_welcome_override is not None:
            return self._show_welcome_override
        seen = self._settings.value(WELCOME_SETTINGS_KEY, False)
        return not (seen is True or str(seen).strip().lower() in {"1", "true", "yes"})

    def _show_welcome(self) -> None:
        self._refresh_welcome_workspace()
        self.page_stack.setCurrentWidget(self.welcome_page)
        self.statusBar().hide()
        self.setWindowTitle(f"Welcome - Lappa ROS2 Package IDE - v{__version__}")

    def _enter_workbench(self, *, mark_seen: bool = True) -> None:
        if mark_seen:
            self._settings.setValue(WELCOME_SETTINGS_KEY, True)
            self._settings.sync()
        self.page_stack.setCurrentWidget(self.workbench_page)
        self.statusBar().show()
        self._sync_editor_chrome()

    def _refresh_welcome_workspace(self) -> None:
        if hasattr(self, "welcome_page"):
            self.welcome_page.set_workspace(workspace.load_workspace_state(), self.packages)

    def _welcome_open_workspace(self) -> None:
        if self._add_workspace_folder():
            self._enter_workbench()

    def _welcome_open_package(self) -> None:
        if self._add_workspace_package():
            self._enter_workbench()

    def _welcome_new_workspace(self) -> None:
        if self._new_workspace():
            self._enter_workbench()

    def _welcome_select_package(self, package_path: str) -> None:
        self._editor_load_package(package_path)
        if self._editor_pkg and self._package_key(self._editor_pkg) == str(Path(package_path).resolve()):
            self._enter_workbench()

    def _build_topbar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("topbar")
        bar.setFixedHeight(46)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        brand = QLabel("Lappa")
        brand.setObjectName("brand")
        subtitle = QLabel("ROS2 Package IDE")
        subtitle.setObjectName("brandSub")
        brand_box = QVBoxLayout()
        brand_box.setSpacing(0)
        brand_box.addWidget(brand)
        brand_box.addWidget(subtitle)
        layout.addLayout(brand_box)

        layout.addSpacing(12)
        layout.addWidget(QLabel("Package"))
        self.pkg_combo = QComboBox()
        self.pkg_combo.setMinimumWidth(180)
        for pkg in self.packages:
            self.pkg_combo.addItem(self._package_label(pkg), self._package_key(pkg))
        layout.addWidget(self.pkg_combo)

        self.header_file_label = QLabel("No file open")
        self.header_file_label.setObjectName("pathLabel")
        layout.addWidget(self.header_file_label, 1)

        b_save = _button("Save", primary=True, compact=True)
        b_save.setIcon(_icon("save"))
        b_save.clicked.connect(self._editor_save)
        b_reload = _button("Reload", compact=True)
        b_reload.setIcon(_icon("refresh"))
        b_reload.clicked.connect(self._editor_reload)
        b_run = _button("Run", primary=True, compact=True)
        b_run.setIcon(_icon("play"))
        b_run.clicked.connect(self.sim_run)
        b_stop = _button("Stop", compact=True)
        b_stop.setIcon(_icon("stop"))
        b_stop.clicked.connect(self.sim_stop)
        b_docker = _button("Docker", compact=True)
        b_docker.setIcon(_icon("docker"))
        b_docker.clicked.connect(self._editor_docker_launch)
        for button in (b_save, b_reload, b_run, b_stop, b_docker):
            layout.addWidget(button)

        return bar

    def _build_workspace(self) -> QSplitter:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("workspace")
        splitter.setChildrenCollapsible(False)
        splitter.setOpaqueResize(False)
        splitter.setHandleWidth(6)
        splitter.addWidget(self._build_project_panel())
        splitter.addWidget(self._build_editor_panel())
        splitter.addWidget(self._build_sim_panel())
        splitter.setSizes([330, 780, 440])
        return splitter

    def _build_project_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("projectPanel")
        outer = QHBoxLayout(panel)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        rail = QFrame()
        rail.setObjectName("activityRail")
        rail.setFixedWidth(50)
        rail_layout = QVBoxLayout(rail)
        rail_layout.setContentsMargins(4, 8, 4, 8)
        rail_layout.setSpacing(6)
        b_files = _tool_button("explorer", "Explorer")
        b_files.clicked.connect(lambda: self.ed_file_tree.setFocus())
        b_run = _tool_button("play", "Run simulation")
        b_run.clicked.connect(self.sim_run)
        b_ai = _tool_button("ai", "AI chat")
        b_ai.clicked.connect(self._focus_ai_panel)
        for button in (b_files, b_run, b_ai):
            rail_layout.addWidget(button)
        rail_layout.addStretch(1)
        b_welcome = _tool_button("cube", "Welcome")
        b_welcome.clicked.connect(self._show_welcome)
        rail_layout.addWidget(b_welcome)
        outer.addWidget(rail)

        explorer = QFrame()
        explorer.setObjectName("explorerPanel")
        layout = QVBoxLayout(explorer)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        title_row = QHBoxLayout()
        title_row.setSpacing(4)
        title = QLabel("Explorer")
        title.setObjectName("panelTitleSmall")
        title_row.addWidget(title)
        title_row.addStretch(1)
        b_open = _toolbar_button("folder", "Open workspace folder")
        b_open.clicked.connect(self._add_workspace_folder)
        b_pkg = _toolbar_button("cube", "Add ROS package")
        b_pkg.clicked.connect(self._add_workspace_package)
        b_new_file = _toolbar_button("file-plus", "New file")
        b_new_file.clicked.connect(self._create_new_file)
        b_new_dir = _toolbar_button("folder-plus", "New folder")
        b_new_dir.clicked.connect(self._create_new_folder)
        b_refresh = _toolbar_button("refresh", "Refresh workspace")
        b_refresh.clicked.connect(lambda: self._reload_workspace_packages())
        title_row.addWidget(b_open)
        title_row.addWidget(b_pkg)
        title_row.addWidget(b_new_file)
        title_row.addWidget(b_new_dir)
        title_row.addWidget(b_refresh)
        layout.addLayout(title_row)

        self.pkg_meta = QLabel("-")
        self.pkg_meta.setObjectName("muted")
        self.pkg_meta.setWordWrap(True)
        layout.addWidget(self.pkg_meta)

        self.file_filter = QLineEdit()
        self.file_filter.setPlaceholderText("Search files")
        layout.addWidget(self.file_filter)

        self.ed_file_tree = QTreeWidget()
        self.ed_file_tree.setObjectName("fileTree")
        self.ed_file_tree.setHeaderHidden(True)
        self.ed_file_tree.setAnimated(False)
        self.ed_file_tree.setUniformRowHeights(True)
        self.ed_file_tree.itemClicked.connect(self._editor_open_file)
        self.ed_file_tree.itemActivated.connect(self._editor_open_file)
        layout.addWidget(self.ed_file_tree, 1)

        layout.addWidget(_section("Workspace Roots"))
        self.workspace_roots_list = QListWidget()
        self.workspace_roots_list.setObjectName("rootList")
        self.workspace_roots_list.setMaximumHeight(58)
        layout.addWidget(self.workspace_roots_list)

        package_row = QHBoxLayout()
        package_row.addWidget(_section("Packages"))
        package_row.addStretch(1)
        b_new_workspace = _toolbar_button("reset", "New empty workspace")
        b_new_workspace.clicked.connect(self._new_workspace)
        package_row.addWidget(b_new_workspace)
        layout.addLayout(package_row)

        self.demo_list = QListWidget()
        self.demo_list.setMaximumHeight(96)
        for pkg in self.packages:
            item = QListWidgetItem(self._package_label(pkg))
            item.setData(Qt.ItemDataRole.UserRole, self._package_key(pkg))
            self.demo_list.addItem(item)
        self.demo_list.itemDoubleClicked.connect(lambda _: self._open_selected_package())
        layout.addWidget(self.demo_list)
        outer.addWidget(explorer, 1)
        return panel

    def _build_editor_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("editorPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header_frame = QFrame()
        header_frame.setObjectName("editorHeader")
        header = QHBoxLayout(header_frame)
        header.setContentsMargins(12, 10, 12, 8)
        header.setSpacing(10)
        title = QLabel("Source Editor")
        title.setObjectName("panelTitle")
        self.ed_path_label = QLabel("No file open")
        self.ed_path_label.setObjectName("pathLabel")
        header.addWidget(title)
        header.addWidget(self.ed_path_label, 1)
        layout.addWidget(header_frame)

        center_splitter = QSplitter(Qt.Orientation.Vertical)
        center_splitter.setObjectName("centerSplitter")
        center_splitter.setChildrenCollapsible(False)
        center_splitter.setOpaqueResize(False)
        center_splitter.setHandleWidth(7)

        editor_body = QFrame()
        editor_body.setObjectName("editorBody")
        editor_layout = QVBoxLayout(editor_body)
        editor_layout.setContentsMargins(12, 0, 10, 10)
        editor_layout.setSpacing(0)

        self.ed_text = QPlainTextEdit()
        self.ed_text.setObjectName("codeEditor")
        mono = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        mono.setPointSize(11)
        self.ed_text.setFont(mono)
        self.ed_text.textChanged.connect(self._mark_editor_dirty)
        self.ed_text.cursorPositionChanged.connect(self._update_cursor_status)

        self.editor_view_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.editor_view_splitter.setObjectName("editorViewSplitter")
        self.editor_view_splitter.setChildrenCollapsible(False)
        self.editor_view_splitter.setOpaqueResize(False)
        self.editor_view_splitter.setHandleWidth(6)
        self.editor_view_splitter.addWidget(self.ed_text)
        self.model_preview = ModelPreview()
        self.model_preview.setObjectName("modelPreview")
        self.editor_view_splitter.addWidget(self.model_preview)
        self.editor_view_splitter.setSizes([900, 0])
        self.model_preview.hide()
        editor_layout.addWidget(self.editor_view_splitter, 1)
        center_splitter.addWidget(editor_body)

        self.ops_tabs = QTabWidget()
        self.ops_tabs.setObjectName("opsTabs")
        self.ops_tabs.addTab(self._tab_ai(), "AI Chat")
        self.ops_tabs.addTab(self._tab_console(), "Console")
        self.ops_tabs.addTab(self._tab_workspace(), "Workspace")
        self.ops_tabs.addTab(self._tab_models(), "3D Models")
        self.ops_tabs.addTab(self._tab_packages(), "Packages")
        self.ops_tabs.addTab(self._tab_ros2(), "ROS2 / Docker")
        center_splitter.addWidget(self.ops_tabs)
        center_splitter.setSizes([640, 180])
        center_splitter.setStretchFactor(0, 4)
        center_splitter.setStretchFactor(1, 1)
        layout.addWidget(center_splitter, 1)
        return panel

    def _build_sim_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("simPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 14, 14, 14)
        layout.setSpacing(10)

        top = QHBoxLayout()
        title = QLabel("Live Simulation")
        title.setObjectName("panelTitle")
        self.sim_state_pill = QLabel("Idle")
        self.sim_state_pill.setObjectName("statePill")
        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(self.sim_state_pill)
        layout.addLayout(top)

        self.canvas = SimCanvas()
        view_bar = QHBoxLayout()
        view_bar.setSpacing(8)
        view_bar.addWidget(QLabel("View"))
        self.sim_view_combo = QComboBox()
        self.sim_view_combo.addItems(["Orbit", "Top", "Follow"])
        self.sim_view_combo.currentTextChanged.connect(self.canvas.set_view_mode)
        view_bar.addWidget(self.sim_view_combo)
        for text, callback in (
            ("Grid", self.canvas.set_grid_visible),
            ("Laser", self.canvas.set_laser_visible),
            ("Trail", self.canvas.set_trail_visible),
        ):
            toggle = QCheckBox(text)
            toggle.setChecked(True)
            toggle.toggled.connect(callback)
            view_bar.addWidget(toggle)
        view_bar.addStretch(1)
        reset_view = _toolbar_button("reset", "Reset camera", width=28)
        reset_view.clicked.connect(self.canvas.reset_view)
        view_bar.addWidget(reset_view)
        layout.addLayout(view_bar)
        layout.addWidget(self.canvas, 1)

        metrics = QGridLayout()
        pose_card, self.pose_label = _metric("Pose")
        twist_card, self.lbl_twist = _metric("Twist")
        scan_card, self.scan_label = _metric("Scan")
        reload_card, self.reload_label = _metric("Reloads")
        metrics.addWidget(pose_card, 0, 0)
        metrics.addWidget(twist_card, 0, 1)
        metrics.addWidget(scan_card, 1, 0)
        metrics.addWidget(reload_card, 1, 1)
        layout.addLayout(metrics)

        controls = QFrame()
        controls.setObjectName("controlPanel")
        control_layout = QVBoxLayout(controls)
        control_layout.setContentsMargins(12, 10, 12, 10)
        control_layout.setSpacing(8)

        self.demo_combo = QComboBox()
        for pkg in self.packages:
            self.demo_combo.addItem(self._package_label(pkg), self._package_key(pkg))
        control_layout.addWidget(QLabel("Simulation package"))
        control_layout.addWidget(self.demo_combo)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self.sl_lx = QSlider(Qt.Orientation.Horizontal)
        self.sl_lx.setRange(-100, 100)
        self.sl_ly = QSlider(Qt.Orientation.Horizontal)
        self.sl_ly.setRange(-100, 100)
        self.sl_az = QSlider(Qt.Orientation.Horizontal)
        self.sl_az.setRange(-150, 150)
        form.addRow("linear.x", self.sl_lx)
        form.addRow("linear.y", self.sl_ly)
        form.addRow("angular.z", self.sl_az)
        control_layout.addLayout(form)

        button_row = QHBoxLayout()
        b_run = _button("Run", primary=True)
        b_run.clicked.connect(self.sim_run)
        b_stop = _button("Stop")
        b_stop.clicked.connect(self.sim_stop)
        b_zero = _button("Zero")
        b_zero.clicked.connect(self.sim_zero)
        button_row.addWidget(b_run)
        button_row.addWidget(b_stop)
        button_row.addWidget(b_zero)
        control_layout.addLayout(button_row)
        layout.addWidget(controls)

        self.sim_log = QTextEdit()
        self.sim_log.setObjectName("logBox")
        self.sim_log.setReadOnly(True)
        self.sim_log.setMaximumHeight(110)
        layout.addWidget(self.sim_log)
        return panel

    def _tab_ai(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.ai_log = QTextEdit()
        self.ai_log.setObjectName("aiChat")
        self.ai_log.setReadOnly(True)
        self.ai_log.setPlaceholderText("AI assistant conversation")
        self.ai_log.setPlainText(
            "Lappa AI Assistant ready.\n"
            "Ask for a package review, ROS launch check, code explanation, or simulation guidance."
        )
        layout.addWidget(self.ai_log, 1)

        input_row = QHBoxLayout()
        self.ai_input = QLineEdit()
        self.ai_input.setPlaceholderText("Ask AI about this package or file")
        self.ai_input.returnPressed.connect(self._ai_send)
        b_send = _button("Send", primary=True, compact=True)
        b_send.clicked.connect(self._ai_send)
        input_row.addWidget(self.ai_input, 1)
        input_row.addWidget(b_send)
        layout.addLayout(input_row)
        return tab

    def _tab_workspace(self) -> QWidget:
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        actions = QVBoxLayout()
        b_add_folder = _button("Add Folder")
        b_add_folder.clicked.connect(self._add_workspace_folder)
        b_add_pkg = _button("Add Package")
        b_add_pkg.clicked.connect(self._add_workspace_package)
        b_new = _button("New Workspace")
        b_new.clicked.connect(self._new_workspace)
        b_refresh = _button("Refresh Scan", primary=True)
        b_refresh.clicked.connect(lambda: self._reload_workspace_packages())
        for button in (b_add_folder, b_add_pkg, b_new, b_refresh):
            actions.addWidget(button)
        actions.addStretch(1)
        layout.addLayout(actions)
        self.workspace_log = QTextEdit()
        self.workspace_log.setObjectName("logBox")
        self.workspace_log.setReadOnly(True)
        layout.addWidget(self.workspace_log, 1)
        return tab

    def _tab_models(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        form = QFormLayout()
        self.mesh_preset = QComboBox()
        for preset in models3d.list_presets():
            self.mesh_preset.addItem(preset["id"])
        self.mesh_name = QComboBox()
        self.mesh_name.setEditable(True)
        self.mesh_name.setCurrentText("my_chassis")
        form.addRow("Preset", self.mesh_preset)
        form.addRow("Name", self.mesh_name)
        layout.addLayout(form)
        row = QHBoxLayout()
        b_create = _button("Create mesh", primary=True)
        b_create.clicked.connect(self._create_mesh)
        b_build = _button("Build full robot")
        b_build.clicked.connect(self._build_robot)
        b_refresh = _button("Refresh library")
        b_refresh.clicked.connect(self._refresh_meshes)
        row.addWidget(b_create)
        row.addWidget(b_build)
        row.addWidget(b_refresh)
        row.addStretch(1)
        layout.addLayout(row)
        self.mesh_list = QListWidget()
        self.mesh_list.setMaximumHeight(70)
        layout.addWidget(self.mesh_list)
        self._refresh_meshes()
        return tab

    def _tab_packages(self) -> QWidget:
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        self.pkg_list = QListWidget()
        for pkg in packager.list_bundleable():
            name = pkg["name"] if isinstance(pkg, dict) else str(pkg)
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.pkg_list.addItem(item)
        layout.addWidget(self.pkg_list, 1)
        side = QVBoxLayout()
        b_bundle = _button("Create bundle", primary=True)
        b_bundle.clicked.connect(self._bundle)
        side.addWidget(b_bundle)
        self.pkg_log = QTextEdit()
        self.pkg_log.setObjectName("logBox")
        self.pkg_log.setReadOnly(True)
        side.addWidget(self.pkg_log, 1)
        layout.addLayout(side, 2)
        return tab

    def _tab_ros2(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        row = QHBoxLayout()
        self.ros2_combo = QComboBox()
        for version in ros2_versions.list_versions():
            self.ros2_combo.addItem(f"{version['id']} - {version.get('name', '')}", version["id"])
        selected = ros2_versions.get_selected().get("id")
        for i in range(self.ros2_combo.count()):
            if self.ros2_combo.itemData(i) == selected:
                self.ros2_combo.setCurrentIndex(i)
        b_apply = _button("Apply")
        b_apply.setToolTip("Apply selected ROS2 distro")
        b_apply.clicked.connect(self._set_ros2)
        self.docker_start_button = _button("Start", primary=True)
        self.docker_start_button.setToolTip("Build and start the Lappa ROS2 runtime")
        self.docker_start_button.clicked.connect(self._docker_start)
        self.docker_launch_button = _button("Launch")
        self.docker_launch_button.setToolTip("Build and launch the active package in ROS2")
        self.docker_launch_button.clicked.connect(self._docker_launch_active)
        self.docker_stop_button = _button("Stop Run")
        self.docker_stop_button.setToolTip("Stop the current ros2 launch process")
        self.docker_stop_button.clicked.connect(self._docker_stop_launch)
        self.docker_down_button = _button("Down")
        self.docker_down_button.setToolTip("Stop the Lappa Docker container")
        self.docker_down_button.clicked.connect(self._docker_stop)
        b_refresh = _button("Refresh")
        b_refresh.setIcon(_icon("refresh"))
        b_refresh.clicked.connect(self._refresh_docker)
        row.addWidget(QLabel("Target"))
        row.addWidget(self.ros2_combo, 1)
        for button in (
            b_apply,
            self.docker_start_button,
            self.docker_launch_button,
            self.docker_stop_button,
            self.docker_down_button,
            b_refresh,
        ):
            row.addWidget(button)
        layout.addLayout(row)

        diagnostic_panel = QFrame()
        diagnostic_panel.setObjectName("dockerDiagnosticPanel")
        diagnostic_layout = QGridLayout(diagnostic_panel)
        diagnostic_layout.setContentsMargins(10, 8, 10, 8)
        diagnostic_layout.setHorizontalSpacing(18)
        diagnostic_layout.setVerticalSpacing(5)
        self.docker_status_labels: dict[str, QLabel] = {}
        diagnostic_names = [
            ("cli", "Docker CLI"),
            ("engine", "Engine"),
            ("compose", "Compose"),
            ("image", "ROS2 Image"),
            ("container", "Container"),
            ("launch", "ROS2 Launch"),
        ]
        for index, (key, title) in enumerate(diagnostic_names):
            name = QLabel(title)
            name.setObjectName("dockerStatusName")
            value = QLabel("Checking")
            value.setObjectName("dockerStatusValue")
            value.setProperty("statusLevel", "muted")
            diagnostic_layout.addWidget(name, index // 3, (index % 3) * 2)
            diagnostic_layout.addWidget(value, index // 3, (index % 3) * 2 + 1)
            self.docker_status_labels[key] = value
        layout.addWidget(diagnostic_panel)

        guidance_row = QHBoxLayout()
        self.docker_guidance = QLabel("Checking Docker runtime...")
        self.docker_guidance.setObjectName("dockerGuidance")
        self.docker_guidance.setWordWrap(True)
        guidance_row.addWidget(self.docker_guidance, 1)
        self.docker_desktop_button = _button("Open Docker Desktop", compact=True)
        self.docker_desktop_button.clicked.connect(self._open_docker_desktop)
        self.docker_install_button = _button("Install Docker", compact=True)
        self.docker_install_button.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(docker_bridge.DOCKER_INSTALL_URL))
        )
        guidance_row.addWidget(self.docker_desktop_button)
        guidance_row.addWidget(self.docker_install_button)
        layout.addLayout(guidance_row)

        self.docker_info = QTextEdit()
        self.docker_info.setObjectName("logBox")
        self.docker_info.setReadOnly(True)
        layout.addWidget(self.docker_info, 1)
        self._refresh_docker()
        return tab

    def _tab_console(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        self.event_log = QTextEdit()
        self.event_log.setObjectName("logBox")
        self.event_log.setReadOnly(True)
        layout.addWidget(self.event_log)
        return tab

    def _status(self, msg: str) -> None:
        self.statusBar().showMessage(msg)
        self._log(msg)

    def _install_shortcuts(self) -> None:
        shortcuts = [
            ("Ctrl+S", self._editor_save, "Save active file"),
            ("Ctrl+R", self._editor_reload, "Reload active file"),
            ("Ctrl+O", self._welcome_open_workspace, "Open workspace folder"),
            ("Ctrl+N", self._create_new_file, "New file"),
            ("Ctrl+Shift+N", self._create_new_folder, "New folder"),
            ("F5", self.sim_run, "Run native simulation"),
            ("Shift+F5", self.sim_stop, "Stop native simulation"),
            ("Ctrl+Shift+A", self._focus_ai_panel, "Focus AI chat"),
            ("Ctrl+Shift+H", self._show_welcome, "Show welcome"),
        ]
        for sequence, slot, label in shortcuts:
            action = QAction(label, self)
            action.setShortcut(QKeySequence(sequence))
            action.triggered.connect(lambda _checked=False, slot=slot: slot())
            self.addAction(action)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, "_resize_timer"):
            self._resize_active = True
            self._resize_timer.start(140)

    def _finish_resize(self) -> None:
        self._resize_active = False
        if hasattr(self, "canvas"):
            self.canvas.update()

    def _log(self, msg: str) -> None:
        if hasattr(self, "event_log"):
            self.event_log.append(msg)
        if hasattr(self, "workspace_log"):
            self.workspace_log.append(msg)

    def _focus_ai_panel(self) -> None:
        if hasattr(self, "ops_tabs"):
            self.ops_tabs.setCurrentIndex(0)
        if hasattr(self, "ai_input"):
            self.ai_input.setFocus()

    def _editor_display_text(self) -> str:
        if not self._editor_pkg or not self._editor_rel:
            return "No file open"
        display = f"{self._editor_pkg.name}/{self._editor_rel}"
        return f"* {display}" if self._editor_dirty else display

    def _sync_editor_chrome(self) -> None:
        display = self._editor_display_text()
        if hasattr(self, "ed_path_label"):
            self.ed_path_label.setText(display)
        if hasattr(self, "header_file_label"):
            self.header_file_label.setText(display)
        marker = "* " if self._editor_dirty else ""
        self.setWindowTitle(f"{marker}Lappa - ROS2 Package IDE - v{__version__}")
        self._update_cursor_status()

    def _set_editor_dirty(self, dirty: bool) -> None:
        self._editor_dirty = dirty
        self._sync_editor_chrome()

    def _mark_editor_dirty(self) -> None:
        if self._editor_rel and not self._editor_dirty:
            self._set_editor_dirty(True)

    def _update_cursor_status(self) -> None:
        if not hasattr(self, "cursor_label") or not hasattr(self, "ed_text"):
            return
        cursor = self.ed_text.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.positionInBlock() + 1
        state = "Modified" if self._editor_dirty else "Saved"
        suffix = Path(self._editor_rel or "").suffix.lower().lstrip(".") or "text"
        self.cursor_label.setText(f"Ln {line}, Col {col} | {suffix} | {state}")

    def _confirm_editor_transition(self) -> bool:
        if not self._editor_dirty:
            return True
        target = self._editor_display_text().removeprefix("* ")
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("Unsaved changes")
        box.setText(f"Save changes to {target}?")
        save = box.addButton("Save", QMessageBox.ButtonRole.AcceptRole)
        discard = box.addButton("Discard", QMessageBox.ButtonRole.DestructiveRole)
        cancel = box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(save)
        box.exec()
        clicked = box.clickedButton()
        if clicked == save:
            self._editor_save()
            return not self._editor_dirty
        if clicked == discard:
            self._set_editor_dirty(False)
            return True
        return clicked != cancel and not self._editor_dirty

    def _ai_send(self) -> None:
        if not hasattr(self, "ai_input") or not hasattr(self, "ai_log"):
            return
        prompt = self.ai_input.text().strip()
        if not prompt:
            return
        self.ai_input.clear()
        pkg = self._active_package()
        file_label = self._editor_rel or "no file open"
        package_label = pkg.name if pkg else "no package"
        self.ai_log.append(f"\nYou: {prompt}")
        self.ai_log.append(
            "Lappa AI: Context captured for "
            f"package={package_label}, file={file_label}. "
            "Suggested review path: package.xml, launch files, node entry points, URDF/mesh refs, "
            "then run native simulation to verify pose, twist, lidar, and hot-reload behavior."
        )
        self._focus_ai_panel()

    def _package_key(self, pkg: RosPackage) -> str:
        return str(pkg.path.resolve())

    def _package_label(self, pkg: RosPackage) -> str:
        key = self._package_key(pkg)
        if key in self._package_labels:
            return self._package_labels[key]
        names = [p.name for p in self.packages]
        if names.count(pkg.name) > 1:
            return f"{pkg.name}  -  {pkg.path.parent.name}"
        return pkg.name

    def _rebuild_package_index(self) -> None:
        self._package_by_path = {self._package_key(pkg): pkg for pkg in self.packages}
        counts: dict[str, int] = {}
        for pkg in self.packages:
            counts[pkg.name] = counts.get(pkg.name, 0) + 1
        self._package_labels = {}
        for pkg in self.packages:
            label = pkg.name
            if counts[pkg.name] > 1:
                label = f"{pkg.name}  -  {pkg.path.parent.name}"
            self._package_labels[self._package_key(pkg)] = label

    def _fill_package_combo(self, combo: QComboBox, current_key: str | None = None) -> None:
        combo.blockSignals(True)
        combo.clear()
        for pkg in self.packages:
            combo.addItem(self._package_label(pkg), self._package_key(pkg))
        if current_key:
            idx = combo.findData(current_key)
            if idx >= 0:
                combo.setCurrentIndex(idx)
        combo.blockSignals(False)

    def _combo_package(self, combo: QComboBox) -> RosPackage | None:
        key = combo.currentData()
        if key:
            return self._package_by_path.get(str(key))
        return None

    def _active_package(self) -> RosPackage | None:
        if self._editor_pkg:
            return self._editor_pkg
        if hasattr(self, "pkg_combo"):
            return self._combo_package(self.pkg_combo)
        if hasattr(self, "demo_combo"):
            return self._combo_package(self.demo_combo)
        return self.packages[0] if self.packages else None

    def _active_package_name(self) -> str:
        pkg = self._active_package()
        return pkg.name if pkg else "diff_drive_2w"

    def _is_3d_file(self, rel: str) -> bool:
        return Path(rel).suffix.lower() in {".obj", ".stl", ".dae", ".urdf", ".xml"}

    def _refresh_workspace_roots(self) -> None:
        if not hasattr(self, "workspace_roots_list"):
            return
        self.workspace_roots_list.clear()
        for root in workspace.workspace_roots():
            self.workspace_roots_list.addItem(str(root))

    def _reload_workspace_packages(
        self,
        *,
        keep_key: str | None = None,
        open_active: bool = True,
    ) -> None:
        current = keep_key
        if not current and self._editor_pkg:
            current = self._package_key(self._editor_pkg)
        self.packages = workspace.workspace_packages()
        self._rebuild_package_index()
        if hasattr(self, "pkg_combo"):
            self._fill_package_combo(self.pkg_combo, current)
        if hasattr(self, "demo_combo"):
            self._fill_package_combo(self.demo_combo, current)
        if hasattr(self, "demo_list"):
            self.demo_list.clear()
            for pkg in self.packages:
                item = QListWidgetItem(self._package_label(pkg))
                item.setData(Qt.ItemDataRole.UserRole, self._package_key(pkg))
                self.demo_list.addItem(item)
        self._refresh_workspace_roots()
        if open_active and self.pkg_combo.count():
            if current and self.pkg_combo.findData(current) >= 0:
                self.pkg_combo.setCurrentIndex(self.pkg_combo.findData(current))
            self._editor_load_current_package()
        elif not self.packages:
            self._editor_pkg = None
            self._all_files = []
            self._all_dirs = []
            self._editor_rel = None
            if hasattr(self, "pkg_meta"):
                self.pkg_meta.setText("No package loaded")
            if hasattr(self, "ed_file_tree"):
                self.ed_file_tree.clear()
            if hasattr(self, "ed_text"):
                self.ed_text.blockSignals(True)
                self.ed_text.clear()
                self.ed_text.blockSignals(False)
            if hasattr(self, "model_preview"):
                self.model_preview.hide()
            self._set_editor_dirty(False)
        self._refresh_welcome_workspace()

    def _add_workspace_folder(self) -> bool:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Add workspace folder",
            str(Path.home()),
        )
        if not folder:
            return False
        try:
            workspace.add_workspace_root(folder)
            self._reload_workspace_packages()
            self._status(f"Workspace folder added: {folder}")
            return True
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Workspace", str(exc))
            return False

    def _add_workspace_package(self) -> bool:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Add ROS2 package",
            str(Path.home()),
        )
        if not folder:
            return False
        path = Path(folder).expanduser().resolve()
        if not workspace.is_ros_package_dir(path):
            QMessageBox.warning(self, "Workspace", "Selected folder has no package.xml.")
            return False
        try:
            workspace.add_workspace_root(path)
            key = str(path)
            self._reload_workspace_packages(keep_key=key)
            self._status(f"Package added: {path.name}")
            return True
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Workspace", str(exc))
            return False

    def _new_workspace(self) -> bool:
        if not self._confirm_editor_transition():
            return False
        workspace.create_workspace("Workspace", include_samples=False)
        self._reload_workspace_packages()
        self._status("New workspace created")
        return True

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile() and Path(url.toLocalFile()).is_dir():
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event) -> None:  # noqa: N802
        added = 0
        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue
            path = Path(url.toLocalFile()).expanduser().resolve()
            if not path.is_dir():
                continue
            try:
                workspace.add_workspace_root(path)
                added += 1
            except Exception as exc:  # noqa: BLE001
                self._status(f"Drop ignored: {exc}")
        if added:
            self._reload_workspace_packages()
            self._status(f"Workspace updated from dropped folder(s): {added}")
            if self.page_stack.currentWidget() is self.welcome_page:
                self._enter_workbench()

    def _clean_rel_path(self, raw: str) -> str:
        rel = raw.replace("\\", "/").strip().lstrip("/")
        while "//" in rel:
            rel = rel.replace("//", "/")
        if not rel or rel in {".", ".."} or rel.endswith("/"):
            raise ValueError("Enter a relative file or folder path.")
        root = self._editor_pkg.path.resolve() if self._editor_pkg else None
        if root:
            target = (root / rel).resolve()
            target.relative_to(root)
        return rel

    def _create_new_file(self) -> None:
        if not self._editor_pkg:
            QMessageBox.information(self, "New File", "Open a package first.")
            return
        rel, ok = QInputDialog.getText(
            self,
            "New File",
            "Relative path:",
            text="src/new_node.py",
        )
        if not ok:
            return
        try:
            clean = self._clean_rel_path(rel)
            target = (self._editor_pkg.path / clean).resolve()
            if target.exists():
                QMessageBox.warning(self, "New File", "File already exists.")
                return
            write_file(self._editor_pkg, clean, "")
            self._editor_load_package(self._editor_pkg.path)
            self._open_file(clean)
            self._status(f"Created file {clean}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "New File", str(exc))

    def _create_new_folder(self) -> None:
        if not self._editor_pkg:
            QMessageBox.information(self, "New Folder", "Open a package first.")
            return
        rel, ok = QInputDialog.getText(
            self,
            "New Folder",
            "Relative path:",
            text="src/new_folder",
        )
        if not ok:
            return
        try:
            clean = self._clean_rel_path(rel.rstrip("/"))
            root = self._editor_pkg.path.resolve()
            target = (root / clean).resolve()
            target.relative_to(root)
            target.mkdir(parents=True, exist_ok=True)
            self._all_dirs = self._scan_package_dirs()
            self._refresh_file_list()
            self._status(f"Created folder {clean}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "New Folder", str(exc))

    def _editor_load_current_package(self, *_args) -> None:
        pkg = self._combo_package(self.pkg_combo)
        if pkg:
            self._editor_load_package(pkg)

    def _editor_load_package(self, package: RosPackage | str | Path) -> None:
        if isinstance(package, RosPackage):
            pkg = package
        else:
            try:
                pkg = workspace.resolve_package_ref(package, base_dir=Path.cwd())
            except FileNotFoundError:
                return
        if not pkg.path.is_dir():
            return
        previous_key = self._package_key(self._editor_pkg) if self._editor_pkg else None
        if self._editor_dirty and not self._confirm_editor_transition():
            if previous_key and hasattr(self, "pkg_combo"):
                idx = self.pkg_combo.findData(previous_key)
                if idx >= 0:
                    self.pkg_combo.blockSignals(True)
                    self.pkg_combo.setCurrentIndex(idx)
                    self.pkg_combo.blockSignals(False)
            return
        self._editor_pkg = load_package(pkg.path)
        self._editor_rel = None
        self._set_editor_dirty(False)
        self._all_files = list(self._editor_pkg.files)
        self._all_dirs = self._scan_package_dirs()
        self.pkg_meta.setText(
            f"{self._editor_pkg.name}\n{len(self._all_files)} files\n{self._editor_pkg.path}"
        )
        workspace.set_active_package(self._editor_pkg.path)
        self.file_filter.blockSignals(True)
        self.file_filter.clear()
        self.file_filter.blockSignals(False)
        self._refresh_file_list()
        if hasattr(self, "demo_combo"):
            idx = self.demo_combo.findData(self._package_key(self._editor_pkg))
            if idx >= 0:
                self.demo_combo.setCurrentIndex(idx)
        if hasattr(self, "pkg_combo"):
            idx = self.pkg_combo.findData(self._package_key(self._editor_pkg))
            if idx >= 0 and self.pkg_combo.currentIndex() != idx:
                self.pkg_combo.blockSignals(True)
                self.pkg_combo.setCurrentIndex(idx)
                self.pkg_combo.blockSignals(False)
        prefer = (
            next((f for f in self._all_files if f.endswith("teleop.py")), None)
            or next((f for f in self._all_files if f == "package.xml"), None)
            or (self._all_files[0] if self._all_files else None)
        )
        if prefer:
            self._open_file(prefer)
        self._status(f"Opened package {self._editor_pkg.name}")

    def _scan_package_dirs(self) -> list[str]:
        if not self._editor_pkg:
            return []
        root = self._editor_pkg.path.resolve()
        skip = {"__pycache__", "build", "install", "log"}
        dirs: list[str] = []
        for path in sorted(root.rglob("*")):
            if not path.is_dir():
                continue
            rel = path.relative_to(root).as_posix()
            parts = rel.split("/")
            if any(part.startswith(".") or part in skip for part in parts):
                continue
            dirs.append(rel)
        return dirs

    def _refresh_file_list(self) -> None:
        query = self.file_filter.text().strip().lower() if hasattr(self, "file_filter") else ""
        current = self._editor_rel
        if not hasattr(self, "ed_file_tree"):
            return
        self.ed_file_tree.clear()
        nodes: dict[str, QTreeWidgetItem] = {}

        def ensure_node(path_key: str, *, file_rel: str | None = None) -> QTreeWidgetItem:
            parts = path_key.split("/")
            parent: QTreeWidgetItem | None = None
            built: list[str] = []
            item: QTreeWidgetItem | None = None
            for index, part in enumerate(parts):
                built.append(part)
                key = "/".join(built)
                item = nodes.get(key)
                if item is None:
                    item = QTreeWidgetItem([part])
                    item.setData(0, Qt.ItemDataRole.UserRole, None)
                    item.setIcon(0, _icon("folder"))
                    if parent:
                        parent.addChild(item)
                    else:
                        self.ed_file_tree.addTopLevelItem(item)
                    nodes[key] = item
                parent = item
                if index < len(parts) - 1:
                    item.setExpanded(True)
            if item is None:
                item = QTreeWidgetItem([path_key])
                self.ed_file_tree.addTopLevelItem(item)
            if file_rel:
                item.setData(0, Qt.ItemDataRole.UserRole, file_rel)
                item.setIcon(0, _icon("cube" if self._is_3d_file(file_rel) else "file"))
            return item

        for rel in self._all_dirs:
            if query and query not in rel.lower():
                continue
            ensure_node(rel)

        current_item: QTreeWidgetItem | None = None
        for rel in self._all_files:
            if query and query not in rel.lower():
                continue
            item = ensure_node(rel, file_rel=rel)
            if current and rel == current:
                current_item = item

        if current_item:
            self.ed_file_tree.setCurrentItem(current_item)
            self.ed_file_tree.scrollToItem(current_item)
        self.ed_file_tree.expandToDepth(0)

    def _editor_open_file(self, item: QTreeWidgetItem) -> None:
        if not item:
            return
        rel = item.data(0, Qt.ItemDataRole.UserRole)
        if rel:
            self._open_file(str(rel))

    def _open_file(self, rel: str) -> None:
        if not self._editor_pkg:
            return
        if rel != self._editor_rel and not self._confirm_editor_transition():
            return
        try:
            text = read_file(self._editor_pkg, rel)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Open failed", str(exc))
            return
        self._editor_rel = rel
        self.ed_text.blockSignals(True)
        self.ed_text.setPlainText(text)
        self.ed_text.blockSignals(False)
        self._set_editor_dirty(False)
        if self._is_3d_file(rel):
            self.model_preview.show()
            self.model_preview.load_text(rel, text)
            self.editor_view_splitter.setSizes([620, 360])
        else:
            self.model_preview.hide()
            self.editor_view_splitter.setSizes([900, 0])
        self._sync_editor_chrome()
        self._refresh_file_list()

    def _editor_reload(self) -> None:
        if self._editor_rel and self._confirm_editor_transition():
            self._open_file(self._editor_rel)

    def _editor_save(self) -> None:
        if not self._editor_pkg or not self._editor_rel:
            QMessageBox.information(self, "Save", "Open a file first.")
            return
        try:
            write_file(self._editor_pkg, self._editor_rel, self.ed_text.toPlainText())
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Save failed", str(exc))
            return
        if self._is_3d_file(self._editor_rel):
            self.model_preview.load_text(self._editor_rel, self.ed_text.toPlainText())
        SESSION.notify_file_change(self._editor_rel)
        self._set_editor_dirty(False)
        self._status(f"Saved {self._editor_pkg.name}/{self._editor_rel}")

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._confirm_editor_transition():
            super().closeEvent(event)
        else:
            event.ignore()

    def _editor_docker_launch(self) -> None:
        self._docker_launch_active()

    def sim_zero(self) -> None:
        self.sl_lx.setValue(0)
        self.sl_ly.setValue(0)
        self.sl_az.setValue(0)

    def sim_run(self) -> None:
        pkg = self._combo_package(self.demo_combo) or self._active_package()
        demo = pkg.name if pkg else self._active_package_name()
        path = pkg.path if pkg else None
        SESSION.start(demo, path if path and path.is_dir() else None)
        self.canvas.clear_trail()
        self._sim_running = True
        self._timer.start(50)
        self.sim_state_pill.setText("Running")
        self.sim_log.append(f"native sim start: {demo}")
        self._status(f"Running native simulation for {demo}")

    def sim_stop(self) -> None:
        SESSION.stop()
        self._sim_running = False
        self._timer.stop()
        self.sim_state_pill.setText("Idle")
        self.sim_log.append("native sim stop")
        self._status("Simulation stopped")

    def _tick_sim(self) -> None:
        if not self._sim_running:
            return
        if self._resize_active:
            return
        lx = self.sl_lx.value() / 100.0
        ly = self.sl_ly.value() / 100.0
        az = self.sl_az.value() / 100.0
        SESSION.cmd(lx, ly, az)
        state = SESSION.tick()
        self.canvas.set_state(state)
        self.pose_label.setText(
            f"x={state.get('x', 0):.2f} y={state.get('y', 0):.2f} th={state.get('theta', 0):.2f}"
        )
        self.lbl_twist.setText(f"lx={lx:.2f} ly={ly:.2f} az={az:.2f}")
        lidar = state.get("lidar") or []
        self.scan_label.setText(f"{len(lidar)} rays" if lidar else "-")
        status = SESSION.status()
        self.reload_label.setText(str(status.get("reload_count", 0)))

    def _selected_package_from_list(self) -> RosPackage | None:
        item = self.demo_list.currentItem()
        if item:
            key = item.data(Qt.ItemDataRole.UserRole)
            if key:
                return self._package_by_path.get(str(key))
        return self._combo_package(self.demo_combo) or self._active_package()

    def _open_selected_package(self) -> None:
        pkg = self._selected_package_from_list()
        if not pkg:
            return
        idx = self.pkg_combo.findData(self._package_key(pkg))
        if idx >= 0:
            self.pkg_combo.setCurrentIndex(idx)

    def _run_selected_package(self) -> None:
        pkg = self._selected_package_from_list()
        if not pkg:
            return
        idx = self.demo_combo.findData(self._package_key(pkg))
        if idx >= 0:
            self.demo_combo.setCurrentIndex(idx)
        self.sim_run()

    def _create_mesh(self) -> None:
        try:
            result = models3d.create_model(
                self.mesh_preset.currentText(),
                name=self.mesh_name.currentText() or None,
            )
            self._status(f"Created mesh {result['id']}")
            self._refresh_meshes()
        except Exception as exc:  # noqa: BLE001
            self._status(f"Mesh create failed: {exc}")

    def _build_robot(self) -> None:
        pkg = self._active_package()
        demo = pkg.name if pkg else self._active_package_name()
        try:
            target = str(pkg.path) if pkg else demo
            result = models3d.build_aligned_robot(target, kind=demo)
            self._status(
                f"Built 3D robot for {result['package']}: {result['links']} links"
            )
            if pkg:
                self._editor_load_package(pkg)
        except Exception as exc:  # noqa: BLE001
            self._status(f"Build robot failed: {exc}")

    def _refresh_meshes(self) -> None:
        if not hasattr(self, "mesh_list"):
            return
        self.mesh_list.clear()
        for mesh in models3d.list_library():
            self.mesh_list.addItem(f"{mesh['id']} ({mesh.get('bytes', 0)} B)")

    def _bundle(self) -> None:
        names: list[str] = []
        for i in range(self.pkg_list.count()):
            item = self.pkg_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                names.append(item.text())
        try:
            result = packager.package_bundle(names or None, distro=None)
            self.pkg_log.append(f"{result['filename']} ({result['size_bytes']} bytes)")
            self._status(f"Bundle created: {result['filename']}")
        except Exception as exc:  # noqa: BLE001
            self.pkg_log.append(str(exc))
            self._status(f"Bundle failed: {exc}")

    def _set_ros2(self) -> None:
        distro = str(self.ros2_combo.currentData())
        try:
            selected = ros2_versions.set_selected(distro)
            docker_bridge.apply_ros2_dockerfile(distro)
            self._status(f"ROS2 target set to {selected['id']}")
            self._refresh_docker()
        except Exception as exc:  # noqa: BLE001
            self._status(f"ROS2 set failed: {exc}")

    def _docker_start(self) -> None:
        self._run_docker_operation("Starting Docker runtime", docker_bridge.start_runtime)

    def _docker_stop(self) -> None:
        self._run_docker_operation("Stopping Docker runtime", docker_bridge.stop_runtime)

    def _docker_launch_active(self) -> None:
        pkg = self._active_package()
        demo = pkg.name if pkg else self._active_package_name()
        if pkg:
            try:
                pkg.path.resolve().relative_to(DEMOS_ROOT.resolve())
            except ValueError:
                msg = (
                    "Docker launch currently uses the mounted bundled package tree. "
                    "Run native sim for external workspace packages."
                )
                self._docker_last_result = {"ok": False, "error": msg}
                self._refresh_docker()
                self._status(msg)
                return
        self._run_docker_operation(
            f"Building and launching {demo}", lambda: docker_bridge.launch_demo(demo)
        )

    def _docker_stop_launch(self) -> None:
        self._run_docker_operation("Stopping ROS2 launch", docker_bridge.stop_launch)

    def _run_docker_operation(
        self, label: str, operation: Callable[[], dict[str, object]]
    ) -> None:
        if self._docker_busy:
            return
        self._docker_busy = True
        self.docker_guidance.setText(f"{label}. This may take a few minutes on first build.")
        self._update_docker_buttons({})

        def worker() -> None:
            try:
                result = operation()
                diagnostics = result.get("status") if isinstance(result, dict) else None
                if not isinstance(diagnostics, dict):
                    diagnostics = docker_bridge.status()
            except Exception as exc:  # noqa: BLE001
                result = {"ok": False, "error": str(exc)}
                diagnostics = docker_bridge.status()
            self.docker_operation_finished.emit(label, result, diagnostics)

        threading.Thread(target=worker, daemon=True).start()

    def _finish_docker_operation(self, label: str, result: object, diagnostics: object) -> None:
        self._docker_busy = False
        self._docker_last_result = result if isinstance(result, dict) else {"result": str(result)}
        status = diagnostics if isinstance(diagnostics, dict) else docker_bridge.status()
        self._apply_docker_status(status)
        if status.get("container_health") == "starting":
            QTimer.singleShot(5000, self._refresh_docker)
        ok = bool(self._docker_last_result.get("ok"))
        message = (
            self._docker_last_result.get("message")
            or self._docker_last_result.get("error")
            or (f"{label} complete" if ok else f"{label} failed")
        )
        self._status(str(message)[:160])

    @staticmethod
    def _docker_level(value: bool | None, *, warn_when_false: bool = False) -> str:
        if value is None:
            return "muted"
        if value:
            return "ok"
        return "warn" if warn_when_false else "error"

    def _set_docker_status(self, key: str, text: str, level: str) -> None:
        label = self.docker_status_labels[key]
        label.setText(text)
        label.setProperty("statusLevel", level)
        label.style().unpolish(label)
        label.style().polish(label)

    def _update_docker_buttons(self, status: dict) -> None:
        busy = self._docker_busy
        available = bool(status.get("available"))
        daemon = bool(status.get("daemon"))
        compose = bool(status.get("compose_available"))
        running = bool(status.get("running"))
        session = status.get("session") or {}
        self.docker_start_button.setEnabled(not busy and bool(status.get("ready_for_start")))
        self.docker_launch_button.setEnabled(
            not busy
            and available
            and daemon
            and compose
            and (not running or bool(status.get("ready_for_launch")))
        )
        self.docker_stop_button.setEnabled(
            not busy and session.get("mode") == "docker_launch"
        )
        self.docker_down_button.setEnabled(not busy and running)

    def _apply_docker_status(self, status: dict) -> None:
        available = bool(status.get("available"))
        daemon = bool(status.get("daemon"))
        compose = bool(status.get("compose_available"))
        image_present = status.get("image_present")
        container_exists = status.get("container_exists")
        running = bool(status.get("running"))
        container_health = status.get("container_health")
        session = status.get("session") or {}

        cli_text = "Installed" if available else "Missing"
        self._set_docker_status("cli", cli_text, self._docker_level(available))
        engine_text = "Running" if daemon else ("Stopped" if available else "Unavailable")
        self._set_docker_status("engine", engine_text, self._docker_level(daemon))
        compose_text = status.get("compose_version") or ("Missing" if available else "Unavailable")
        self._set_docker_status("compose", str(compose_text), self._docker_level(compose))
        image_text = (
            "Ready"
            if image_present is True
            else "Not built"
            if image_present is False
            else "Not checked"
        )
        self._set_docker_status(
            "image", image_text, self._docker_level(image_present, warn_when_false=True)
        )
        container_text = (
            f"Running ({container_health})"
            if running and container_health
            else "Running"
            if running
            else str(status.get("container_status") or "Stopped")
            if container_exists is not None
            else "Not checked"
        )
        container_level = (
            "error"
            if container_health == "unhealthy"
            else "warn"
            if container_health == "starting"
            else "ok"
            if running
            else "warn"
            if daemon
            else "muted"
        )
        self._set_docker_status("container", container_text.title(), container_level)
        launch_running = bool(session.get("running"))
        launch_text = session.get("demo") if launch_running else "Idle"
        self._set_docker_status("launch", str(launch_text), "ok" if launch_running else "muted")

        message = str(status.get("message") or "Docker status unavailable.")
        guidance = str(status.get("guidance") or "")
        self.docker_guidance.setText(f"{message} {guidance}".strip())
        state = status.get("state")
        self.docker_install_button.setVisible(state == "not_installed")
        self.docker_desktop_button.setVisible(
            state == "engine_stopped" and bool(status.get("docker_desktop_path"))
        )
        self._update_docker_buttons(status)

        details = [
            f"CLI: {status.get('cli_version') or 'not installed'}",
            f"Path: {status.get('cli_path') or '-'}",
            f"Context: {status.get('context') or '-'}",
            f"Engine: {status.get('server_version') or 'not running'}",
            f"ROS2 target: {status.get('ros2_distro')}",
            f"Image: {status.get('image')}",
            f"Container: {status.get('container_status')}",
            f"Health: {status.get('container_health') or '-'}",
            f"Compose: {status.get('compose_file')}",
        ]
        if status.get("detail"):
            details.extend(["", "Diagnostic:", str(status["detail"])])
        if session.get("last_log"):
            details.extend(["", "ROS2 session log:", str(session["last_log"])])
        if self._docker_last_result:
            details.extend(
                [
                    "",
                    "Last operation:",
                    json.dumps(self._docker_last_result, indent=2, default=str),
                ]
            )
        self.docker_info.setPlainText("\n".join(details))

    def _open_docker_desktop(self) -> None:
        result = docker_bridge.open_docker_desktop()
        self._docker_last_result = result
        self.docker_guidance.setText(
            str(result.get("message") or result.get("error") or "Docker Desktop request sent.")
        )
        self._status(self.docker_guidance.text())
        if result.get("ok"):
            QTimer.singleShot(5000, self._refresh_docker)

    def _refresh_docker(self) -> None:
        if not hasattr(self, "docker_info"):
            return
        try:
            self._apply_docker_status(docker_bridge.status())
        except Exception as exc:  # noqa: BLE001
            self.docker_guidance.setText(f"Docker status check failed: {exc}")
            self.docker_info.setPlainText(str(exc))

    def _goto(self, key: str) -> None:
        """Compatibility hook for screenshot automation."""
        if key == "welcome":
            self._show_welcome()
            return
        self._enter_workbench(mark_seen=False)
        mapping = {
            "ai": 0,
            "console": 1,
            "workspace": 2,
            "demos": 2,
            "models": 3,
            "packages": 4,
            "ros2": 5,
            "docker": 5,
        }
        if key in mapping:
            self.ops_tabs.setCurrentIndex(mapping[key])
        elif key == "sim":
            self.canvas.setFocus()
        else:
            self.ed_text.setFocus()
