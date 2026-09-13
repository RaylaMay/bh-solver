"""Optional native GUI entry point with explicit capability diagnostics.

The composition here intentionally selects DW2 mock engineering ports. It never
imports the scientific composition root. gui-scripts enables windowed launch on
Windows; the repository also supplies a local macOS developer .app wrapper.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> None:
    """Launch the draft workspace; absent Qt is an error, never a browser fallback."""
    parser = argparse.ArgumentParser(description="BH solver native workstation preview")
    parser.add_argument("--data-root", type=Path, help="Local draft and workspace directory")
    args = parser.parse_args()
    if sys.version_info >= (3, 15):
        raise SystemExit("DESKTOP_RUNTIME_UNAVAILABLE: Qt 6.11.2 requires Python below 3.15.")
    try:
        from PySide6.QtCore import QStandardPaths
        from PySide6.QtWidgets import QApplication
    except ImportError as error:
        raise SystemExit(
            "DESKTOP_RUNTIME_UNAVAILABLE: install the optional desktop dependencies "
            "(uv sync --extra desktop)."
        ) from error

    from bh_sim.adapters.desktop_preview import create_preview_gateway
    from bh_sim.uix.window import WorkstationWindow
    from bh_sim.uix.workspace import WorkspaceSettings

    app = QApplication(sys.argv[:1])
    app.setApplicationName("BH solver")
    app.setOrganizationName("BH")
    app.setStyle("Fusion")
    root = args.data_root or Path(
        QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
    )
    window = WorkstationWindow(
        create_preview_gateway(root), WorkspaceSettings(root / "workspace.ini")
    )
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
