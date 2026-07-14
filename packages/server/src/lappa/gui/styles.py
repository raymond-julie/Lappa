"""Qt stylesheet for the Lappa desktop IDE."""

STYLESHEET = """
* {
  font-family: "Segoe UI", "Inter", sans-serif;
  font-size: 13px;
  color: #e6edf3;
}

QMainWindow, QWidget#central {
  background: #0b1020;
}

QFrame#topbar {
  background: #0f172a;
  border-bottom: 1px solid #223049;
}

QLabel#brand {
  font-size: 21px;
  font-weight: 800;
  color: #f8fafc;
}

QLabel#brandSub, QLabel#muted, QLabel#metricTitle {
  color: #94a3b8;
}

QLabel#sectionTitle {
  color: #dbeafe;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}

QLabel#panelTitle {
  color: #f8fafc;
  font-size: 18px;
  font-weight: 800;
}

QLabel#pathLabel {
  color: #7dd3fc;
  font-family: "Cascadia Mono", "Consolas", monospace;
  font-size: 12px;
}

QLabel#statePill {
  background: #172554;
  color: #bfdbfe;
  border: 1px solid #1d4ed8;
  border-radius: 10px;
  padding: 4px 10px;
  font-weight: 700;
}

QFrame#projectPanel, QFrame#editorPanel, QFrame#simPanel {
  background: #0b1020;
  border-right: 1px solid #1e293b;
}

QFrame#simPanel {
  border-right: none;
  border-left: 1px solid #1e293b;
}

QFrame#metricCard, QFrame#controlPanel {
  background: #111827;
  border: 1px solid #263449;
  border-radius: 8px;
}

QLabel#metricValue {
  color: #f8fafc;
  font-family: "Cascadia Mono", "Consolas", monospace;
  font-weight: 700;
}

QPushButton {
  background: #1f2937;
  color: #e5e7eb;
  border: 1px solid #334155;
  border-radius: 7px;
  padding: 8px 12px;
  font-weight: 700;
}

QPushButton:hover {
  border-color: #38bdf8;
  background: #243244;
}

QPushButton[primary="true"] {
  background: #2563eb;
  border-color: #2563eb;
  color: #ffffff;
}

QPushButton[primary="true"]:hover {
  background: #1d4ed8;
  border-color: #60a5fa;
}

QPushButton[compact="true"] {
  padding: 6px 9px;
}

QLineEdit, QComboBox, QTextEdit, QListWidget, QPlainTextEdit {
  background: #0f172a;
  border: 1px solid #263449;
  border-radius: 7px;
  padding: 6px 9px;
  selection-background-color: #2563eb;
}

QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QListWidget:focus, QPlainTextEdit:focus {
  border-color: #38bdf8;
}

QPlainTextEdit#codeEditor {
  background: #080d18;
  color: #e5edf7;
  border: 1px solid #263449;
  border-radius: 8px;
  padding: 10px;
  font-family: "Cascadia Mono", "Consolas", monospace;
}

QTextEdit#logBox {
  background: #080d18;
  color: #bfd2e8;
  font-family: "Cascadia Mono", "Consolas", monospace;
}

QListWidget::item {
  min-height: 24px;
  padding: 6px;
  border-radius: 5px;
}

QListWidget::item:selected {
  background: #1e3a8a;
  color: #ffffff;
}

QTabWidget#opsTabs::pane {
  border: 1px solid #263449;
  border-radius: 8px;
  top: -1px;
  background: #0f172a;
}

QTabBar::tab {
  background: #111827;
  color: #94a3b8;
  border: 1px solid #263449;
  padding: 7px 12px;
  margin-right: 3px;
  border-top-left-radius: 7px;
  border-top-right-radius: 7px;
}

QTabBar::tab:selected {
  color: #f8fafc;
  background: #1f2937;
  border-color: #38bdf8;
}

QSplitter::handle {
  background: #1e293b;
}

QStatusBar {
  background: #0f172a;
  color: #94a3b8;
  border-top: 1px solid #223049;
}

QSlider::groove:horizontal {
  height: 6px;
  background: #263449;
  border-radius: 3px;
}

QSlider::sub-page:horizontal {
  background: #2563eb;
  border-radius: 3px;
}

QSlider::handle:horizontal {
  width: 16px;
  margin: -6px 0;
  background: #7dd3fc;
  border: 2px solid #0f172a;
  border-radius: 8px;
}
"""
