"""End-to-end acceptance test for DW5 Draw-to-Export milestone.

Verifies the complete workflow:
1. Flowsheet construction (add units, connect streams, configure inputs)
2. Incomplete case validation gate
3. Successful validation and supervised solver run
4. Process workbook inspection (streams, equipment metrics, mass/energy balance closure)
5. PFD canvas live result overlays and visibility toggling
6. 2D profile plotting, non-modal floating comparison window, and pinning
7. Vector SVG and CSV export with full audit provenance headers
8. Staleness tracking on flowsheet edits and last-valid result preservation
9. Multi-case tab isolation and persistent floating graph comparison
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QLineEdit

from bh_sim.adapters.desktop_preview import create_supervised_gateway
from bh_sim.boundary import contracts as c
from bh_sim.uix.workspace import WorkspaceSettings
from bh_sim.uix.workstation_editor import WorkstationEditor


@pytest.fixture
def studio(tmp_path: Path) -> Iterator[WorkstationEditor]:
    app = QApplication.instance() or QApplication([])
    gateway = create_supervised_gateway(tmp_path)
    settings = WorkspaceSettings(tmp_path / "ui.ini")
    window = WorkstationEditor(gateway, settings)
    window.show()
    app.processEvents()
    assert window.create_draft("DW5 Acceptance Case")
    yield window
    window.close()
    app.processEvents()


def test_dw5_complete_draw_to_export_workflow(studio: WorkstationEditor) -> None:
    app = QApplication.instance()
    assert app is not None

    # 1. Flowsheet construction
    studio.run_command("add source")
    studio.run_command("add heater")
    studio.run_command("add sink")
    assert studio.document is not None
    assert len(studio.document.objects) == 3

    studio.run_command("connect Source-001 out-0 Heater-001 in-0")
    studio.run_command("connect Heater-001 out-0 Sink-001 in-0")
    assert len(studio.document.draft.connections) == 2

    # 2. Incomplete case check: cannot run without required inputs
    can_run_early = studio.run_current()
    assert not can_run_early, "Solver run must be gated behind complete inputs and valid receipt"

    # 3. Configure valid engineering inputs
    studio.run_command("set Source-001 massFlow 12.5 kg/s")
    studio.run_command("set Source-001 temperature 360 K")
    studio.run_command("set Source-001 pressure 250000 Pa")
    studio.run_command("set Heater-001 duty 75000 W")

    # 4. Validate and Run
    assert studio.validate_current(), (
        "Validation must succeed for fully configured heater flowsheet"
    )
    assert studio.run_current(), "Supervised solver run must execute and converge"
    assert studio.last_run_view is not None
    assert studio.last_run_view.convergence == "CONVERGED"

    # 5. Inspect Process Workbook
    wb = studio.workbook_view.workbook
    assert wb is not None, "Workbook must be populated on run completion"
    assert wb.run_id == studio.last_run_view.run_id
    assert wb.convergence == "CONVERGED"
    assert wb.closure == "PASSED"
    assert wb.physical_validity in ("VALID", "EXTRAPOLATED")

    # Verify Streams tab
    assert len(wb.streams) == 2
    inlet = wb.streams[0]
    outlet = wb.streams[1]
    assert (
        inlet.mass_flow_kg_s is not None and pytest.approx(inlet.mass_flow_kg_s, abs=1e-3) == 12.5
    )
    assert inlet.temperature_k is not None and pytest.approx(inlet.temperature_k, abs=1e-2) == 360.0
    assert outlet.temperature_k is not None and outlet.temperature_k > inlet.temperature_k

    # Verify Process Balances closure (First Law: Mass & Energy residuals within tolerance)
    assert len(wb.balances) >= 2
    mass_bal = next(b for b in wb.balances if b.balance_type == "MASS")
    energy_bal = next(b for b in wb.balances if b.balance_type == "ENERGY")
    assert mass_bal.status == "PASSED"
    assert abs(mass_bal.residual) <= mass_bal.tolerance
    assert energy_bal.status == "PASSED"
    assert abs(energy_bal.residual) <= energy_bal.tolerance

    # 6. Canvas Overlays
    assert studio.canvas.show_overlays is True
    assert studio.canvas.overlays is not None
    assert len(studio.canvas.overlays.streams) == 2
    assert len(studio.canvas.overlays.equipment) >= 1

    # Toggle overlays off and on
    studio.toggle_canvas_overlays()
    assert studio.canvas.show_overlays is False
    studio.toggle_canvas_overlays()
    assert studio.canvas.show_overlays is True

    # 7. Plotting and Floating Graph Window
    heater_node = next(e for e in studio.document.draft.equipment if e.model_id == "heater")
    studio.plot_object(heater_node.object_id)
    plot_def = studio.graph_viewer.plot_canvas.plot_def
    assert plot_def is not None, "Plot definition must be loaded for heater"
    assert len(plot_def.series) >= 1

    # Open in non-modal floating comparison window
    floating_dialog = studio.open_graph_window()
    assert floating_dialog is not None
    assert floating_dialog.isVisible()
    assert floating_dialog.viewer.pinned_btn.isChecked()

    # 8. Export to CSV and SVG
    with tempfile.TemporaryDirectory() as export_dir:
        csv_export_file = Path(export_dir) / "heater_profile.csv"
        svg_export_file = Path(export_dir) / "heater_profile.svg"

        studio.graph_viewer.plot_canvas.export_csv(str(csv_export_file))
        studio.graph_viewer.plot_canvas.export_svg(str(svg_export_file))

        assert csv_export_file.exists()
        csv_text = csv_export_file.read_text(encoding="utf-8")
        assert f"# Run ID: {studio.last_run_view.run_id}" in csv_text
        assert "# Plot Title:" in csv_text

        assert svg_export_file.exists()
        svg_text = svg_export_file.read_text(encoding="utf-8")
        assert "<svg" in svg_text
        assert f"<!-- Run ID: {studio.last_run_view.run_id} -->" in svg_text

    # 9. Flowsheet modification and Staleness tracking
    studio.run_command("set Heater-001 duty 80000 W")
    studio.refresh()
    assert studio.dirty is True
    assert "Stale" in studio.workbook_view.stale_label.text()
    # Preserves previous last valid run view
    assert studio.last_run_view is not None

    # 10. Multi-case isolation: create second draft
    assert studio.create_draft("Process Model B")
    assert studio.active_id == "Process Model B"
    # New session starts clean without un-run workbook
    assert studio.workbook_view.workbook is None

    # Floating window from Case A remains open and pinned!
    assert floating_dialog.isVisible()
    assert floating_dialog.viewer.plot_canvas.plot_def is not None
    assert floating_dialog.viewer.plot_canvas.plot_def.plot_id == plot_def.plot_id

    floating_dialog.close()


def _setup_valid_heater_flowsheet(studio: WorkstationEditor) -> None:
    studio.run_command("add source")
    studio.run_command("add heater")
    studio.run_command("add sink")
    studio.run_command("connect Source-001 out-0 Heater-001 in-0")
    studio.run_command("connect Heater-001 out-0 Sink-001 in-0")
    studio.run_command("set Source-001 massFlow 12.5 kg/s")
    studio.run_command("set Source-001 temperature 360 K")
    studio.run_command("set Source-001 pressure 250000 Pa")
    studio.run_command("set Heater-001 duty 75000 W")


def test_tab_switch_during_solve_routes_to_originating_case(studio: WorkstationEditor) -> None:
    _setup_valid_heater_flowsheet(studio)
    assert studio.validate_current()
    assert studio.has_valid_receipt()

    # Create second case tab
    assert studio.create_draft("Case B")
    assert studio.active_id == "Case B"

    # Switch back to Case A
    case_a_index = -1
    case_b_index = -1
    for i in range(studio.case_tabs.count()):
        if studio.case_tabs.tabData(i) == "DW5 Acceptance Case":
            case_a_index = i
        elif studio.case_tabs.tabData(i) == "Case B":
            case_b_index = i
    assert case_a_index != -1 and case_b_index != -1
    studio.switch_tab(case_a_index)
    assert studio.active_id == "DW5 Acceptance Case"

    real_dispatch = studio.gateway.dispatch

    def dispatch_hook(request: c.CommandRequest) -> c.CommandOutcome:
        if request.command_name == "run.start":
            QTimer.singleShot(0, studio, lambda: studio.switch_tab(case_b_index))
        return real_dispatch(request)

    studio.gateway.dispatch = dispatch_hook

    # Execute run
    assert studio.run_current()

    # The active tab was switched to Case B during solving
    assert studio.active_id == "Case B"
    # Case B's canvas and workbook are NOT polluted
    assert studio.workbook_view.workbook is None
    assert studio.canvas.overlays is None
    assert studio.last_run_view is None

    # Switch back to Case A
    studio.switch_tab(case_a_index)
    assert studio.active_id == "DW5 Acceptance Case"
    assert studio.last_run_view is not None
    assert studio.last_run_view.convergence == "CONVERGED"
    assert studio.workbook_view.workbook is not None
    assert studio.canvas.overlays is not None


def test_scientific_failure_retains_last_valid_canvas_overlays(
    studio: WorkstationEditor,
) -> None:
    _setup_valid_heater_flowsheet(studio)
    assert studio.validate_current()
    assert studio.run_current()

    # Verify first valid run populated canvas overlays
    assert studio.canvas.overlays is not None
    valid_overlays = studio.canvas.overlays
    assert studio.session is not None
    assert studio.session.last_valid_overlays == valid_overlays

    # Validate again to obtain receipt for second run
    assert studio.validate_current()

    # Intercept gateway.dispatch to return a run with physical validity deficit
    real_dispatch = studio.gateway.dispatch

    def dispatch_with_deficit(request: c.CommandRequest) -> c.CommandOutcome:
        outcome = real_dispatch(request)
        if request.command_name == "run.start" and outcome.disposition == "COMPLETED":
            run_view = outcome.data
            assert isinstance(run_view, c.RunViewDto)
            invalid_run_view = replace(run_view, physical_validity="INVALID")
            return replace(outcome, data=invalid_run_view)
        return outcome

    studio.gateway.dispatch = dispatch_with_deficit

    # Execute second run with deficit
    assert studio.run_current()
    assert studio.last_run_view is not None
    assert studio.last_run_view.physical_validity == "INVALID"

    # Canvas MUST retain the previous valid overlays
    assert studio.canvas.overlays is not None
    assert studio.canvas.overlays == valid_overlays
    assert studio.session.overlays == valid_overlays

    # Status banner must announce retention of last valid overlays
    assert "Retaining last valid flowsheet overlays" in studio.scientific_status.text()
    assert "invalid" in studio.scientific_status.text()


def test_parameter_edit_invalidates_receipt_and_disables_run(
    studio: WorkstationEditor,
) -> None:
    _setup_valid_heater_flowsheet(studio)
    assert studio.validate_current()
    assert studio.has_valid_receipt()
    assert studio.action_registry.actions["run.start"].isEnabled()

    # Inspect Source unit
    assert studio.document is not None
    source_node = next(e for e in studio.document.draft.equipment if e.model_id == "source")
    studio.inspect_ids((source_node.object_id,))
    line_edits = studio.input_panel.findChildren(QLineEdit)
    assert line_edits

    # 1. Simulate user typing in input field
    target_field = line_edits[0]
    target_field.setText("9999.0")
    target_field.textEdited.emit("9999.0")

    # Immediate invalidation
    assert not studio.has_valid_receipt()
    assert not studio.action_registry.actions["run.start"].isEnabled()
    assert not studio.run_current()

    # 2. Re-apply valid flowsheet parameter and re-validate
    target_field.setModified(False)
    studio.run_command("set Source-001 massFlow 12.5 kg/s")
    assert studio.validate_current()
    assert studio.has_valid_receipt()
    assert studio.action_registry.actions["run.start"].isEnabled()

    # 3. Test schedule_input_edit invalidation
    studio.schedule_input_edit(c.ConfigureInputEdit("Source-001", "massFlow", "20.0", "kg/s"))
    assert not studio.has_valid_receipt()
    assert not studio.run_current()


def test_saved_engineering_edit_stays_stale_and_undo_restores_source(
    studio: WorkstationEditor,
) -> None:
    _setup_valid_heater_flowsheet(studio)
    assert studio.validate_current() and studio.run_current()
    assert "Stale" not in studio.workbook_view.stale_label.text()
    studio.run_command("set Heater-001 duty 125000 W")
    assert studio.save_current() and not studio.dirty
    assert "Stale" in studio.workbook_view.stale_label.text()
    assert "Stale" in studio.scientific_status.text()
    assert studio.canvas.overlays and studio.canvas.overlays.selection.is_stale
    studio.undo()
    assert "Stale" not in studio.workbook_view.stale_label.text()
    studio.redo()
    assert "Stale" in studio.workbook_view.stale_label.text()
    studio.undo()
    assert studio.document is not None
    heater = next(e for e in studio.document.draft.equipment if e.model_id == "heater")
    studio.apply_edit(c.MoveObjectsEdit(((heater.object_id, c.CanvasPointDto(600.0, 300.0)),)))
    assert "Stale" not in studio.workbook_view.stale_label.text()
