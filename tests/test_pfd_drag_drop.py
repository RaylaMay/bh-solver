"""Test PFD palette drag-and-drop interactions and preview handling."""

from __future__ import annotations

import json
import os
from typing import cast

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
from PySide6.QtCore import QMimeData, QPoint, Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QKeyEvent
from PySide6.QtWidgets import QApplication

from bh_sim.boundary import contracts as c
from bh_sim.uix.pfd_canvas import PfdCanvas
from bh_sim.uix.pfd_editor import EquipmentPaletteList


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return cast(QApplication, QApplication.instance() or QApplication([]))


@pytest.fixture
def catalogue() -> c.PfdCatalogueDto:
    return c.PfdCatalogueDto(
        (
            c.PfdModelDto("heater", "Duty heater", (), ()),
            c.PfdModelDto("cooler", "Duty cooler", (), ()),
        )
    )


@pytest.fixture
def document() -> c.PfdDocumentDto:
    draft = c.DraftDto(
        "draft-1",
        1,
        None,
        "2026-09-14T00:00:00Z",
        (),
        (),
        c.PresentationDto(()),
    )
    return c.PfdDocumentDto(draft, ())


def test_equipment_palette_populates_items(
    qapp: QApplication, catalogue: c.PfdCatalogueDto
) -> None:
    palette = EquipmentPaletteList(catalogue)
    assert palette.count() == 2
    item0 = palette.item(0)
    assert item0.text() == "Duty heater"
    assert item0.data(Qt.ItemDataRole.UserRole) == "heater"
    item1 = palette.item(1)
    assert item1.text() == "Duty cooler"
    assert item1.data(Qt.ItemDataRole.UserRole) == "cooler"


def test_canvas_drag_enter_and_drop_valid_payload(
    qapp: QApplication, catalogue: c.PfdCatalogueDto, document: c.PfdDocumentDto
) -> None:
    canvas = PfdCanvas()
    canvas.set_document(document, catalogue)

    emitted_edits: list[object] = []
    canvas.edit_requested.connect(emitted_edits.append)

    payload = json.dumps({"model_id": "heater", "title": "Duty heater", "version": "1.0"}).encode(
        "utf-8"
    )
    mime = QMimeData()
    mime.setData("application/vnd.bh.equipment-model+json", payload)

    enter_event = QDragEnterEvent(
        QPoint(100, 100),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.dragEnterEvent(enter_event)
    assert enter_event.isAccepted()
    assert canvas.placement_preview is not None

    drop_event = QDropEvent(
        QPoint(100, 100),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.dropEvent(drop_event)
    assert drop_event.isAccepted()
    assert canvas.placement_preview is None

    assert len(emitted_edits) == 1
    edit = emitted_edits[0]
    assert isinstance(edit, c.AddEquipmentEdit)
    assert edit.model_id == "heater"


def test_canvas_drag_rejects_unknown_model(
    qapp: QApplication, catalogue: c.PfdCatalogueDto, document: c.PfdDocumentDto
) -> None:
    canvas = PfdCanvas()
    canvas.set_document(document, catalogue)

    payload = json.dumps({"model_id": "unknown_reactor", "title": "Reactor"}).encode("utf-8")
    mime = QMimeData()
    mime.setData("application/vnd.bh.equipment-model+json", payload)

    enter_event = QDragEnterEvent(
        QPoint(100, 100),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.dragEnterEvent(enter_event)
    assert not enter_event.isAccepted()
    assert canvas.placement_preview is None


def test_canvas_escape_cleans_preview(
    qapp: QApplication, catalogue: c.PfdCatalogueDto, document: c.PfdDocumentDto
) -> None:
    canvas = PfdCanvas()
    canvas.set_document(document, catalogue)

    payload = json.dumps({"model_id": "heater", "title": "Duty heater"}).encode("utf-8")
    mime = QMimeData()
    mime.setData("application/vnd.bh.equipment-model+json", payload)

    enter_event = QDragEnterEvent(
        QPoint(100, 100),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.dragEnterEvent(enter_event)
    assert canvas.placement_preview is not None

    key_event = QKeyEvent(
        QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier
    )
    canvas.keyPressEvent(key_event)
    assert canvas.placement_preview is None
