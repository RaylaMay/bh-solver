"""Native widget behavior using Qt offscreen; distinct from witnessed OS interaction."""

from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit, QMessageBox, QToolBar, QToolButton

from bh_sim.adapters.desktop_preview import create_preview_gateway
from bh_sim.boundary import contracts as c
from bh_sim.uix.pfd_editor import PfdEditorWindow, QuantityInput
from bh_sim.uix.pfd_settings import PfdSettingsDialog
from bh_sim.uix.workspace import WorkspaceSettings


@pytest.fixture
def editor(tmp_path: Path) -> Iterator[PfdEditorWindow]:
    app = QApplication.instance() or QApplication([])
    window = PfdEditorWindow(
        create_preview_gateway(tmp_path), WorkspaceSettings(tmp_path / "workspace.ini")
    )
    window.show()
    app.processEvents()
    assert window.create_draft("Widget test")
    yield window
    QApplication.clipboard().clear()
    window.dirty = False
    window.close()
    app.processEvents()


def populate(window: PfdEditorWindow) -> tuple[str, str]:
    for model, x in (("source", 0.0), ("sink", 250.0)):
        assert window.apply_edit(c.AddEquipmentEdit(model, c.CanvasPointDto(x, 0.0)))
    assert window.document is not None
    ids = tuple(n.object_id for n in window.document.draft.equipment)
    return ids[0], ids[1]


def test_port_drag_delete_cancel_undo_and_reopen(
    editor: PfdEditorWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, sink = populate(editor)
    editor.canvas.centerOn(125, 30)
    QApplication.processEvents()
    a = editor.canvas.mapFromScene(editor.canvas.nodes[source].ports["out-0"].scenePos())
    b = editor.canvas.mapFromScene(editor.canvas.nodes[sink].ports["in-0"].scenePos())
    QTest.mousePress(editor.canvas.viewport(), Qt.MouseButton.LeftButton, pos=a)
    QTest.mouseMove(editor.canvas.viewport(), b)
    QTest.mouseRelease(editor.canvas.viewport(), Qt.MouseButton.LeftButton, pos=b)
    assert editor.document is not None and len(editor.document.draft.connections) == 1
    before = editor.document
    editor.canvas.nodes[source].setSelected(True)
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.No)
    editor.delete_selection()
    assert editor.document == before
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
    editor.delete_selection()
    assert len(editor.document.draft.equipment) == 1
    editor.undo()
    assert editor.document == before
    editor.redo()
    assert len(editor.document.draft.equipment) == 1
    editor.undo()
    assert editor.save_current()
    saved = editor.document
    editor.close_draft()
    assert editor.current is None
    assert editor.open_draft("Widget test") and editor.document == saved
    assert not editor.action_registry.actions["run.start"].isEnabled()


def test_move_is_undoable_and_snap_is_presentation_only(editor: PfdEditorWindow) -> None:
    source, _ = populate(editor)
    assert editor.document is not None
    before = editor.document.draft.equipment
    editor.canvas.centerOn(0, 0)
    QApplication.processEvents()
    a = editor.canvas.mapFromScene(editor.canvas.nodes[source].scenePos())
    a += editor.canvas.mapFromScene(35, 25) - editor.canvas.mapFromScene(0, 0)
    b = a + editor.canvas.mapFromScene(39, 39) - editor.canvas.mapFromScene(0, 0)
    QTest.mousePress(editor.canvas.viewport(), Qt.MouseButton.LeftButton, pos=a)
    QTest.mouseMove(editor.canvas.viewport(), b, 20)
    QTest.mouseRelease(editor.canvas.viewport(), Qt.MouseButton.LeftButton, pos=b)
    obj = next(o for o in editor.document.objects if o.object_id == source)
    assert obj.position == c.CanvasPointDto(40.0, 40.0)
    assert editor.document.draft.equipment == before
    editor.undo()
    assert next(
        o for o in editor.document.objects if o.object_id == source
    ).position == c.CanvasPointDto(0.0, 0.0)


def test_noop_focus_and_original_notation(editor: PfdEditorWindow) -> None:
    source, _ = populate(editor)
    assert editor.apply_edit(c.ConfigureInputEdit(source, "pressure", "1.000", "bar"))
    editor.inspect_ids((source,))
    QApplication.processEvents()
    fields = editor.input_panel.findChildren(QuantityInput)
    field = next(f for f in fields if f.accessibleName() == "Pressure value")
    assert field.text() == "100000"
    before = editor.document
    field.setFocus()
    QApplication.processEvents()
    assert field.text() == "1.000"
    editor.canvas.setFocus()
    QApplication.processEvents()
    assert field.text() == "100000" and editor.document == before
    field.setFocus()
    field.selectAll()
    QTest.keyClicks(field, "2.000")
    QTest.keyClick(field, Qt.Key.Key_Tab)
    QApplication.processEvents()
    assert editor.document is not None
    quantity = editor.document.draft.equipment[0].parameters[0].quantity
    assert quantity == c.QuantityDto(2.0, "bar")
    assert (
        next(o for o in editor.document.objects if o.object_id == source).notation[0].text
        == "2.000"
    )


def test_copy_default_has_no_connections(editor: PfdEditorWindow) -> None:
    source, sink = populate(editor)
    editor.apply_edit(c.ConnectPortsEdit(source, "out-0", sink, "in-0"))
    editor.canvas.nodes[source].setSelected(True)
    editor.canvas.nodes[sink].setSelected(True)
    editor.copy_selection()
    editor.paste()
    assert editor.document is not None
    assert len(editor.document.draft.equipment) == 4 and len(editor.document.draft.connections) == 1
    editor.undo()
    editor.paste(connections=True)
    assert len(editor.document.draft.connections) == 2


