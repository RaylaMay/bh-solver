"""Capture DW3.2 on native Qt with isolated, incomplete reference-fixture inputs."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from bh_sim.adapters.desktop_preview import create_preview_gateway
from bh_sim.boundary import contracts as c
from bh_sim.uix.workspace import WorkspaceSettings
from bh_sim.uix.workstation_editor import WorkstationEditor


def main() -> None:
    """Save layout evidence; no user cases, application settings or solver calls."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    app = QApplication([])
    app.setStyle("Fusion")
    root = Path(tempfile.mkdtemp(prefix="bh-dw32-capture-"))
    window = WorkstationEditor(create_preview_gateway(root), WorkspaceSettings(root / "ui.ini"))
    window.resize(1440, 900)
    window.show()
    assert window.create_draft("Cooling loop")
    for model, x in (("source", 0.0), ("heater", 230.0), ("sink", 460.0)):
        assert window.apply_edit(c.AddEquipmentEdit(model, c.CanvasPointDto(x, 0.0)))
    assert window.document
    a, b, end = [n.object_id for n in window.document.draft.equipment]
    assert window.apply_edit(c.ConnectPortsEdit(a, "out-0", b, "in-0"))
    assert window.apply_edit(c.ConnectPortsEdit(b, "out-0", end, "in-0"))
    assert window.apply_edit(c.ConfigureInputEdit(b, "duty", "5.0", "kW"))
    assert window.save_current()
    assert window.snapshot_named("Design review baseline")
    assert window.apply_edit(c.ConfigureInputEdit(b, "duty", "8.0", "kW"))
    assert window.save_current()
    assert window.create_draft("Alternative A")
    assert window.open_draft("Cooling loop")
    window.canvas.select_ids((b,))

    def capture() -> None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        window.grab().save(str(args.output))
        window.set_ribbon(True)
        QTimer.singleShot(250, ribbon_capture)

    def ribbon_capture() -> None:
        window.grab().save(str(args.output.with_name("ribbon.png")))
        window.set_ribbon(False)
        window.apply_preset("Compare")
        window.compare_versions()
        QTimer.singleShot(250, compare_capture)

    def compare_capture() -> None:
        window.grab().save(str(args.output.with_name("compare.png")))
        window.close()
        print("Captured native design, ribbon and compare layouts", flush=True)
        app.quit()

    # Native dock geometry settles after show. Fit against that viewport rather
    # than the temporary construction size, then allow a frame before capture.
    QTimer.singleShot(250, window.fit_flowsheet)
    QTimer.singleShot(500, capture)
    QTimer.singleShot(15000, lambda: app.exit(2))
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
