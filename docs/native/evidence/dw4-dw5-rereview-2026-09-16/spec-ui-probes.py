"""Read-only UI review probes; all generated application data is temporary.

Run with candidate/src on PYTHONPATH and QT_QPA_PLATFORM=offscreen.
The delayed-run probes wrap the real in-process engine to expose UI interleavings.
"""

import json
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QLineEdit

from bh_sim.adapters.desktop_preview import create_supervised_gateway
from bh_sim.uix.workspace import WorkspaceSettings
from bh_sim.uix.workstation_editor import WorkstationEditor


def record(label, **data):
    print(json.dumps({"probe": label, **data}, default=str), flush=True)


def make_window(root):
    gateway = create_supervised_gateway(root)
    window = WorkstationEditor(gateway, WorkspaceSettings(root / "ui.ini"))
    window.show()
    assert window.create_draft("A")
    commands = [
        "add source", "add heater", "add sink",
        "connect Source-001 out-0 Heater-001 in-0",
        "connect Heater-001 out-0 Sink-001 in-0",
        "set Source-001 massFlow 12.5 kg/s",
        "set Source-001 temperature 360 K",
        "set Source-001 pressure 250000 Pa",
        "set Heater-001 duty 75000 W",
    ]
    for command in commands:
        window.run_command(command)
    return window, gateway


app = QApplication([])
with tempfile.TemporaryDirectory(prefix="bh-spec-edit-") as temp:
    window, gateway = make_window(Path(temp))
    record("explicit_validation", before=window.last_receipt,
           run_enabled=window.action_registry.actions["run.start"].isEnabled(),
           run_return=window.run_current(), after=window.last_receipt)
    assert window.validate_current()
    receipt_id = window.last_receipt.receipt_id
    window.run_command("set Heater-001 duty 80000 W")
    record("stale_receipt", same_receipt=window.last_receipt.receipt_id == receipt_id,
           run_enabled=window.action_registry.actions["run.start"].isEnabled())
    window.run_command("select Heater-001")
    field = next(f for f in window.input_panel.findChildren(QLineEdit)
                 if f.accessibleName() == "Heat duty value")
    field.setText("125000")
    field.setModified(True)
    validated = window.validate_current()
    heater = next(u for u in window.current.equipment if u.model_id == "heater")
    record("flush_inspector", validated=validated, duty=heater.parameters[0].quantity.value)
    window.close()

with tempfile.TemporaryDirectory(prefix="bh-spec-async-") as temp:
    window, gateway = make_window(Path(temp))
    assert window.validate_current()
    window.create_draft("B")
    window.switch_tab(0)
    assert window.active_id == "A"
    assert window.validate_current()
    original = gateway.services.engineering.run
    timeline = []

    def slow(*args, **kwargs):
        timeline.append(("start", time.monotonic()))
        time.sleep(0.4)
        result = original(*args, **kwargs)
        timeline.append(("finish", time.monotonic()))
        return result

    gateway.services.engineering.run = slow

    def switch():
        timeline.append(("switch_begin", time.monotonic()))
        window.switch_tab(1)
        timeline.append(("switch_end", time.monotonic()))

    QTimer.singleShot(50, switch)
    succeeded = window.run_current()
    start = timeline[0][1]
    record("case_switch", succeeded=succeeded, active=window.active_id,
           displayed_run_case=window.last_run_view.case_id,
           b_stored_case=window.sessions["B"].last_run_view.case_id,
           b_workbook_case=window.sessions["B"].workbook.case_id,
           timeline=[(label, round(moment-start, 3)) for label, moment in timeline])

    window.switch_tab(0)
    assert window.validate_current()
    timeline.clear()

    def cancel():
        timeline.append(("cancel_begin", time.monotonic()))
        returned = window.cancel_current_run()
        timeline.append(("cancel_end", time.monotonic()))
        record("cancel_request", returned=returned)

    QTimer.singleShot(50, cancel)
    succeeded = window.run_current()
    start = timeline[0][1]
    record("cancel", run_succeeded=succeeded,
           attempts=[attempt.state for attempt in gateway.services.list_attempts("A")],
           timeline=[(label, round(moment-start, 3)) for label, moment in timeline])
    window.close()

with tempfile.TemporaryDirectory(prefix="bh-spec-lastvalid-") as temp:
    window, gateway = make_window(Path(temp))
    assert window.validate_current()
    assert window.run_current()
    good_run = window.last_run_view.run_id
    window.run_command("set Source-001 temperature 50 K")
    validated = window.validate_current()
    returned = window.run_current() if validated else False
    last_valid = gateway.services.last_valid_run("case:A")
    record("last_valid", validated=validated, run_return=returned,
           good_run=good_run, latest_status=window.last_run_view.convergence,
           selected_overlay_run=window.canvas.overlays.run_id,
           selected_workbook_run=window.session.workbook.run_id,
           repository_last_valid_run=last_valid.run_id if last_valid else None,
           available_last_valid_actions=[name for name in window.action_registry.actions
                                         if "last_valid" in name])
    window.close()