def test_settings_preview_does_not_apply_on_cancel(editor: PfdEditorWindow) -> None:
    assert editor.document is not None
    before = editor.document
    dialog = PfdSettingsDialog(before.settings, editor)
    expected = replace(
        before.settings,
        crossing="bridge",
        snap_radius=12.0,
        display_precision=4,
        units=(c.UnitPreferenceDto("Pa", "bar"),),
    )
    dialog.populate(expected)
    assert dialog.read() == expected
    dialog.reject()
    assert editor.document == before
    field = dialog.controls["grid_spacing"]
    assert isinstance(field, QLineEdit)
    field.setText("0")
    with pytest.raises(ValueError):
        dialog.read()


def test_zero_delta_wheel_event_does_not_zoom(editor: PfdEditorWindow) -> None:
    from PySide6.QtCore import QPoint, QPointF
    from PySide6.QtGui import QWheelEvent

    before = editor.canvas.transform().m11()
    event = QWheelEvent(
        QPointF(100.0, 100.0),
        QPointF(100.0, 100.0),
        QPoint(),
        QPoint(),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.ScrollEnd,
        False,
    )
    QApplication.sendEvent(editor.canvas.viewport(), event)
    assert editor.canvas.transform().m11() == before


def test_stream_keyboard_selection_and_settings_shortcuts(editor: PfdEditorWindow) -> None:
    source, sink = populate(editor)
    editor.apply_edit(c.ConnectPortsEdit(source, "out-0", sink, "in-0"))
    assert editor.document is not None
    stream = editor.document.draft.connections[0].object_id
    editor.equipment.selectRow(2)
    assert editor.selected_ids() == (stream,)
    assert editor.selection_title.text() == "S-001"
    dialog = PfdSettingsDialog(
        replace(editor.document.settings, shortcuts=(("pfd.connect", "Ctrl+Alt+L"),)), editor
    )
    assert dialog.read().shortcuts == (("pfd.connect", "Ctrl+Alt+L"),)
    assert editor.apply_edit(c.SettingsEdit(dialog.read()))
    assert editor.action_registry.actions["pfd.connect"].shortcut().toString() == "Ctrl+Alt+L"


def test_workspace_switcher_toolbar_and_layers_are_visible(editor: PfdEditorWindow) -> None:
    assert editor.workspace_buttons["flowsheet"].isEnabled()
    assert editor.workspace_buttons["flowsheet"].isChecked()
    assert not editor.workspace_buttons["dynamics"].isEnabled()
    assert "M7" in editor.workspace_buttons["dynamics"].toolTip()
    assert not editor.workspace_buttons["controls"].isEnabled()
    toolbar = next(
        toolbar
        for toolbar in editor.findChildren(QToolBar)
        if toolbar.objectName() == "pfd-editing-toolbar"
    )
    labels = {button.text() for button in toolbar.findChildren(QToolButton)}
    assert {"Select", "Connect", "Rename", "Delete", "Undo", "Redo", "Fit", "100%"} <= labels
    assert {"Groups", "Layers", "Settings"} <= labels


def test_group_click_highlights_without_selecting_members(editor: PfdEditorWindow) -> None:
    source, sink = populate(editor)
    assert editor.apply_edit(c.ConnectPortsEdit(source, "out-0", sink, "in-0"))
    assert editor.document is not None
    stream = editor.document.draft.connections[0].object_id
    group = c.VisualStreamGroup("visual:test", "Test group", (stream,), "#FFD166")
    assert editor.apply_edit(c.UpsertVisualStreamGroupEdit(group))
    editor.canvas.scene_data.clearSelection()
    editor.refresh_layers()
    category = editor.layers_tree.topLevelItem(1)
    assert category is not None
    item = category.child(0)
    assert item is not None
    editor.layers_tree.setCurrentItem(item)
    editor.layer_item_clicked(item, 0)
    assert editor.document.layer_preferences.active_visual_group_id == group.group_id
    assert editor.canvas.selected_ids() == ()
    assert editor.canvas.stream_halos[stream].isVisible()
    editor.select_group_members()
    assert editor.canvas.selected_ids() == (stream,)


def test_animation_states_direction_status_and_reduced_motion(editor: PfdEditorWindow) -> None:
    source, sink = populate(editor)
    assert editor.apply_edit(c.ConnectPortsEdit(source, "out-0", sink, "in-0"))
    assert editor.document is not None
    stream = editor.document.draft.connections[0].object_id
    frame = c.FlowVisualizationFrame(
        "run:fixture",
        12.0,
        (c.FlowStreamVisualization(stream, -2.0, "reverse", "kg/s", "STALE"),),
        "completed-run",
    )
    editor.canvas.set_visualization_frame(frame)
    before = editor.canvas.animation_phase
    editor.canvas.advance_animation()
    assert editor.canvas.animation_phase != before
    assert editor.canvas.flow_markers[stream].isVisible()
    assert editor.canvas.streams[stream].pen().style() == Qt.PenStyle.DashLine
    assert "Stale" in editor.canvas.stream_status_icons[stream].text()
    assert editor.canvas.stream_status_icons[stream].isVisible()
    assert "run:fixture" in editor.layer_legend.text()
    zero = replace(
        frame,
        streams=(c.FlowStreamVisualization(stream, 0.0, "stationary", "kg/s", "VALID"),),
    )
    editor.canvas.set_visualization_frame(zero)
    editor.canvas.advance_animation()
    assert editor.canvas.flow_markers[stream].isVisible()
    preferences = replace(editor.document.layer_preferences, reduced_motion=True)
    assert editor.apply_edit(c.SetPfdLayerPreferencesEdit(preferences))
    editor.canvas.set_visualization_frame(frame)
    assert not editor.canvas.animation_timer.isActive()
