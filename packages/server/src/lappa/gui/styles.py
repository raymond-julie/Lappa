"""Modern dark theme for Lappa Qt desktop."""

STYLESHEET = """
* {
  font-family: "Segoe UI", "Inter", "JetBrains Mono", sans-serif;
  font-size: 13px;
  color: #e6edf3;
}
QMainWindow, QWidget#central {
  background: #0d1117;
}
QFrame#sidebar {
  background: #010409;
  border-right: 1px solid #21262d;
}
QLabel#brand {
  font-size: 18px;
  font-weight: 700;
  color: #a371f7;
  padding: 4px;
}
QLabel#brandSub {
  color: #8b949e;
  font-size: 11px;
}
QPushButton {
  border-radius: 8px;
  padding: 8px 12px;
}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QListWidget {
  background: #0d1117;
  border: 1px solid #30363d;
  border-radius: 8px;
  padding: 6px 10px;
  selection-background-color: #388bfd;
}
QListWidget::item {
  padding: 8px;
  border-radius: 6px;
}
QListWidget::item:selected {
  background: #21262d;
  color: #58a6ff;
}
QStatusBar {
  background: #010409;
  color: #8b949e;
  border-top: 1px solid #21262d;
}
QSlider::groove:horizontal {
  height: 6px;
  background: #21262d;
  border-radius: 3px;
}
QSlider::handle:horizontal {
  width: 16px;
  margin: -6px 0;
  background: #58a6ff;
  border-radius: 8px;
}
QFrame#card {
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 12px;
}
"""
