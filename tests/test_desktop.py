"""DW2 keyboard, persistence and authority checks using Qt's offscreen platform.

These automate widget behavior, not native OS accessibility or renderer benchmarks.
The desktop extra is optional; the suite reports a skip when Qt is unavailable.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtCore import QByteArray, Qt, QTimer
from PySide6.QtGui import QKeySequence
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QInputDialog, QLineEdit, QMessageBox

from bh_sim.adapters.desktop_preview import create_preview_gateway
from bh_sim.application.commands import CommandRegistry
from bh_sim.application.services import ApplicationServices
from bh_sim.boundary.contracts import (
    CommandOutcome,
    CommandRequest,
    CreateDraftParameters,
    DraftDto,
    DraftListDto,
    DraftParameters,
    ListDraftsParameters,
)
from bh_sim.boundary.ports import CommandGateway
from bh_sim.uix.actions import CommandPalette
from bh_sim.uix.window import WorkstationWindow
from bh_sim.uix.workspace import LAYOUT_VERSION, WorkspaceSettings


class RecordingGateway:
    """Record interaction commands while retaining real draft persistence behavior."""

    def __init__(self, delegate: CommandGateway) -> None:
        self.delegate = delegate
        self.calls: list[CommandRequest] = []

    @property
    def command_names(self) -> tuple[str, ...]:
        return self.delegate.command_names

    def dispatch(self, request: CommandRequest) -> CommandOutcome:
        self.calls.append(request)
        return self.delegate.dispatch(request)


@pytest.fixture(scope="module")
def app() -> Iterator[QApplication]:
    instance = QApplication.instance()
    application = instance if isinstance(instance, QApplication) else QApplication([])
    application.setStyle("Fusion")
    yield application


@pytest.fixture
def window(tmp_path: Path, app: QApplication) -> Iterator[WorkstationWindow]:
    gateway = RecordingGateway(create_preview_gateway(tmp_path))
    widget = WorkstationWindow(gateway, WorkspaceSettings(tmp_path / "workspace.ini"))
    widget.show()
    widget.activateWindow()
    app.processEvents()
    yield widget
    widget.dirty = False
    widget.close()
    app.processEvents()


def test_keyboard_create_save_and_palette_open(window: WorkstationWindow) -> None:
    def enter_name() -> None:
        dialog = QApplication.activeModalWidget()
        if isinstance(dialog, QInputDialog):
            editor = dialog.findChild(QLineEdit)
            if isinstance(editor, QLineEdit):
                QTest.keyClicks(editor, "Keyboard draft")
                QTest.keyClick(editor, Qt.Key.Key_Return)

    QTimer.singleShot(0, enter_name)
    QTest.keySequence(window, QKeySequence(QKeySequence.StandardKey.New))
    assert window.current is not None and window.current.draft_id == "Keyboard draft"
    assert window.dirty
    window.activateWindow()
    QApplication.processEvents()
    QTest.keySequence(window, QKeySequence(QKeySequence.StandardKey.Save))
    assert not window.dirty
    assert not window.action_registry.actions["draft.save"].isEnabled()
    assert isinstance(window.gateway, RecordingGateway)
    names = [command.command_name for command in window.gateway.calls]
    assert names.count("draft.create") == 1
    assert names.count("draft.save") == 1
    assert not any(name in {"run.start", "draft.validate"} for name in names)
    palette = CommandPalette(window.action_registry, window)
    palette.search.setText("close draft")
    palette.activate_selected()
    assert window.current is None
    window.activateWindow()
    QApplication.processEvents()

    def choose_first() -> None:
        dialog = QApplication.activeModalWidget()
        if isinstance(dialog, QDialog):
            QTest.keyClick(dialog, Qt.Key.Key_Return)

    QTimer.singleShot(0, choose_first)
    QTest.keySequence(window, QKeySequence(QKeySequence.StandardKey.Open))
    assert window.current is not None and not window.dirty


def test_cancel_preserves_unsaved_draft_and_close_does_not_autosave(
    window: WorkstationWindow,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert window.create_draft("Keep this")
    monkeypatch.setattr(QMessageBox, "exec", lambda self: QMessageBox.StandardButton.Cancel)
    window.close_draft()
    assert window.current is not None and window.dirty
    assert not window.close()
    assert isinstance(window.gateway, RecordingGateway)
    assert "draft.save" not in [item.command_name for item in window.gateway.calls]
    monkeypatch.setattr(QMessageBox, "exec", lambda self: QMessageBox.StandardButton.Save)
    window.close_draft()
    assert window.current is None and not window.dirty
    assert "draft.save" in [item.command_name for item in window.gateway.calls]


def test_unavailable_run_has_consistent_enablement(window: WorkstationWindow) -> None:
    assert window.create_draft("No fabricated results")
    for name in ("run.start", "draft.validate"):
        action = window.action_registry.actions[name]
        assert not action.isEnabled()
        assert "unavailable" in action.toolTip()
    palette = CommandPalette(window.action_registry, window)
    palette.search.setText("run.start")
    palette.activate_selected()
    assert window.last_outcome is not None
    assert isinstance(window.last_outcome.data, DraftDto)
    assert "Convergence: not run" in window.scientific_status.text()
    assert "Closure: not checked" in window.scientific_status.text()
    assert "Physical: unknown" in window.scientific_status.text()
    assert "Correlation: unknown" in window.scientific_status.text()
    # On macOS an explicit accessible name replaces the label's changing value.
    assert not window.scientific_status.accessibleName()
    assert not window.selection_title.accessibleName()
    assert window.scientific_status.accessibleDescription() == "Independent engineering states"
    assert isinstance(window.gateway, RecordingGateway)
    assert not any(item.command_name == "run.start" for item in window.gateway.calls)


def test_layout_focus_theme_shortcuts_round_trip(
    window: WorkstationWindow, tmp_path: Path, app: QApplication
) -> None:
    window.navigator_dock.hide()
    window.action_registry.actions["focus.navigator"].trigger()
    assert window.navigator_dock.isVisible()
    assert window.navigator.hasFocus()
    sequence = QKeySequence("Ctrl+Alt+N")
    assert window.action_registry.assign("draft.create", sequence) is None
    assert window.action_registry.assign("draft.open", sequence) is not None
    assert window.action_registry.assign("draft.open", QKeySequence("Ctrl+Q")) is not None
    window.set_theme("Light")
    window.inspector_dock.hide()
    assert window.close()
    restored = WorkstationWindow(
        create_preview_gateway(tmp_path), WorkspaceSettings(tmp_path / "workspace.ini")
    )
    restored.show()
    app.processEvents()
    assert restored.theme == "Light"
    assert not restored.inspector_dock.isVisible()
    assert restored.action_registry.actions["draft.create"].shortcut() == sequence
    assert restored.current is None
    restored.restore_default_layout()
    assert restored.inspector_dock.isVisible()
    restored.close()


def test_invalid_layout_is_recoverable(tmp_path: Path, app: QApplication) -> None:
    settings = WorkspaceSettings(tmp_path / "workspace.ini")
    settings.settings.setValue("layout/version", 900)
    settings.settings.setValue("layout/state", "malformed")
    widget = WorkstationWindow(create_preview_gateway(tmp_path), settings)
    widget.show()
    app.processEvents()
    assert widget.navigator_dock.isVisible() and widget.inspector_dock.isVisible()
    assert widget.current is None
    widget.close()


def test_corrupt_dock_state_does_not_apply_partial_geometry(window: WorkstationWindow) -> None:
    settings = window.workspace.settings
    settings.setValue("layout/version", LAYOUT_VERSION)
    window.resize(1200, 760)
    settings.setValue("layout/geometry", window.saveGeometry())
    settings.setValue("layout/state", QByteArray(b"invalid dock state"))
    window.resize(1300, 800)
    previous_size = window.size()
    assert not window.workspace.restore(window)
    assert window.size() == previous_size
    assert window.navigator_dock.isVisible()


def test_shortcut_swaps_restore_atomically_and_bad_maps_retain_defaults(
    window: WorkstationWindow,
) -> None:
    registry = window.action_registry
    new = registry.actions["draft.create"].shortcut()
    opened = registry.actions["draft.open"].shortcut()
    portable = QKeySequence.SequenceFormat.PortableText
    swapped = {"draft.create": opened.toString(portable), "draft.open": new.toString(portable)}
    assert registry.restore(swapped) == ()
    assert registry.actions["draft.create"].shortcut() == opened
    assert registry.actions["draft.open"].shortcut() == new
    before = dict(registry.overrides)
    assert registry.restore({"draft.open": opened.toString(portable)})
    assert registry.overrides == before
    assert registry.actions["draft.open"].shortcut() == new
    assert registry.restore({"draft.open": "not a key"})


def test_failed_save_preserves_unsaved_draft(
    window: WorkstationWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert window.create_draft("Unsaved after failure")
    original = window.current
    assert isinstance(window.gateway, RecordingGateway)
    delegate = window.gateway.delegate
    assert isinstance(delegate, CommandRegistry)
    assert isinstance(delegate.services, ApplicationServices)

    def failed_save(_draft: DraftDto) -> DraftDto:
        raise OSError("a private path must not be exposed")

    monkeypatch.setattr(delegate.services.drafts, "save", failed_save)
    assert not window.save_current()
    assert window.current is original and window.dirty
    assert window.last_outcome is not None
    assert window.last_outcome.diagnostics[0].code == "BOUNDARY_FAILURE"
    assert "private path" not in str(window.last_outcome)


def test_rejected_payload_cannot_acknowledge_save(
    window: WorkstationWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert window.create_draft("Retain unsaved identity")
    current = window.current
    monkeypatch.setattr(
        window.gateway,
        "dispatch",
        lambda request: CommandOutcome(request.request_id, "REJECTED", data=current),
    )
    assert not window.save_current()
    assert window.current is current and window.dirty


def test_preview_draft_catalog_and_name_collision(tmp_path: Path) -> None:
    gateway = create_preview_gateway(tmp_path)
    create = gateway.dispatch(
        CommandRequest("draft.create", "one", "owner", CreateDraftParameters("Cooling loop"))
    )
    assert isinstance(create.data, DraftDto)
    assert list((tmp_path / "drafts").glob("*.json")) == []
    saved = gateway.dispatch(
        CommandRequest("draft.save", "two", "owner", DraftParameters(create.data))
    )
    assert isinstance(saved.data, DraftDto)
    # Existing filename normalization must not turn another name into an overwrite.
    collision = gateway.dispatch(
        CommandRequest("draft.create", "three", "owner", CreateDraftParameters("Cooling-loop"))
    )
    assert collision.diagnostics[0].code == "DRAFT_EXISTS"
    listing = gateway.dispatch(
        CommandRequest("draft.list", "four", "owner", ListDraftsParameters())
    )
    assert isinstance(listing.data, DraftListDto)
    assert [entry.draft_id for entry in listing.data.drafts] == ["Cooling loop"]
    rejected = gateway.dispatch(
        CommandRequest("draft.validate", "five", "owner", DraftParameters(saved.data))
    )
    assert rejected.diagnostics[0].code == "CAPABILITY_UNAVAILABLE"


def test_small_window_and_high_contrast_retain_controls(
    window: WorkstationWindow, app: QApplication
) -> None:
    window.resize(1040, 720)
    window.set_theme("High contrast")
    app.processEvents()
    assert window.welcome_new.isVisible()
    assert window.welcome_open.isVisible()
    assert window.welcome_new.height() >= 32
    assert window.scientific_status.wordWrap() is False
    assert window.welcome_new.accessibleName()
    QTest.keyClick(window.welcome_new, Qt.Key.Key_Tab)
    assert QApplication.focusWidget() is not None
