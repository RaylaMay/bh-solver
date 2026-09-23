"""Versioned, presentation-only workspace settings; no draft autosave or Run.

Qt's geometry/state bytes are used only for window layout. Corrupt or oversized
settings fall back to the default layout. This is not an engineering artifact.
"""

import json
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QByteArray, QSettings
from PySide6.QtWidgets import QMainWindow

LAYOUT_VERSION = 1
MAX_LAYOUT_BYTES = 65536


class WorkspaceSettings:
    """Store one user's local appearance, docks and shortcut preferences."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.settings = QSettings(str(path), QSettings.Format.IniFormat)

    def actor_id(self) -> str:
        """Use a persistent local identity without exposing the OS account name.

        This is attribution for a local editor, not authenticated collaboration.
        """
        value = str(self.settings.value("identity/actor", ""))
        if not value:
            value = "editor:" + uuid4().hex
            self.settings.setValue("identity/actor", value)
            self.settings.sync()
        return value

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

    def ribbon(self) -> bool:
        """Compact toolbar remains the default; this preference never enters a case."""
        return str(self.settings.value("appearance/ribbon", "false")).lower() == "true"

    def command_history(self) -> list[str]:
        """Recall local text only; restoring preferences never executes commands."""
        try:
            values = json.loads(str(self.settings.value("commands/recall", "[]")))
            if isinstance(values, list) and all(isinstance(v, str) for v in values):
                return [v[:4096] for v in values[-100:]]
        except ValueError:
            pass
        return []

    def export_template(
        self,
        window: QMainWindow,
        theme: str,
        compact: bool,
        shortcuts: dict[str, str],
        ribbon: bool,
    ) -> str:
        """Serialize bounded workspace presentation only, excluding project/command text."""
        return json.dumps(
            {
                "schema": "bh-workspace-template-v1",
                "layout_version": LAYOUT_VERSION,
                "layout": bytes(window.saveState(LAYOUT_VERSION).toBase64().data()).decode("ascii"),
                "theme": theme,
                "compact": compact,
                "ribbon": ribbon,
                "shortcuts": shortcuts,
            },
            sort_keys=True,
            indent=2,
        )

    @staticmethod
    def parse_template(text: str) -> dict:
        """Reject unknown keys and oversized templates before any UI preference changes."""
        import base64

        if len(text.encode()) > 100_000:
            raise ValueError("Workspace template exceeds 100 KB")
        value = json.loads(text)
        keys = {"schema", "layout_version", "layout", "theme", "compact", "ribbon", "shortcuts"}
        if not isinstance(value, dict) or set(value) != keys:
            raise ValueError("Unsupported workspace template fields")
        if (
            value["schema"] != "bh-workspace-template-v1"
            or value["layout_version"] != LAYOUT_VERSION
        ):
            raise ValueError("Unsupported workspace template version")
        if value["theme"] not in {"Dark", "Light", "High contrast"} or any(
            type(value[key]) is not bool for key in ("compact", "ribbon")
        ):
            raise ValueError("Invalid appearance preference")
        if not isinstance(value["shortcuts"], dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in value["shortcuts"].items()
        ):
            raise ValueError("Invalid shortcut mapping")
        data = base64.b64decode(value["layout"], validate=True)
        if not 0 < len(data) <= MAX_LAYOUT_BYTES:
            raise ValueError("Invalid workspace layout size")
        return {**value, "layout": QByteArray(data)}
