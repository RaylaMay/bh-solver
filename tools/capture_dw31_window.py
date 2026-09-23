"""Capture the complete DW3.1 native window with presentation-only fixture data."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from bh_sim.adapters.desktop_preview import create_preview_gateway
from bh_sim.boundary import contracts as c
from bh_sim.uix.pfd_editor import PfdEditorWindow
from bh_sim.uix.workspace import WorkspaceSettings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(tempfile.mkdtemp(prefix="bh-dw31-window-"))
    app = QApplication([])
    window = PfdEditorWindow(create_preview_gateway(root), WorkspaceSettings(root / "ui.ini"))
    assert window.create_draft("DW3.1 visual fixture")
    for model, point in (
        ("source", c.CanvasPointDto(0.0, 0.0)),
        ("heater", c.CanvasPointDto(230.0, 0.0)),
        ("sink", c.CanvasPointDto(460.0, 0.0)),
    ):
        assert window.apply_edit(c.AddEquipmentEdit(model, point))
    assert window.document is not None
    nodes = window.document.draft.equipment
    assert window.apply_edit(
        c.ConnectPortsEdit(nodes[0].object_id, "out-0", nodes[1].object_id, "in-0")
    )
    assert window.apply_edit(
        c.ConnectPortsEdit(nodes[1].object_id, "out-0", nodes[2].object_id, "in-0")
    )
    streams = tuple(stream.object_id for stream in window.document.draft.connections)
    group = c.VisualStreamGroup("visual:fixture", "Main process path", streams, "#FFD166")
    assert window.apply_edit(c.UpsertVisualStreamGroupEdit(group))
    assert window.apply_edit(
        c.SetPfdLayerPreferencesEdit(c.PfdLayerPreferences(active_visual_group_id=group.group_id))
    )
    window.layers_dock.show()
    window.layers_dock.raise_()
    window.resize(1440, 900)
    window.show()

    def capture() -> None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        assert window.grab().save(str(args.output))
        print(f"Captured {args.output}")
        window.dirty = False
        window.close()
        app.quit()

    QTimer.singleShot(750, capture)
    QTimer.singleShot(10000, lambda: app.exit(2))
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
