"""Lappa Qt desktop IDE: package editor with live native simulation."""

from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import QPointF, QSize, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QFont, QFontDatabase, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox,
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
from lappa.sim.session import SESSION


def _button(text: str, *, primary: bool = False, compact: bool = False) -> QPushButton:
    b = QPushButton(text)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setProperty("primary", primary)
    b.setProperty("compact", compact)
    return b


def _tool_button(text: str, tooltip: str = "") -> QToolButton:
    b = QToolButton()
    b.setText(text)
    b.setToolTip(tooltip or text)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
    b.setFixedSize(QSize(42, 34))
    return b


def _toolbar_button(text: str, tooltip: str = "", width: int = 34) -> QToolButton:
    b = QToolButton()
    b.setText(text)
    b.setToolTip(tooltip or text)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
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
    """2D top-down simulator viewport."""

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumSize(360, 300)
        self.state: dict = {
            "x": 0.0,
            "y": 0.0,
            "theta": 0.0,
            "kind": "diff_drive_2w",
            "lidar": [],
            "running": False,
        }
        self.trail: list[tuple[float, float]] = []

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

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QColor("#08111f"))

        grid_pen = QPen(QColor("#1d2b3d"))
        grid_pen.setWidth(1)
        painter.setPen(grid_pen)
        for x in range(0, w, 36):
            painter.drawLine(x, 0, x, h)
        for y in range(0, h, 36):
            painter.drawLine(0, y, w, y)

        cx, cy = w / 2, h / 2
        scale = min(w, h) / 6.4

        axis_pen = QPen(QColor("#31435d"))
        axis_pen.setWidth(2)
        painter.setPen(axis_pen)
        painter.drawLine(QPointF(0, cy), QPointF(w, cy))
        painter.drawLine(QPointF(cx, 0), QPointF(cx, h))

        if len(self.trail) > 1:
            trail_pen = QPen(QColor(56, 139, 253, 150))
            trail_pen.setWidth(2)
            painter.setPen(trail_pen)
            for i in range(1, len(self.trail)):
                x0, y0 = self.trail[i - 1]
                x1, y1 = self.trail[i]
                painter.drawLine(
                    QPointF(cx + x0 * scale, cy - y0 * scale),
                    QPointF(cx + x1 * scale, cy - y1 * scale),
                )

        x = float(self.state.get("x") or 0.0)
        y = float(self.state.get("y") or 0.0)
        theta = float(self.state.get("theta") or 0.0)
        rx, ry = cx + x * scale, cy - y * scale

        lidar = self.state.get("lidar") or []
        if lidar:
            painter.setPen(QPen(QColor(63, 185, 80, 60), 1))
            for i, r in enumerate(lidar):
                angle = theta + (i / len(lidar)) * math.pi * 2
                lx = rx + math.cos(angle) * float(r) * scale * 0.35
                ly = ry - math.sin(angle) * float(r) * scale * 0.35
                painter.drawLine(QPointF(rx, ry), QPointF(lx, ly))

        painter.save()
        painter.translate(rx, ry)
        painter.rotate(-math.degrees(theta))
        kind = self.state.get("kind") or "diff_drive_2w"
        if kind == "simple_arm":
            self._draw_arm(painter)
        elif kind == "omni_3w":
            self._draw_omni(painter)
        elif kind == "ackermann_4w":
            self._draw_car(painter, QColor("#e3b341"))
        elif kind == "tricycle_3w":
            self._draw_tricycle(painter)
        else:
            self._draw_diff(painter)
        painter.restore()

        painter.setPen(QColor("#9fb3c8"))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(14, 22, f"{kind}  x={x:.2f}  y={y:.2f}  theta={theta:.2f}")

    def _draw_diff(self, painter: QPainter) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#44c767")))
        painter.drawRoundedRect(-20, -14, 40, 28, 5, 5)
        painter.setBrush(QBrush(QColor("#0b0f17")))
        painter.drawRoundedRect(-16, -20, 12, 7, 3, 3)
        painter.drawRoundedRect(-16, 13, 12, 7, 3, 3)
        painter.setPen(QPen(QColor("#f8fafc"), 2))
        painter.drawLine(0, 0, 28, 0)

    def _draw_omni(self, painter: QPainter) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#388bfd")))
        painter.drawEllipse(QPointF(0, 0), 22, 22)
        painter.setBrush(QBrush(QColor("#dbeafe")))
        for i in range(3):
            angle = i * math.tau / 3
            painter.drawEllipse(QPointF(math.cos(angle) * 20, math.sin(angle) * 20), 5, 5)
        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.drawLine(0, 0, 30, 0)

    def _draw_tricycle(self, painter: QPainter) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#a371f7")))
        points = [QPointF(24, 0), QPointF(-18, -16), QPointF(-18, 16)]
        painter.drawPolygon(points)
        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.drawLine(0, 0, 30, 0)

    def _draw_car(self, painter: QPainter, color: QColor) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawRoundedRect(-28, -15, 56, 30, 5, 5)
        painter.setBrush(QBrush(QColor("#0b0f17")))
        for wx, wy in [(-18, -20), (-18, 14), (18, -20), (18, 14)]:
            painter.drawRoundedRect(wx - 5, wy, 10, 6, 2, 2)
        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.drawLine(0, 0, 34, 0)

    def _draw_arm(self, painter: QPainter) -> None:
        joints = self.state.get("joints") or [0.4, -0.6]
        j0 = float(joints[0]) if joints else 0.4
        j1 = float(joints[1]) if len(joints) > 1 else -0.6
        x1, y1 = 68 * math.cos(j0), -68 * math.sin(j0)
        x2 = x1 + 52 * math.cos(j0 + j1)
        y2 = y1 - 52 * math.sin(j0 + j1)
        arm_pen = QPen(QColor("#a371f7"), 7)
        arm_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(arm_pen)
        painter.drawLine(QPointF(0, 0), QPointF(x1, y1))
        painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#58a6ff")))
        for px, py in [(0, 0), (x1, y1), (x2, y2)]:
            painter.drawEllipse(QPointF(px, py), 6, 6)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        ensure_dirs()
        self.packages = workspace.workspace_packages()
        self._package_by_path: dict[str, RosPackage] = {}
        self._package_labels: dict[str, str] = {}
        self._editor_pkg: RosPackage | None = None
        self._editor_rel: str | None = None
        self._all_files: list[str] = []
        self._all_dirs: list[str] = []
        self._ai_turns: list[tuple[str, str]] = []
        self._sim_running = False
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

        root.addWidget(self._build_topbar())
        workspace_area = self._build_workspace()
        root.addWidget(workspace_area, 1)

        self.setStatusBar(QStatusBar())
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick_sim)

        self._reload_workspace_packages(open_active=False)
        self.pkg_combo.currentIndexChanged.connect(self._editor_load_current_package)
        self.file_filter.textChanged.connect(self._refresh_file_list)
        if self.pkg_combo.count():
            self._editor_load_current_package()

        self._status("Ready. Workspace packages are editable and simulatable side by side.")

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
        b_save.clicked.connect(self._editor_save)
        b_reload = _button("Reload", compact=True)
        b_reload.clicked.connect(self._editor_reload)
        b_run = _button("Run", primary=True, compact=True)
        b_run.clicked.connect(self.sim_run)
        b_stop = _button("Stop", compact=True)
        b_stop.clicked.connect(self.sim_stop)
        b_docker = _button("Docker", compact=True)
        b_docker.clicked.connect(self._editor_docker_launch)
        for button in (b_save, b_reload, b_run, b_stop, b_docker):
            layout.addWidget(button)

        return bar

    def _build_workspace(self) -> QSplitter:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("workspace")
        splitter.setChildrenCollapsible(False)
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
        b_files = _tool_button("EX", "Explorer")
        b_files.clicked.connect(lambda: self.ed_file_tree.setFocus())
        b_run = _tool_button("Run", "Run active package simulation")
        b_run.clicked.connect(self.sim_run)
        b_ai = _tool_button("AI", "Open AI chat panel")
        b_ai.clicked.connect(self._focus_ai_panel)
        for button in (b_files, b_run, b_ai):
            rail_layout.addWidget(button)
        rail_layout.addStretch(1)
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
        b_open = _toolbar_button("Open", "Open workspace folder", 48)
        b_open.clicked.connect(self._add_workspace_folder)
        b_pkg = _toolbar_button("Pkg", "Add ROS package", 34)
        b_pkg.clicked.connect(self._add_workspace_package)
        b_new_file = _toolbar_button("+F", "New file", 30)
        b_new_file.clicked.connect(self._create_new_file)
        b_new_dir = _toolbar_button("+D", "New folder", 30)
        b_new_dir.clicked.connect(self._create_new_folder)
        b_refresh = _toolbar_button("R", "Refresh workspace", 28)
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
        b_new_workspace = _toolbar_button("New", "New empty workspace", 42)
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
        editor_layout.addWidget(self.ed_text, 1)
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
            "Lappa AI ready.\n"
            "Ask about the active ROS package, current file, launch setup, or simulation behavior."
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
        b_start = _button("Start", primary=True)
        b_start.setToolTip("Start Docker runtime")
        b_start.clicked.connect(self._docker_start)
        b_launch = _button("Launch")
        b_launch.setToolTip("Launch active package in Docker")
        b_launch.clicked.connect(self._docker_launch_active)
        b_stop = _button("Stop Run")
        b_stop.setToolTip("Stop ros2 launch process")
        b_stop.clicked.connect(self._docker_stop_launch)
        b_down = _button("Down")
        b_down.setToolTip("Stop Docker container")
        b_down.clicked.connect(self._docker_stop)
        row.addWidget(QLabel("Target"))
        row.addWidget(self.ros2_combo, 1)
        for button in (b_apply, b_start, b_launch, b_stop, b_down):
            row.addWidget(button)
        layout.addLayout(row)
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
            "Lappa AI: I have the IDE context now: "
            f"package={package_label}, file={file_label}. "
            "The chat panel is wired for the desktop workflow; connect the model backend here "
            "to turn this into code edits, ROS launch checks, and simulation guidance."
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
                self.ed_text.clear()

    def _add_workspace_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Add workspace folder",
            str(Path.home()),
        )
        if not folder:
            return
        try:
            workspace.add_workspace_root(folder)
            self._reload_workspace_packages()
            self._status(f"Workspace folder added: {folder}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Workspace", str(exc))

    def _add_workspace_package(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Add ROS2 package",
            str(Path.home()),
        )
        if not folder:
            return
        path = Path(folder).expanduser().resolve()
        if not workspace.is_ros_package_dir(path):
            QMessageBox.warning(self, "Workspace", "Selected folder has no package.xml.")
            return
        try:
            workspace.add_workspace_root(path)
            key = str(path)
            self._reload_workspace_packages(keep_key=key)
            self._status(f"Package added: {path.name}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Workspace", str(exc))

    def _new_workspace(self) -> None:
        workspace.create_workspace("Workspace", include_samples=False)
        self._reload_workspace_packages()
        self._status("New workspace created")

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
        self._editor_pkg = load_package(pkg.path)
        self._editor_rel = None
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
        try:
            text = read_file(self._editor_pkg, rel)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Open failed", str(exc))
            return
        self._editor_rel = rel
        self.ed_text.setPlainText(text)
        display = f"{self._editor_pkg.name}/{rel}"
        self.ed_path_label.setText(display)
        self.header_file_label.setText(display)
        self._refresh_file_list()

    def _editor_reload(self) -> None:
        if self._editor_rel:
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
        SESSION.notify_file_change(self._editor_rel)
        self._status(f"Saved {self._editor_pkg.name}/{self._editor_rel}")

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
        try:
            result = docker_bridge.start_runtime()
            self.docker_info.setPlainText(str(result))
            self._status("Docker runtime " + ("started" if result.get("ok") else "failed"))
        except Exception as exc:  # noqa: BLE001
            self.docker_info.setPlainText(str(exc))
            self._status(f"Docker start failed: {exc}")

    def _docker_stop(self) -> None:
        try:
            result = docker_bridge.stop_runtime()
            self.docker_info.setPlainText(str(result))
            self._status("Docker runtime stopped")
        except Exception as exc:  # noqa: BLE001
            self.docker_info.setPlainText(str(exc))
            self._status(f"Docker stop failed: {exc}")

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
                self.docker_info.setPlainText(msg)
                self._status(msg)
                return
        try:
            result = docker_bridge.launch_demo(demo)
            self.docker_info.setPlainText(str(result))
            msg = result.get("message") or result.get("error") or "Docker launch complete"
            self._status(str(msg)[:140])
        except Exception as exc:  # noqa: BLE001
            self.docker_info.setPlainText(str(exc))
            self._status(f"Docker launch failed: {exc}")

    def _docker_stop_launch(self) -> None:
        try:
            result = docker_bridge.stop_launch()
            self.docker_info.setPlainText(str(result))
            self._status("Docker launch stopped")
        except Exception as exc:  # noqa: BLE001
            self.docker_info.setPlainText(str(exc))
            self._status(f"Docker launch stop failed: {exc}")

    def _refresh_docker(self) -> None:
        if not hasattr(self, "docker_info"):
            return
        try:
            self.docker_info.setPlainText(str(docker_bridge.status()))
        except Exception as exc:  # noqa: BLE001
            self.docker_info.setPlainText(str(exc))

    def _goto(self, key: str) -> None:
        """Compatibility hook for screenshot automation."""
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
