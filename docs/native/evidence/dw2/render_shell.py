"""Capture actual DW2 widgets offscreen with temporary, fixture-only draft storage.

Run with the desktop extra installed. Images are visual software evidence, not a
macOS interaction/accessibility witness or a renderer benchmark. No user case,
workspace preference or scientific calculation is read or written by this script.
"""

from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication

from bh_sim.adapters.desktop_preview import create_preview_gateway
from bh_sim.api.schemas import PfdDraftDto
from bh_sim.uix.window import WorkstationWindow
from bh_sim.uix.workspace import WorkspaceSettings

ROOT = Path(__file__).resolve().parents[4]
OUTPUT = Path(__file__).resolve().parent


def main() -> None:
    """Render welcome and read-only fixture inputs in the three shipped themes."""
    app = QApplication([])
    app.setStyle("Fusion")
    with TemporaryDirectory(prefix="bh-dw2-render-") as scratch:
        root = Path(scratch)
        gateway = create_preview_gateway(root)
        window = WorkstationWindow(gateway, WorkspaceSettings(root / "workspace.ini"))
        window.show()
        app.processEvents()
        assert window.grab().save(str(OUTPUT / "shell-welcome.png"))
        # Populate only the temporary repository in the preserved browser format.
        fixture = PfdDraftDto.model_validate_json(
            (ROOT / "tests/fixtures/dw1/baseline.request.json").read_text()
        )
        (root / "drafts/thermal-loop-concept.r000001.json").write_text(
            fixture.model_dump_json(by_alias=True)
        )
        window.refresh_catalog()
        assert window.open_draft(fixture.draft_id)
        for theme, filename in (
            ("Dark", "shell-draft-dark.png"),
            ("Light", "shell-draft-light.png"),
            ("High contrast", "shell-draft-contrast.png"),
        ):
            window.set_theme(theme)
            window.equipment.selectRow(0)
            app.processEvents()
            assert window.grab().save(str(OUTPUT / filename))
        assert window.close()
    print("Rendered four DW2 widget views from temporary fixture storage; no solver invoked")


if __name__ == "__main__":
    main()
