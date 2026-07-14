"""Qt stylesheet for the Lappa desktop IDE."""

STYLESHEET = """
* {
  font-family: "Segoe UI", "Inter", sans-serif;
  font-size: 12px;
  color: #e6edf3;
}

QMainWindow, QWidget#central, QWidget#workbenchPage {
  background: #0b1020;
}

QFrame#welcomePage {
  background: #080d18;
}

QFrame#welcomeStage, QFrame#welcomeActions {
  background: transparent;
}

QLabel#welcomeIcon {
  background: transparent;
}

QLabel#welcomeBrand {
  color: #f8fafc;
  font-size: 19px;
  font-weight: 800;
}

QLabel#welcomeProduct, QLabel#welcomeVersion, QLabel#welcomeMeta {
  color: #7f91a8;
  font-size: 11px;
}

QLabel#welcomeProduct {
  font-weight: 700;
}

QLabel#welcomeTitle {
  color: #f8fafc;
  font-size: 30px;
  font-weight: 700;
}

QLabel#welcomeSubtitle {
  color: #9fb4cc;
  font-size: 13px;
}

QFrame#welcomeWorkspacePanel {
  background: #0f172a;
  border: 1px solid #263449;
  border-radius: 8px;
}

QLabel#welcomeWorkspaceName {
  color: #f8fafc;
  font-size: 16px;
  font-weight: 700;
}

QLabel#welcomeRoot {
  color: #8fa6bf;
  font-family: "Cascadia Mono", "Consolas", monospace;
  font-size: 11px;
}

QPushButton#welcomeAction {
  min-width: 290px;
  padding: 9px 13px;
  text-align: left;
}

QListWidget#welcomePackageList {
  background: #0b1220;
  border: 1px solid #223049;
  border-radius: 5px;
  padding: 4px;
}

QFrame#topbar {
  background: #0f172a;
  border-bottom: 1px solid #223049;
}

QLabel#brand {
  font-size: 16px;
  font-weight: 800;
  color: #f8fafc;
}

QLabel#brandSub {
  font-size: 11px;
}

QLabel#brandSub, QLabel#muted, QLabel#metricTitle {
  color: #94a3b8;
}

QLabel#sectionTitle {
  color: #dbeafe;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}

QLabel#panelTitle {
  color: #f8fafc;
  font-size: 15px;
  font-weight: 800;
}

QLabel#panelTitleSmall {
  color: #f8fafc;
  font-size: 12px;
  font-weight: 800;
  text-transform: uppercase;
}

QLabel#pathLabel {
  color: #7dd3fc;
  font-family: "Cascadia Mono", "Consolas", monospace;
  font-size: 11px;
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

QFrame#activityRail {
  background: #080d18;
  border-right: 1px solid #1e293b;
}

QFrame#explorerPanel {
  background: #0b1020;
}

QFrame#editorHeader {
  background: #0b1020;
  border-bottom: 1px solid #1e293b;
}

QFrame#editorBody {
  background: #0b1020;
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

QFrame#dockerDiagnosticPanel {
  background: #0b1220;
  border: 1px solid #263449;
  border-radius: 5px;
}

QLabel#dockerStatusName {
  color: #8293a8;
  font-size: 11px;
}

QLabel#dockerStatusValue {
  color: #91a4ba;
  font-family: "Cascadia Mono", "Consolas", monospace;
  font-size: 11px;
  font-weight: 700;
}

QLabel#dockerStatusValue[statusLevel="ok"] {
  color: #55d187;
}

QLabel#dockerStatusValue[statusLevel="warn"] {
  color: #e7b84b;
}

QLabel#dockerStatusValue[statusLevel="error"] {
  color: #ff7b72;
}

QLabel#dockerGuidance {
  color: #b8c8da;
  padding: 2px 0;
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
  border-radius: 5px;
  padding: 5px 9px;
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
  padding: 3px 8px;
}

QToolButton {
  background: transparent;
  color: #94a3b8;
  border: 1px solid transparent;
  border-radius: 5px;
  font-weight: 800;
}

QToolButton:hover {
  background: #111827;
  color: #e5edf7;
  border-color: #263449;
}

QLineEdit, QComboBox, QTextEdit, QListWidget, QTreeWidget, QPlainTextEdit {
  background: #0f172a;
  border: 1px solid #263449;
  border-radius: 5px;
  padding: 4px 6px;
  selection-background-color: #2563eb;
}

QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QListWidget:focus, QTreeWidget:focus, QPlainTextEdit:focus {
  border-color: #38bdf8;
}

QPlainTextEdit#codeEditor {
  background: #080d18;
  color: #e5edf7;
  border: 1px solid #263449;
  border-radius: 5px;
  padding: 8px;
  font-family: "Cascadia Mono", "Consolas", monospace;
}

QWidget#modelPreview {
  background: #080d18;
  border: 1px solid #263449;
  border-radius: 5px;
}

QTextEdit#logBox {
  background: #080d18;
  color: #bfd2e8;
  font-family: "Cascadia Mono", "Consolas", monospace;
}

QTextEdit#aiChat {
  background: #080d18;
  color: #d7e5f5;
  font-family: "Segoe UI", "Inter", sans-serif;
  line-height: 1.4;
}

QListWidget::item, QTreeWidget::item {
  min-height: 18px;
  padding: 3px;
  border-radius: 3px;
}

QTreeWidget#fileTree {
  padding: 4px;
}

QListWidget::item:selected, QTreeWidget::item:selected {
  background: #1e3a8a;
  color: #ffffff;
}

QTabWidget#opsTabs::pane {
  border: 1px solid #263449;
  border-radius: 5px;
  top: -1px;
  background: #0f172a;
}

QTabBar::tab {
  background: #111827;
  color: #94a3b8;
  border: 1px solid #263449;
  padding: 5px 10px;
  margin-right: 2px;
  border-top-left-radius: 5px;
  border-top-right-radius: 5px;
}

QTabBar::tab:selected {
  color: #f8fafc;
  background: #1f2937;
  border-color: #38bdf8;
}

QSplitter::handle {
  background: #1e293b;
}

QSplitter#centerSplitter::handle:vertical {
  height: 7px;
  background: #172033;
  border-top: 1px solid #263449;
  border-bottom: 1px solid #263449;
}

QSplitter#editorViewSplitter::handle:horizontal {
  width: 6px;
  background: #172033;
  border-left: 1px solid #263449;
  border-right: 1px solid #263449;
}

QStatusBar {
  background: #0f172a;
  color: #94a3b8;
  border-top: 1px solid #223049;
}

QLabel#statusInfo {
  color: #9fb4cc;
  font-family: "Cascadia Mono", "Consolas", monospace;
  font-size: 11px;
  padding: 0 8px;
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
