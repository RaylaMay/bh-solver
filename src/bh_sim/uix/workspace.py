"""Versioned, presentation-only workspace settings; no draft autosave or Run.

Qt's geometry/state bytes are used only for window layout. Corrupt or oversized
settings fall back to the default layout. This is not an engineering artifact.
"""

import json
from pathlib import Path

from PySide6.QtCore import QByteArray, QSettings
from PySide6.QtWidgets import QMainWindow

LAYOUT_VERSION = 1
MAX_LAYOUT_BYTES = 65536


class WorkspaceSettings:
    """Store one user's local appearance, docks and shortcut preferences."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.settings = QSettings(str(path), QSettings.Format.IniFormat)

    def appearance(self) -> tuple[str, bool]:
        """Return bounded appearance choices; no external provider or device use."""
        theme = str(self.settings.value("appearance/theme", "Dark"))
        if theme not in {"Dark", "Light", "High contrast"}:
            theme = "Dark"
        return theme, str(self.settings.value("appearance/compact", "false")).lower() == "true"

    def restore(self, window: QMainWindow) -> bool:
        """Restore valid layout bytes; reject unknown layout versions."""
        if str(self.settings.value("layout/version", "")) != str(LAYOUT_VERSION):
            return False
        geometry = self.settings.value("layout/geometry")
        state = self.settings.value("layout/state")
        if not all(
            isinstance(item, QByteArray) and 0 < item.size() <= MAX_LAYOUT_BYTES
            for item in (geometry, state)
        ):
            return False
        assert isinstance(geometry, QByteArray) and isinstance(state, QByteArray)
        previous_geometry = window.geometry()
        previous_window_state = window.windowState()
        previous_state = window.saveState(LAYOUT_VERSION)
        if window.restoreGeometry(geometry) and window.restoreState(state, LAYOUT_VERSION):
            return True
        # A valid geometry with corrupt dock bytes must not apply half a layout.
        window.restoreState(previous_state, LAYOUT_VERSION)
        window.setGeometry(previous_geometry)
        window.setWindowState(previous_window_state)
        return False

    def shortcuts(self) -> dict[str, str]:
        """Read only string-to-string overrides; unknown command IDs are ignored by UIX."""
        try:
            values = json.loads(str(self.settings.value("commands/shortcuts", "{}")))
        except (ValueError, TypeError):
            return {}
        if not isinstance(values, dict) or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in values.items()
        ):
            return {}
        return values

    def save(
        self, window: QMainWindow, theme: str, compact: bool, shortcuts: dict[str, str]
    ) -> bool:
        """Persist layout only; return false when Qt reports a storage failure."""
        for key, value in {
            "layout/version": LAYOUT_VERSION,
            "layout/geometry": window.saveGeometry(),
            "layout/state": window.saveState(LAYOUT_VERSION),
            "appearance/theme": theme,
            "appearance/compact": compact,
            "commands/shortcuts": json.dumps(shortcuts, sort_keys=True),
        }.items():
            self.settings.setValue(key, value)
        self.settings.sync()
        return self.settings.status() == QSettings.Status.NoError
