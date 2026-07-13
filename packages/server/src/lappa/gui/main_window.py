"""Lappa modern Qt desktop — IDE editor, sim, demos, 3D, packages, Docker."""

from __future__ import annotations

import math

from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QFontDatabase
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSlider,
    QStackedWidget,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from lappa import __version__, docker_bridge, models3d, packager, ros2_versions
from lappa.config import DEMOS_ROOT, ensure_dirs
from lappa.gui.styles import STYLESHEET
from lappa.package_loader import list_demo_packages, load_package, read_file, write_file
from lappa.sim.session import SESSION


def _btn_primary(text: str) -> QPushButton:
    b = QPushButton(text)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setStyleSheet(
        "QPushButton { background: #1f6feb; color: white; border: none; "
        "border-radius: 8px; padding: 10px 16px; font-weight: 700; }"
        "QPushButton:hover { background: #388bfd; }"
    )
    return b


def _btn_ghost(text: str) -> QPushButton:
    b = QPushButton(text)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setStyleSheet(
        "QPushButton { background: #21262d; color: #e6edf3; border: 1px solid #30363d; "
        "border-radius: 8px; padding: 10px 14px; font-weight: 600; }"
        "QPushButton:hover { border-color: #58a6ff; }"
        "QPushButton:checked { background: #388bfd33; border-color: #58a6ff; color: #58a6ff; }"
    )
    return b


