"""DW2 design tokens for a dense, readable native engineering workspace.

Version 1: system typography, explicit focus/selection, dark/light/high-contrast
themes, comfortable/compact density, and no motion effects. Colours indicate
presentation state only, never a calculation's validity.
"""

from dataclasses import dataclass

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

DESIGN_VERSION = 2


@dataclass(frozen=True)
class Theme:
    """Editable visual tokens; no engineering meaning or unit conversion."""

    canvas: str
    panel: str
    raised: str
    text: str
    muted: str
    border: str
    accent: str
    selected_text: str


THEMES = {
    "Dark": Theme(
        "#121B22", "#1A2630", "#23333F", "#EDF3F5", "#B0C0CB", "#435764", "#82D7CC", "#102A28"
    ),
    "Light": Theme(
        "#F1F5F7", "#FFFFFF", "#E7EEF2", "#172C37", "#4C6371", "#9AAFB9", "#006E64", "#FFFFFF"
    ),
    "High contrast": Theme(
        "#000000", "#080808", "#161616", "#FFFFFF", "#EEEEEE", "#FFFFFF", "#FFFF00", "#000000"
    ),
}


def apply_design(app: QApplication, theme_name: str, compact: bool) -> None:
    """Apply theme and target sizing consistently; no animations are enabled."""
    theme = THEMES[theme_name]
    palette = QPalette()
    for role, colour in (
        (QPalette.ColorRole.Window, theme.panel),
        (QPalette.ColorRole.Base, theme.canvas),
        (QPalette.ColorRole.AlternateBase, theme.raised),
        (QPalette.ColorRole.Text, theme.text),
        (QPalette.ColorRole.PlaceholderText, theme.muted),
        (QPalette.ColorRole.WindowText, theme.text),
        (QPalette.ColorRole.Button, theme.raised),
        (QPalette.ColorRole.ButtonText, theme.text),
        (QPalette.ColorRole.Highlight, theme.accent),
        (QPalette.ColorRole.HighlightedText, theme.selected_text),
        (QPalette.ColorRole.ToolTipBase, theme.raised),
        (QPalette.ColorRole.ToolTipText, theme.text),
    ):
        palette.setColor(role, QColor(colour))
    app.setPalette(palette)
    target = 24 if compact else 32
    app.setStyleSheet(f"""
        QWidget {{ font-size: 13px; }}
        QMainWindow, QDialog {{ background: {theme.panel}; }}
        QToolBar {{ spacing: 4px; padding: 4px; border-bottom: 1px solid {theme.border}; }}
        QToolButton, QPushButton {{ min-height: {target}px; padding: 2px 12px;
            border: 1px solid {theme.border}; border-radius: 5px; background: {theme.raised}; }}
        QPushButton#primary {{ background: {theme.accent}; color: {theme.selected_text}; }}
        QToolButton:hover, QPushButton:hover {{ border-color: {theme.accent}; }}
        QToolButton:disabled, QPushButton:disabled {{ color: {theme.muted}; }}
        QLineEdit, QComboBox, QKeySequenceEdit {{ min-height: {target}px; padding: 2px 8px;
            border: 1px solid {theme.border}; border-radius: 4px; background: {theme.canvas}; }}
        QTreeWidget, QTableWidget, QListWidget, QPlainTextEdit {{ border: 0;
            background: {theme.canvas}; selection-background-color: {theme.accent};
            selection-color: {theme.selected_text}; }}
        QTreeWidget::item, QListWidget::item {{ min-height: {target}px; padding: 2px 4px; }}
        QHeaderView::section {{ padding: 8px; background: {theme.raised}; border: 0;
            border-bottom: 1px solid {theme.border}; }}
        QDockWidget::title {{ padding: 6px; background: {theme.raised}; }}
        QStatusBar {{ border-top: 1px solid {theme.border}; padding: 4px; }}
        QLabel#eyebrow {{ color: {theme.accent}; font-weight: 600; letter-spacing: 2px; }}
        QLabel#title {{ font-size: 27px; font-weight: 600; }}
        QLabel#muted {{ color: {theme.muted}; }}
        QFrame#card {{ background: {theme.panel}; border: 1px solid {theme.border};
            border-radius: 8px; }}
        QLineEdit:focus, QComboBox:focus, QPushButton:focus, QToolButton:focus,
        QTreeWidget:focus, QTableWidget:focus, QListWidget:focus, QKeySequenceEdit:focus {{
            border: 2px solid {theme.accent}; }}
    """)
