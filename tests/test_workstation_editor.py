"""DW3.2 widget contracts: local history, independent tabs and shared commands."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
from PySide6.QtCore import Qt
from PySide6.QtGui import QTransform
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox

from bh_sim.adapters.desktop_preview import create_preview_gateway
from bh_sim.boundary import contracts as c
from bh_sim.uix.workspace import WorkspaceSettings
from bh_sim.uix.workstation_editor import WorkstationEditor


@pytest.fixture
def studio(tmp_path: Path) -> Iterator[WorkstationEditor]:
    app = QApplication.instance() or QApplication([])
    window = WorkstationEditor(
        create_preview_gateway(tmp_path), WorkspaceSettings(tmp_path / "ui.ini")
    )
    window.show()
    app.processEvents()
    assert window.create_draft("Design A")
    yield window
    window.close()
    app.processEvents()


def test_native_surface_canvas_and_ribbon_use_shared_actions(studio: WorkstationEditor) -> None:
    QApplication.processEvents()
    assert studio.canvas.height() > studio.height() / 2
    assert not studio.activity_dock.isVisible()
    assert studio.tools_bar.isVisible() and not studio.ribbon.isVisible()
    studio.set_ribbon(True)
    assert studio.ribbon.isVisible() and not studio.tools_bar.isVisible()
    assert not studio.action_registry.actions["run.start"].isEnabled()
    studio.run_command("add source")
    assert studio.document and len(studio.document.objects) == 1
    QApplication.processEvents()
    studio.fit_flowsheet()
    assert 0.25 < studio.canvas.transform().m11() <= 4.0
    studio.run_command("undo")
    assert len(studio.document.objects) == 0


def test_tabs_preserve_view_selection_history_without_save(studio: WorkstationEditor) -> None:
    studio.run_command("add source")
    assert studio.document and studio.session
    identifier = studio.document.objects[0].object_id
    studio.canvas.select_ids((identifier,))
    studio.canvas.setTransform(QTransform.fromScale(1.4, 1.4))
    studio.canvas.centerOn(220, 80)
    initial = studio.session.state
    assert studio.create_draft("Design B")
    studio.run_command("add sink")
    second = studio.document
    assert studio.open_draft("Design A")
    assert studio.document == initial.document
    assert studio.session.state == initial
    assert studio.canvas.selected_ids() == (identifier,)
    assert studio.canvas.transform().m11() == pytest.approx(1.4)
    studio.undo()
    assert not studio.document.objects
    studio.open_draft("Design B")
    assert studio.document == second


def test_restart_recovers_unsaved_document_and_undo(
    studio: WorkstationEditor, tmp_path: Path
) -> None:
    studio.run_command("add source")
    studio.run_command("set Source-001 pressure 1.000 bar")
    assert studio.document
    before = studio.document
    studio.close()
    restored = WorkstationEditor(
        create_preview_gateway(tmp_path), WorkspaceSettings(tmp_path / "ui.ini")
    )
    assert restored.document == before and restored.dirty
    restored.undo()
    assert restored.document and not restored.document.draft.equipment[0].parameters
    restored.redo()
    assert restored.document == before
    restored.close()


def test_snapshot_preview_is_read_only_and_current_is_retained(studio: WorkstationEditor) -> None:
    studio.run_command("add source")
    assert studio.snapshot_named("Baseline")
    assert studio.session
    baseline = studio.session.state.entries[-1].entry_id
    studio.run_command("add sink")
    current = studio.document
    studio.preview_entry(baseline)
    assert studio.document and len(studio.document.objects) == 1
    assert not studio.canvas.isInteractive()
    assert not studio.action_registry.actions["draft.save"].isEnabled()
    assert not studio.apply_edit(c.AddEquipmentEdit("source", c.CanvasPointDto(0.0, 0.0)))
    studio.return_current()
    assert studio.document == current and studio.canvas.isInteractive()


def test_highlight_isolation_and_navigation_do_not_enter_history(studio: WorkstationEditor) -> None:
    studio.run_command("add source")
    studio.run_command("add sink")
    studio.run_command("connect Source-001 out-0 Sink-001 in-0")
    assert studio.document and studio.session
    stream = studio.document.draft.connections[0].object_id
    group = c.VisualStreamGroup("visual:test", "Circuit", (stream,))
    assert studio.apply_edit(c.UpsertVisualStreamGroupEdit(group))
    before = studio.session.state
    category = studio.layers_tree.topLevelItem(1)
    assert category
    item = category.child(0)
    assert item
    studio.layer_item_clicked(item, 0)
    assert studio.session.state == before
    assert studio.canvas.selected_ids() == ()
    assert studio.canvas.stream_halos[stream].isVisible()
    studio.isolate_visual_group()
    studio.isolate_visual_group()
    studio.canvas.centerOn(500, 500)
    assert studio.session.state == before


def test_command_entry_completion_units_and_delete_confirmation(
    studio: WorkstationEditor, monkeypatch: pytest.MonkeyPatch
) -> None:
    studio.run_command("add source")
    studio.run_command("add sink")
    studio.run_command("connect Source-001 out-0 Sink-001 in-0")
    assert "set Source-001 pressure" in studio.complete_command("set Source-001 pr")
    assert "select Source-001" in studio.complete_command("select Sou")
    before = studio.document
    assert "rejected" in studio.run_command("set Source-001 pressure 5 kg")
    assert studio.document == before
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.No)
    studio.run_command("delete Source-001")
    assert studio.document == before
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
    studio.run_command("delete Source-001")
    assert studio.document and len(studio.document.objects) == 1
    assert "rejected" in studio.run_command("__import__('os').system('echo bad')")
    studio.console.input.setText("help")
    QTest.keyClick(studio.console.input, Qt.Key.Key_Return)
    assert "set <tag>" in studio.console.output.toPlainText()


def test_workspace_template_atomicity_and_case_separation(studio: WorkstationEditor) -> None:
    assert studio.session
    history = studio.session.state
    template = studio.workspace.export_template(studio, "Light", True, {}, True)
    assert studio.apply_workspace_template(template)
    assert studio.theme == "Light" and studio.compact and studio.workspace.ribbon()
    assert studio.session.state == history
    before = studio.saveState()
    assert not studio.apply_workspace_template(
        template.replace("bh-workspace-template-v1", "invalid")
    )
    assert studio.saveState() == before and studio.theme == "Light"


def test_structural_compare_displays_engineering_and_presentation(
    studio: WorkstationEditor,
) -> None:
    studio.run_command("add source")
    assert studio.save_current()
    studio.run_command("set Source-001 pressure 1 bar")
    studio.run_command("rename Source-001 Feed")
    assert studio.save_current()
    studio.show_compare()
    assert studio.compare_before.count() == 2
    studio.compare_versions()
    categories = set()
    labelled_quantity = False
    for i in range(studio.comparison.topLevelItemCount()):
        item = studio.comparison.topLevelItem(i)
        assert item is not None
        categories.add(item.text(0))
        assert "unit:" not in item.text(1)
        labelled_quantity |= item.text(1) == "Feed › pressure" and (item.text(3) == "1.0 bar")
    assert categories == {"engineering", "presentation"}
    assert labelled_quantity


def test_keyboard_undo_and_readable_status(studio: WorkstationEditor) -> None:
    studio.run_command("add source")
    studio.activateWindow()
    studio.canvas.setFocus()
    QApplication.processEvents()
    studio.action_registry.actions["pfd.undo"].trigger()
    assert studio.document and not studio.document.objects
    assert "Recovered locally" in studio.save_status.text()
    assert "Convergence" in studio.scientific_status.text()


def test_reopen_closed_tab_preserves_personal_view(studio: WorkstationEditor) -> None:
    studio.run_command("add source")
    assert studio.document
    identifier = studio.document.objects[0].object_id
    studio.canvas.select_ids((identifier,))
    studio.canvas.setTransform(QTransform.fromScale(1.7, 1.7))
    studio.close_draft()
    assert studio.open_draft("Design A")
    assert studio.canvas.selected_ids() == (identifier,)
    assert studio.canvas.transform().m11() == pytest.approx(1.7)


def test_snapshot_alternative_keeps_prior_path(
    studio: WorkstationEditor, monkeypatch: pytest.MonkeyPatch
) -> None:
    from PySide6.QtWidgets import QInputDialog

    studio.run_command("add source")
    assert studio.snapshot_named("Baseline") and studio.session
    source = studio.session.state
    studio.run_command("add sink")
    studio.preview_entry(source.entries[-1].entry_id)
    monkeypatch.setattr(QInputDialog, "getText", lambda *args: ("Alternative", True))
    studio.branch_selected()
    assert studio.document == source.document
    assert studio.session.state.entries[-1].branch.name == "Alternative"
    assert any(entry.label == "Add Equipment" for entry in studio.session.state.entries)
    assert not studio.session.preview


def test_theme_density_and_reduced_motion_remain_presentation(studio: WorkstationEditor) -> None:
    from dataclasses import replace

    studio.run_command("add source")
    assert studio.session and studio.document
    state = studio.session.state
    for theme in ("Light", "Dark", "High contrast"):
        studio.set_theme(theme)
        assert studio.session.state == state
    assert studio.apply_edit(
        c.SetPfdLayerPreferencesEdit(
            replace(studio.document.layer_preferences, reduced_motion=True)
        )
    )
    assert studio.session.state.entries[-1].classification == "presentation"
    assert not studio.canvas.animation_timer.isActive()
    assert studio.bottom_bar.isVisible()


def test_save_and_tab_switch_flush_original_case_inputs(studio: WorkstationEditor) -> None:
    from bh_sim.uix.pfd_editor import QuantityInput

    studio.run_command("add source")
    assert studio.document
    identifier = studio.document.objects[0].object_id
    studio.canvas.select_ids((identifier,))
    studio.activateWindow()
    QApplication.processEvents()
    field = next(
        f
        for f in studio.input_panel.findChildren(QuantityInput)
        if f.accessibleName() == "Pressure value"
    )
    field.setFocus()
    QTest.keyClicks(field, "2.5")
    studio.action_registry.actions["draft.save"].trigger()
    assert studio.document.draft.equipment[0].parameters[0].quantity.value == 2.5
    assert not studio.dirty
    assert studio.action_registry.actions["draft.save"].isEnabled()
    studio.canvas.select_ids((identifier,))
    field = next(
        f
        for f in studio.input_panel.findChildren(QuantityInput)
        if f.accessibleName() == "Pressure value"
    )
    field.setFocus()
    field.selectAll()
    QTest.keyClicks(field, "3.5")
    assert studio.create_draft("Input isolation")
    QApplication.processEvents()
    assert not studio.document.objects
    assert (
        studio.sessions["Design A"].state.document.draft.equipment[0].parameters[0].quantity.value
        == 3.5
    )