class SimCanvas(QWidget):
    """2D top-down sim visualization."""

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumSize(480, 360)
        self.state: dict = {"x": 0.0, "y": 0.0, "theta": 0.0, "kind": "diff_drive_2w", "lidar": []}
        self.trail: list[tuple[float, float]] = []
        self.setStyleSheet("background: #0a0e14; border-radius: 12px;")

    def set_state(self, st: dict) -> None:
        self.state = st or self.state
        x, y = float(st.get("x") or 0), float(st.get("y") or 0)
        self.trail.append((x, y))
        if len(self.trail) > 200:
            self.trail = self.trail[-200:]
        self.update()

    def clear_trail(self) -> None:
        self.trail.clear()
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor("#0a0e14"))
        # grid
        pen = QPen(QColor("#1c2533"))
        pen.setWidth(1)
        p.setPen(pen)
        for x in range(0, w, 40):
            p.drawLine(x, 0, x, h)
        for y in range(0, h, 40):
            p.drawLine(0, y, w, y)
        cx, cy = w / 2, h / 2
        scale = 80.0
        # trail
        if len(self.trail) > 1:
            pen = QPen(QColor(56, 139, 253, 120))
            pen.setWidth(2)
            p.setPen(pen)
            for i in range(1, len(self.trail)):
                x0, y0 = self.trail[i - 1]
                x1, y1 = self.trail[i]
                p.drawLine(
                    QPointF(cx + x0 * scale, cy - y0 * scale),
                    QPointF(cx + x1 * scale, cy - y1 * scale),
                )
        x = float(self.state.get("x") or 0)
        y = float(self.state.get("y") or 0)
        th = float(self.state.get("theta") or 0)
        rx, ry = cx + x * scale, cy - y * scale
        # lidar
        lidar = self.state.get("lidar") or []
        if lidar:
            pen = QPen(QColor(63, 185, 80, 50))
            p.setPen(pen)
            n = len(lidar)
            for i, r in enumerate(lidar):
                a = th + (i / n) * math.pi * 2
                lx = rx + math.cos(a) * float(r) * 12
                ly = ry - math.sin(a) * float(r) * 12
                p.drawLine(QPointF(rx, ry), QPointF(lx, ly))
        p.save()
        p.translate(rx, ry)
        p.rotate(-math.degrees(th))
        kind = self.state.get("kind") or "diff_drive_2w"
        if kind == "omni_3w":
            p.setBrush(QBrush(QColor("#1f6feb")))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(0, 0), 18, 18)
        elif kind == "simple_arm":
            p.setPen(QPen(QColor("#a371f7"), 5))
            joints = self.state.get("joints") or [0.4, -0.6]
            j0 = float(joints[0]) if joints else 0.4
            j1 = float(joints[1]) if len(joints) > 1 else -0.6
            x1, y1 = 50 * math.cos(j0), -50 * math.sin(j0)
            x2 = x1 + 40 * math.cos(j0 + j1)
            y2 = y1 - 40 * math.sin(j0 + j1)
            p.drawLine(QPointF(0, 0), QPointF(x1, y1))
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        else:
            p.setBrush(QBrush(QColor("#3fb950")))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(-16, -12, 32, 24, 4, 4)
            p.setBrush(QBrush(QColor("#111")))
            p.drawRect(-14, -16, 10, 6)
            p.drawRect(-14, 10, 10, 6)
        # heading
        p.setPen(QPen(QColor("#ffffff"), 2))
        p.drawLine(0, 0, 22, 0)
        p.restore()
        p.setPen(QColor("#8b949e"))
        p.setFont(QFont("Segoe UI", 9))
        p.drawText(
            12,
            18,
            f"{kind}  pose=({x:.2f}, {y:.2f}, {th:.2f})",
        )


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        ensure_dirs()
        self.setWindowTitle(f"Lappa · ROS2 IDE · v{__version__}")
        self.resize(1200, 780)
        self.setMinimumSize(1000, 640)
        self.setStyleSheet(STYLESHEET)

        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(210)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(14, 18, 14, 14)
        brand = QLabel("◆ Lappa")
        brand.setObjectName("brand")
        sl.addWidget(brand)
        sub = QLabel("ROS2 package IDE")
        sub.setObjectName("brandSub")
        sl.addWidget(sub)
        sl.addSpacing(12)

        self._nav: list[QPushButton] = []
        self._keys = ["editor", "sim", "demos", "models", "packages", "ros2"]
        labels = {
            "editor": "📝  Editor",
            "sim": "🎛  Simulation",
            "demos": "🤖  Demos",
            "models": "🧊  3D models",
            "packages": "📦  Packages",
            "ros2": "🐳  ROS2 / Docker",
        }
        for k in self._keys:
            b = _btn_ghost(labels[k])
            b.setCheckable(True)
            b.setStyleSheet(
                b.styleSheet()
                + "QPushButton { text-align: left; }"
            )
            b.clicked.connect(lambda _=False, key=k: self._goto(key))
            self._nav.append(b)
            sl.addWidget(b)
        sl.addStretch(1)
        sl.addWidget(QLabel(f"v{__version__}"))
        root.addWidget(side)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        self._editor_pkg = None
        self._editor_rel: str | None = None
        self.page_editor = self._page_editor()
        self.page_sim = self._page_sim()
        self.page_demos = self._page_demos()
        self.page_models = self._page_models()
        self.page_packages = self._page_packages()
        self.page_ros2 = self._page_ros2()
        for w in (
            self.page_editor,
            self.page_sim,
            self.page_demos,
            self.page_models,
            self.page_packages,
            self.page_ros2,
        ):
            self.stack.addWidget(w)

        self.setStatusBar(QStatusBar())
        self._status("Ready · open a package in Editor · native sim offline")
        self._goto("editor")

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick_sim)
        self._sim_running = False

    def _status(self, msg: str) -> None:
        self.statusBar().showMessage(msg)

    def _goto(self, key: str) -> None:
        idx = self._keys.index(key)
        self.stack.setCurrentIndex(idx)
        for i, b in enumerate(self._nav):
            b.setChecked(i == idx)

    def _page_editor(self) -> QWidget:
        """Package IDE: open demo sources, edit, save — same tree Docker mounts."""
        page = QWidget()
        lay = QHBoxLayout(page)
        lay.setContentsMargins(16, 16, 16, 16)

        left = QVBoxLayout()
        title = QLabel("Package editor")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        left.addWidget(title)
        hint = QLabel(
            "Open package sources here. Docker launch mounts packages/demos → /ws/src."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #8b949e;")
        left.addWidget(hint)

        self.ed_pkg_combo = QComboBox()
        for p in list_demo_packages(DEMOS_ROOT):
            self.ed_pkg_combo.addItem(p.name)
        self.ed_pkg_combo.currentTextChanged.connect(self._editor_load_package)
        left.addWidget(self.ed_pkg_combo)

        self.ed_file_list = QListWidget()
        self.ed_file_list.itemClicked.connect(self._editor_open_file)
        left.addWidget(self.ed_file_list, 1)

        brow = QHBoxLayout()
        b_save = _btn_primary("💾 Save")
        b_save.clicked.connect(self._editor_save)
        b_reload = _btn_ghost("Reload file")
        b_reload.clicked.connect(self._editor_reload)
        b_docker = _btn_ghost("▶ Docker launch")
        b_docker.clicked.connect(self._editor_docker_launch)
        brow.addWidget(b_save)
        brow.addWidget(b_reload)
        brow.addWidget(b_docker)
        left.addLayout(brow)
        lay.addLayout(left, 1)

        right = QVBoxLayout()
        self.ed_path_label = QLabel("No file open")
        self.ed_path_label.setStyleSheet("color: #58a6ff; font-family: Consolas, monospace;")
        right.addWidget(self.ed_path_label)
        self.ed_text = QPlainTextEdit()
        mono = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        mono.setPointSize(11)
        self.ed_text.setFont(mono)
        self.ed_text.setStyleSheet(
            "QPlainTextEdit { background: #0d1117; color: #e6edf3; "
            "border: 1px solid #30363d; border-radius: 8px; padding: 8px; }"
        )
        right.addWidget(self.ed_text, 1)
        lay.addLayout(right, 3)

        if self.ed_pkg_combo.count():
            self._editor_load_package(self.ed_pkg_combo.currentText())
        return page

    def _editor_load_package(self, name: str) -> None:
        name = (name or "").strip()
        if not name:
            return
        path = DEMOS_ROOT / name
        if not path.is_dir():
            return
        self._editor_pkg = load_package(path)
        self._editor_rel = None
        self.ed_file_list.clear()
        for f in self._editor_pkg.files:
            self.ed_file_list.addItem(f)
        self.ed_path_label.setText(f"{name}/ — {len(self._editor_pkg.files)} files")
        self.ed_text.clear()
        # Prefer teleop / package.xml
        prefer = next(
            (f for f in self._editor_pkg.files if f.endswith("teleop.py")),
            None,
        ) or next((f for f in self._editor_pkg.files if f == "package.xml"), None)
        if prefer:
            matches = self.ed_file_list.findItems(prefer, Qt.MatchFlag.MatchExactly)
            if matches:
                self.ed_file_list.setCurrentItem(matches[0])
                self._editor_open_file(matches[0])

    def _editor_open_file(self, item: QListWidgetItem) -> None:
        if not self._editor_pkg or item is None:
            return
        rel = item.text()
        try:
            text = read_file(self._editor_pkg, rel)
            self._editor_rel = rel
            self.ed_text.setPlainText(text)
            self.ed_path_label.setText(f"{self._editor_pkg.name}/{rel}")
            self._status(f"Opened {rel}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Open failed", str(exc))

    def _editor_reload(self) -> None:
        if self._editor_rel and self.ed_file_list.currentItem():
            self._editor_open_file(self.ed_file_list.currentItem())

    def _editor_save(self) -> None:
        if not self._editor_pkg or not self._editor_rel:
            QMessageBox.information(self, "Save", "Open a file first.")
            return
        try:
            write_file(self._editor_pkg, self._editor_rel, self.ed_text.toPlainText())
            self._status(f"Saved {self._editor_pkg.name}/{self._editor_rel}")
            # Notify native sim hot-reload if running same package
            SESSION.notify_file_change(self._editor_rel)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Save failed", str(exc))

    def _editor_docker_launch(self) -> None:
        demo = self.ed_pkg_combo.currentText() or "diff_drive_2w"
        try:
            r = docker_bridge.launch_demo(demo)
            msg = r.get("message") or r.get("error") or str(r)
            self._status(msg[:120])
            if not r.get("ok"):
                QMessageBox.information(
                    self,
                    "Docker launch",
                    f"{msg}\n\nFallback: use Simulation page (native) or "
                    f"`lappa sim start --demo {demo}`",
                )
            else:
                QMessageBox.information(
                    self,
                    "Docker launch",
                    f"Launched {demo} in container.\n"
                    f"{r.get('launch_path')}\n\n"
                    "Package sources are the files you edit in this IDE.",
                )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Docker launch", str(exc))

    def _page_sim(self) -> QWidget:
        page = QWidget()
        lay = QHBoxLayout(page)
        lay.setContentsMargins(20, 16, 20, 16)
        left = QVBoxLayout()
        title = QLabel("Simulation")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        left.addWidget(title)
        self.canvas = SimCanvas()
        left.addWidget(self.canvas, 1)
        lay.addLayout(left, 3)

        right = QFrame()
        right.setObjectName("card")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(14, 14, 14, 14)
        rl.addWidget(QLabel("Teleop"))
        form = QFormLayout()
        self.sl_lx = QSlider(Qt.Orientation.Horizontal)
        self.sl_lx.setRange(-100, 100)
        self.sl_ly = QSlider(Qt.Orientation.Horizontal)
        self.sl_ly.setRange(-100, 100)
        self.sl_az = QSlider(Qt.Orientation.Horizontal)
        self.sl_az.setRange(-150, 150)
        form.addRow("linear.x", self.sl_lx)
        form.addRow("linear.y", self.sl_ly)
        form.addRow("angular.z", self.sl_az)
        rl.addLayout(form)
        self.lbl_twist = QLabel("lx=0 ly=0 az=0")
        self.lbl_twist.setStyleSheet("color: #8b949e; font-family: monospace;")
        rl.addWidget(self.lbl_twist)
        row = QHBoxLayout()
        b_run = _btn_primary("▶ Run")
        b_run.clicked.connect(self.sim_run)
        b_stop = _btn_ghost("■ Stop")
        b_stop.clicked.connect(self.sim_stop)
        b_zero = _btn_ghost("Zero")
        b_zero.clicked.connect(self.sim_zero)
        row.addWidget(b_run)
        row.addWidget(b_stop)
        row.addWidget(b_zero)
        rl.addLayout(row)
        rl.addWidget(QLabel("Active demo"))
        self.demo_combo = QComboBox()
        for p in list_demo_packages(DEMOS_ROOT):
            self.demo_combo.addItem(p.name)
        rl.addWidget(self.demo_combo)
        rl.addStretch(1)
        self.sim_log = QTextEdit()
        self.sim_log.setReadOnly(True)
        self.sim_log.setMaximumHeight(140)
        rl.addWidget(self.sim_log)
        lay.addWidget(right, 1)
        return page

    def sim_zero(self) -> None:
        self.sl_lx.setValue(0)
        self.sl_ly.setValue(0)
        self.sl_az.setValue(0)

    def sim_run(self) -> None:
        demo = self.demo_combo.currentText() or "diff_drive_2w"
        path = DEMOS_ROOT / demo
        SESSION.start(demo, path if path.is_dir() else None)
        self.canvas.clear_trail()
        self._sim_running = True
        self._timer.start(50)
        self.sim_log.append(f"sim start {demo}")
        self._status(f"Running {demo}")

    def sim_stop(self) -> None:
        SESSION.stop()
        self._sim_running = False
        self._timer.stop()
        self.sim_log.append("sim stop")
        self._status("Stopped")

    def _tick_sim(self) -> None:
        if not self._sim_running:
            return
        lx = self.sl_lx.value() / 100.0
        ly = self.sl_ly.value() / 100.0
        az = self.sl_az.value() / 100.0
        SESSION.cmd(lx, ly, az)
        st = SESSION.tick()
        self.canvas.set_state(st)
        self.lbl_twist.setText(f"lx={lx:.2f} ly={ly:.2f} az={az:.2f}")

    def _page_demos(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.addWidget(QLabel("Robot demos"))
        self.demo_list = QListWidget()
        for p in list_demo_packages(DEMOS_ROOT):
            self.demo_list.addItem(f"{p.name}")
        lay.addWidget(self.demo_list, 1)
        b = _btn_primary("Open in Simulation")
        b.clicked.connect(self._open_demo_in_sim)
        lay.addWidget(b, alignment=Qt.AlignmentFlag.AlignLeft)
        return page

    def _open_demo_in_sim(self) -> None:
        item = self.demo_list.currentItem()
        if not item:
            return
        name = item.text().strip()
        idx = self.demo_combo.findText(name)
        if idx >= 0:
            self.demo_combo.setCurrentIndex(idx)
        self._goto("sim")
        self.sim_run()

    def _page_models(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(24, 20, 24, 20)
        title = QLabel("3D models")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        lay.addWidget(title)
        lay.addWidget(QLabel("Procedural meshes · auto-fit · full robot build"))
        form = QFormLayout()
        self.mesh_preset = QComboBox()
        for p in models3d.list_presets():
            self.mesh_preset.addItem(p["id"])
        self.mesh_name = QComboBox()
        self.mesh_name.setEditable(True)
        self.mesh_name.setCurrentText("my_chassis")
        form.addRow("Preset", self.mesh_preset)
        form.addRow("Name", self.mesh_name)
        lay.addLayout(form)
        row = QHBoxLayout()
        b1 = _btn_primary("Create mesh")
        b1.clicked.connect(self._create_mesh)
        b2 = _btn_ghost("Build full 3D robot")
        b2.clicked.connect(self._build_robot)
        b3 = _btn_ghost("Refresh library")
        b3.clicked.connect(self._refresh_meshes)
        row.addWidget(b1)
        row.addWidget(b2)
        row.addWidget(b3)
        row.addStretch(1)
        lay.addLayout(row)
        self.mesh_list = QListWidget()
        lay.addWidget(self.mesh_list, 1)
        self.model_log = QTextEdit()
        self.model_log.setReadOnly(True)
        self.model_log.setMaximumHeight(120)
        lay.addWidget(self.model_log)
        self._refresh_meshes()
        return page

    def _create_mesh(self) -> None:
        try:
            r = models3d.create_model(
                self.mesh_preset.currentText(),
                name=self.mesh_name.currentText() or None,
            )
            self.model_log.append(f"created {r['id']} ({r['bytes']} bytes)")
            self._refresh_meshes()
        except Exception as exc:  # noqa: BLE001
            self.model_log.append(f"error: {exc}")

    def _build_robot(self) -> None:
        demo = self.demo_combo.currentText() or "diff_drive_2w"
        try:
            r = models3d.build_aligned_robot(demo)
            self.model_log.append(
                f"build-robot {r['package']}: {r['links']} links · {r['scene']['count']} scene nodes"
            )
            self._status(f"3D robot built for {demo}")
            QMessageBox.information(
                self,
                "Lappa 3D",
                f"Built aligned robot for {demo}\nLinks: {r['links']}\nURDF: {r['urdf']}",
            )
        except Exception as exc:  # noqa: BLE001
            self.model_log.append(f"error: {exc}")

    def _refresh_meshes(self) -> None:
        self.mesh_list.clear()
        for m in models3d.list_library():
            self.mesh_list.addItem(f"{m['id']}  ({m.get('bytes', 0)} B)")

    def _page_packages(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.addWidget(QLabel("Package bundles"))
        self.pkg_list = QListWidget()
        for p in packager.list_bundleable():
            name = p["name"] if isinstance(p, dict) else str(p)
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.pkg_list.addItem(item)
        lay.addWidget(self.pkg_list, 1)
        b = _btn_primary("Create bundle zip")
        b.clicked.connect(self._bundle)
        lay.addWidget(b, alignment=Qt.AlignmentFlag.AlignLeft)
        self.pkg_log = QTextEdit()
        self.pkg_log.setReadOnly(True)
        self.pkg_log.setMaximumHeight(100)
        lay.addWidget(self.pkg_log)
        return page

    def _bundle(self) -> None:
        names = []
        for i in range(self.pkg_list.count()):
            it = self.pkg_list.item(i)
            if it.checkState() == Qt.CheckState.Checked:
                names.append(it.text())
        try:
            r = packager.package_bundle(names or None, distro=None)
            self.pkg_log.append(f"bundle {r.get('filename')} ({r.get('size_bytes')} bytes)")
            self._status("Bundle created")
        except Exception as exc:  # noqa: BLE001
            self.pkg_log.append(f"error: {exc}")

    def _page_ros2(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(24, 20, 24, 20)
        title = QLabel("ROS2 & Docker")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        lay.addWidget(title)
        form = QFormLayout()
        self.ros2_combo = QComboBox()
        for v in ros2_versions.list_versions():
            self.ros2_combo.addItem(f"{v['id']} — {v.get('name', '')}", v["id"])
        sel = ros2_versions.get_selected().get("id")
        for i in range(self.ros2_combo.count()):
            if self.ros2_combo.itemData(i) == sel:
                self.ros2_combo.setCurrentIndex(i)
        form.addRow("Target distro", self.ros2_combo)
        lay.addLayout(form)
        b = _btn_primary("Apply ROS2 version")
        b.clicked.connect(self._set_ros2)
        lay.addWidget(b, alignment=Qt.AlignmentFlag.AlignLeft)

        drow = QHBoxLayout()
        b_up = _btn_primary("▶ Start Docker runtime")
        b_up.clicked.connect(self._docker_start)
        b_launch = _btn_ghost("Launch sim in Docker")
        b_launch.clicked.connect(self._docker_launch_active)
        b_stop_l = _btn_ghost("Stop launch")
        b_stop_l.clicked.connect(self._docker_stop_launch)
        b_down = _btn_ghost("Stop Docker")
        b_down.clicked.connect(self._docker_stop)
        drow.addWidget(b_up)
        drow.addWidget(b_launch)
        drow.addWidget(b_stop_l)
        drow.addWidget(b_down)
        lay.addLayout(drow)

        bridge = QLabel(
            "Bridge: Editor saves write packages/demos → container /ws/src. "
            "Native Simulation stays available offline without Docker."
        )
        bridge.setWordWrap(True)
        bridge.setStyleSheet("color: #8b949e; margin: 8px 0;")
        lay.addWidget(bridge)

        self.docker_info = QTextEdit()
        self.docker_info.setReadOnly(True)
        lay.addWidget(self.docker_info, 1)
        b2 = _btn_ghost("Refresh Docker status")
        b2.clicked.connect(self._refresh_docker)
        lay.addWidget(b2, alignment=Qt.AlignmentFlag.AlignLeft)
        self._refresh_docker()
        return page

    def _docker_start(self) -> None:
        try:
            r = docker_bridge.start_runtime()
            self.docker_info.setPlainText(str(r))
            self._status("Docker runtime " + ("ok" if r.get("ok") else "failed"))
        except Exception as exc:  # noqa: BLE001
            self.docker_info.setPlainText(str(exc))

    def _docker_stop(self) -> None:
        try:
            r = docker_bridge.stop_runtime()
            self.docker_info.setPlainText(str(r))
            self._status("Docker stopped")
        except Exception as exc:  # noqa: BLE001
            self.docker_info.setPlainText(str(exc))

    def _docker_launch_active(self) -> None:
        demo = (
            self.ed_pkg_combo.currentText()
            if hasattr(self, "ed_pkg_combo")
            else None
        ) or (self.demo_combo.currentText() if hasattr(self, "demo_combo") else None)
        demo = demo or "diff_drive_2w"
        try:
            r = docker_bridge.launch_demo(demo)
            self.docker_info.setPlainText(str(r))
            self._status(f"Docker launch {demo}: {'ok' if r.get('ok') else 'fail'}")
        except Exception as exc:  # noqa: BLE001
            self.docker_info.setPlainText(str(exc))

    def _docker_stop_launch(self) -> None:
        try:
            r = docker_bridge.stop_launch()
            self.docker_info.setPlainText(str(r))
            self._status("Docker launch stopped")
        except Exception as exc:  # noqa: BLE001
            self.docker_info.setPlainText(str(exc))

    def _set_ros2(self) -> None:
        distro = self.ros2_combo.currentData()
        try:
            r = ros2_versions.set_selected(str(distro))
            docker_bridge.apply_ros2_dockerfile(str(distro))
            self._status(f"ROS2 → {r['id']}")
            self.docker_info.append(f"selected {r}")
        except Exception as exc:  # noqa: BLE001
            self.docker_info.append(f"error: {exc}")

    def _refresh_docker(self) -> None:
        try:
            st = docker_bridge.status()
            self.docker_info.setPlainText(str(st))
        except Exception as exc:  # noqa: BLE001
            self.docker_info.setPlainText(str(exc))
