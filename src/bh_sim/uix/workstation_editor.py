"""DW3.2 canvas-centred workstation over durable neutral history commands.

Widgets own only interaction, presentation and personal navigation. History,
checkpoint integrity, editing policy and comparisons live behind the gateway.
"""

from __future__ import annotations

import json
import shlex
import threading
from dataclasses import dataclass, replace
from dataclasses import field as dataclass_field
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent, QKeySequence, QTransform
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QStyle,
    QTabBar,
    QTabWidget,
    QToolBar,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from bh_sim.boundary import contracts as c
from bh_sim.boundary.ports import CommandGateway

from .command_line import CommandLine
from .graph_viewer import GraphDialog, GraphViewer
from .pfd_editor import PfdEditorWindow
from .workbook_view import WorkbookView
from .workspace import LAYOUT_VERSION, WorkspaceSettings


@dataclass
class CaseSession:
    """Independent personal navigation; no scientific value or history authority."""

    state: c.HistoryState
    selection: tuple[str, ...] = ()
    centre: tuple[float, float] = (0.0, 0.0)
    scale: float = 1.0
    active_group: str | None = None
    isolated_group: str | None = None
    preview: c.HistoryState | None = None
    workspace: str = "flowsheet"
    last_receipt: c.ValidationReceiptDto | None = None
    validated_engineering_hash: str | None = None
    _validated_pfd_hash: str | None = None
    last_run_view: c.RunViewDto | None = None
    last_valid_run_view: c.RunViewDto | None = None
    workbook: c.WorkbookDto | None = None
    last_valid_workbook: c.WorkbookDto | None = None
    overlays: c.OverlaysDto | None = None
    last_valid_overlays: c.OverlaysDto | None = None
    # Capture the exact native engineering projection submitted for each result.
    run_source_hashes: dict[str, str] = dataclass_field(default_factory=dict)
    selected_run_id: str | None = None
    active_plot: c.PlotDefinitionDto | None = None


class WorkstationEditor(PfdEditorWindow):
    """Modern shell that reuses the verified PFD gestures and shared action bindings."""

    def __init__(self, gateway: CommandGateway, settings: WorkspaceSettings) -> None:
        self.studio_ready = False
        self.sessions: dict[str, CaseSession] = {}
        self.active_id: str | None = None
        self.switching = False
        self.pending_inputs: list[tuple[str, c.ConfigureInputEdit]] = []
        self.flushing_inputs = False
        self._floating_graphs: list[GraphDialog] = []
        super().__init__(gateway, settings)
        self._build_studio()
        self.studio_ready = True
        self.apply_preset("Design")
        settings.restore(self)
        self.set_ribbon(settings.ribbon())
        self._restore_sessions()
        self.refresh()

    @property
    def session(self) -> CaseSession | None:
        """Active tab state; history remains an immutable application response."""
        return self.sessions.get(self.active_id or "")

    def _button(self, identifier: str, title: str, parent: QWidget) -> QToolButton:
        button = QToolButton(parent)
        action = self.action_registry.actions[identifier]
        button.setDefaultAction(action)
        button.setText(title)
        button.setToolTip(action.toolTip())
        button.setAccessibleName(title)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        # Restore the short surface label when QAction enablement changes.
        action.changed.connect(lambda: button.setText(title))
        return button

    def _build_studio(self) -> None:
        """Replace shell scaffolding with a full canvas and modular native docks."""
        self._legacy_toolbars = self.findChildren(QToolBar)
        for toolbar in self._legacy_toolbars:
            self.removeToolBar(toolbar)
            toolbar.hide()
        page = self.pages.widget(1)
        assert page is not None and page.layout() is not None
        layout = page.layout()
        assert layout is not None
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget() if item else None
            if widget is not None:
                widget.hide()
        layout.setContentsMargins(0, 0, 0, 0)
        self.case_tabs = QTabBar()
        self.case_tabs.setAccessibleName("Open case tabs")
        self.case_tabs.setTabsClosable(True)
        self.case_tabs.setExpanding(False)
        self.case_tabs.currentChanged.connect(self.switch_tab)
        self.case_tabs.tabCloseRequested.connect(self.close_tab)
        layout.addWidget(self.case_tabs)
        self.case_identity = QLabel()
        self.case_identity.setTextFormat(Qt.TextFormat.PlainText)
        self.case_identity.setContentsMargins(12, 5, 12, 5)
        layout.addWidget(self.case_identity)
        layout.addWidget(self.canvas)
        self.canvas.show()
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.equipment.setMaximumHeight(16777215)
        self.workbook_view = WorkbookView()
        self.workbook_view.unit_selected.connect(self._on_workbook_unit_selected)
        self.workbook_view.stream_selected.connect(self._on_workbook_stream_selected)
        self.workbook_view.plot_requested.connect(self.plot_object)
        self.workbook_dock = self._dock("Workbooks", "workbook-dock", self.workbook_view)
        self.graph_viewer = GraphViewer()
        self.graph_viewer.pop_out_requested.connect(self.open_graph_window)
        self.graph_dock = self._dock("Graphs", "graphs-dock", self.graph_viewer)
        self.history_tree = QTreeWidget()
        self.history_tree.setHeaderLabels(["Change / checkpoint", "Author", "Path"])
        self.history_tree.setAccessibleName("Persistent editing history")
        self.history_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.history_tree.itemActivated.connect(
            lambda item, _column: self.preview_entry(str(item.data(0, Qt.ItemDataRole.UserRole)))
        )
        history_panel = QWidget()
        history_layout = QVBoxLayout(history_panel)
        history_layout.setContentsMargins(8, 6, 8, 6)
        controls = QHBoxLayout()
        for title, callback in (
            ("View selected", self.preview_selected),
            ("Return to current", self.return_current),
            ("Continue as alternative", self.branch_selected),
            ("Snapshot…", self.snapshot_dialog),
        ):
            button = QPushButton(title)
            button.clicked.connect(callback)
            controls.addWidget(button)
        controls.addStretch()
        history_layout.addLayout(controls)
        history_layout.addWidget(self.history_tree)
        self.history_dock = self._dock("History", "history-dock", history_panel)
        self.console = CommandLine(
            self.run_command, self.complete_command, self.workspace.command_history()
        )
        self.commands_dock = self._dock("Commands", "commands-dock", self.console)
        self._build_comparison()
        self.activity_dock.setWindowTitle("Diagnostics")
        for dock in (
            self.workbook_dock,
            self.graph_dock,
            self.history_dock,
            self.commands_dock,
            self.compare_dock,
        ):
            self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
            self.tabifyDockWidget(self.activity_dock, dock)
        browser_panel = QWidget()
        browser_layout = QVBoxLayout(browser_panel)
        browser_layout.setContentsMargins(6, 6, 6, 6)
        self.browser_search = QLineEdit()
        self.browser_search.setPlaceholderText("Find case or object…")
        self.browser_search.setAccessibleName("Search project browser")
        self.browser_search.textChanged.connect(self.filter_browser)
        browser_layout.addWidget(self.browser_search)
        browser_layout.addWidget(self.navigator)
        self.navigator_dock.setWidget(browser_panel)
        self.navigator_dock.setWindowTitle("Project browser")
        self.palette_dock.setWindowTitle("Equipment · test fixtures")
        self.layers_tree.setColumnCount(1)
        self.layers_tree.setHeaderLabel("Layers & Groups")
        self.layers_tree.setMinimumHeight(160)
        self._compact_layer_controls()
        # Inspector explains the selected object; long model metadata can be expanded.
        self.advanced = QToolButton()
        self.advanced.setText("Advanced details")
        self.advanced.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.advanced.setCheckable(True)
        self.input_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        self.advanced.setArrowType(Qt.ArrowType.RightArrow)
        self.advanced_details = QLabel()
        self.advanced_details.setTextFormat(Qt.TextFormat.PlainText)
        self.advanced_details.setWordWrap(True)
        self.advanced_details.hide()
        self.advanced.toggled.connect(self.advanced_details.setVisible)
        inspector = self.inspector_dock.widget()
        assert inspector is not None and inspector.layout() is not None
        inspector_layout = inspector.layout()
        assert inspector_layout is not None
        inspector_layout.addWidget(self.advanced)
        inspector_layout.addWidget(self.advanced_details)
        self.plot_button = QPushButton("Plot Object…")
        self.plot_button.setToolTip(
            "Plot T-Q, residual or spatial profile for the selected unit/stream"
        )
        self.plot_button.clicked.connect(self._on_inspector_plot_clicked)
        inspector_layout.addWidget(self.plot_button)
        add = self.action_registry.add
        for identifier, title, callback in (
            ("history.snapshot", "Named snapshot…", self.snapshot_dialog),
            (
                "view.history",
                "History",
                lambda: self.focus_panel(self.history_dock, self.history_tree),
            ),
            (
                "view.commands",
                "Command line",
                lambda: self.focus_panel(self.commands_dock, self.console.input),
            ),
            ("view.compare", "Compare versions", self.show_compare),
            (
                "view.workbook",
                "Workbooks",
                lambda: self.focus_panel(self.workbook_dock, self.workbook_view.tabs),
            ),
            (
                "view.graph",
                "Graphs",
                lambda: self.focus_panel(self.graph_dock, self.graph_viewer.plot_canvas),
            ),
            ("graph.open_window", "Open graph in window", self.open_graph_window),
            ("result.overlays_toggle", "Toggle canvas overlays", self.toggle_canvas_overlays),
            ("workspace.export", "Export workspace template…", self.export_workspace),
            ("workspace.import", "Import workspace template…", self.import_workspace),
            ("pfd.export_image", "Export flowsheet image…", self.export_image),
        ):
            add(identifier, title, callback)
        add("workspace.ribbon", "Ribbon", self.toggle_ribbon).setCheckable(True)
        self.action_registry.assign("view.commands", QKeySequence("Ctrl+Shift+L"))
        for preset in ("Design", "Compare", "Review"):
            add("layout." + preset, preset + " layout", lambda p=preset: self.apply_preset(p))
        self.action_registry.actions["draft.save"].setText("Save version")
        self.action_registry.actions["pfd.undo"].setText("Undo")
        self.action_registry.actions["pfd.redo"].setText("Redo")
        for identifier, icon in (
            ("draft.save", QStyle.StandardPixmap.SP_DialogSaveButton),
            ("draft.open", QStyle.StandardPixmap.SP_DirOpenIcon),
            ("pfd.undo", QStyle.StandardPixmap.SP_ArrowBack),
            ("pfd.redo", QStyle.StandardPixmap.SP_ArrowForward),
        ):
            self.action_registry.actions[identifier].setIcon(self.style().standardIcon(icon))
        self.command_bar = QToolBar("Project commands", self)
        self.command_bar.setObjectName("studio-project-toolbar")
        self.command_bar.setMovable(False)
        brand = QLabel("  BH  ")
        brand.setObjectName("eyebrow")
        self.command_bar.addWidget(brand)
        for identifier, title in (
            ("draft.create", "New"),
            ("draft.open", "Open"),
            ("draft.save", "Save"),
            ("pfd.undo", "Undo"),
            ("pfd.redo", "Redo"),
            ("history.snapshot", "Snapshot"),
        ):
            self.command_bar.addWidget(self._button(identifier, title, self.command_bar))
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.command_bar.addWidget(spacer)
        self.presets = QComboBox()
        self.presets.setAccessibleName("Layout preset")
        self.presets.addItems(("Design", "Compare", "Review"))
        self.presets.textActivated.connect(self.apply_preset)
        self.command_bar.addWidget(self.presets)
        for identifier, title in (
            ("commands.palette", "Find command"),
            ("workspace.ribbon", "Ribbon"),
        ):
            self.command_bar.addWidget(self._button(identifier, title, self.command_bar))
        self.addToolBar(self.command_bar)
        self.tools_bar = QToolBar("Contextual tools", self)
        self.tools_bar.setObjectName("studio-context-toolbar")
        self.tools_bar.setMovable(False)
        self.workspace_switcher.show()
        self.tools_bar.addWidget(self.workspace_switcher)
        self.tools_bar.addSeparator()
        for identifier, title in (
            ("pfd.focus", "Select"),
            ("pfd.add", "Add"),
            ("pfd.connect", "Connect"),
            ("pfd.rename", "Rename"),
            ("pfd.delete", "Delete"),
            ("pfd.fit", "Fit"),
            ("pfd.layers", "Layers"),
            ("pfd.settings", "Settings"),
            ("draft.validate", "Validate"),
            ("run.start", "Run"),
            ("run.cancel", "Cancel"),
        ):
            self.tools_bar.addWidget(self._button(identifier, title, self.tools_bar))
        self.addToolBarBreak()
        self.addToolBar(self.tools_bar)
        self.ribbon = QToolBar("Ribbon commands", self)
        self.ribbon.setObjectName("studio-ribbon-toolbar")
        self.ribbon.setMovable(False)
        ribbon_tabs = QTabWidget()
        ribbon_tabs.setAccessibleName("Ribbon command groups")
        for title, identifiers in (
            ("Create", ("pfd.add", "pfd.connect", "pfd.paste", "pfd.paste_connected")),
            ("Edit", ("pfd.rename", "pfd.delete", "pfd.undo", "pfd.redo", "pfd.settings")),
            ("View", ("pfd.fit", "pfd.zoom_reset", "pfd.layers", "view.commands", "view.history")),
            (
                "Review",
                ("view.compare", "history.snapshot", "draft.validate", "run.start", "run.cancel"),
            ),
        ):
            panel = QWidget()
            row = QHBoxLayout(panel)
            row.setContentsMargins(6, 3, 6, 3)
            for identifier in identifiers:
                row.addWidget(
                    self._button(
                        identifier,
                        self.action_registry.actions[identifier].text().replace("&", ""),
                        panel,
                    )
                )
            row.addStretch()
            ribbon_tabs.addTab(panel, title)
        self.ribbon.addWidget(ribbon_tabs)
        self.addToolBar(self.ribbon)
        for action in self.menuBar().actions():
            menu = action.menu()
            if isinstance(menu, QMenu) and action.text().replace("&", "") == "View":
                for dock in (
                    self.palette_dock,
                    self.workbook_dock,
                    self.history_dock,
                    self.commands_dock,
                    self.compare_dock,
                ):
                    menu.addAction(dock.toggleViewAction())
                for identifier in (
                    "workspace.ribbon",
                    "workspace.import",
                    "workspace.export",
                    "layout.Design",
                    "layout.Compare",
                    "layout.Review",
                ):
                    menu.addAction(self.action_registry.actions[identifier])
        self.bottom_bar = QToolBar("Workspace panels", self)
        self.bottom_bar.setObjectName("studio-panel-toolbar")
        self.bottom_bar.setMovable(False)
        self.action_registry.register_existing(
            "view.workbook", self.workbook_dock.toggleViewAction()
        )
        for identifier, title in (
            ("view.history", "History"),
            ("view.activity", "Diagnostics"),
            ("view.workbook", "Workbooks"),
            ("view.commands", "Commands"),
            ("view.compare", "Compare"),
        ):
            self.bottom_bar.addWidget(self._button(identifier, title, self.bottom_bar))
        self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, self.bottom_bar)
        self.action_registry.restore(self.workspace.shortcuts())

    def _compact_layer_controls(self) -> None:
        """Keep groups reachable while less frequent styling/motion controls collapse."""
        panel = self.layers_tree.parentWidget()
        assert panel is not None
        layout = panel.layout()
        assert layout is not None
        # The retained PFD editor supplies a tree, base form, group grid, motion form
        # and legend. Reuse their handlers; only rearrange their presentation.
        items = [layout.takeAt(0) for _ in range(layout.count())]
        assert len(items) == 5 and all(item is not None for item in items)
        layout.addWidget(self.layers_tree)
        group_layout = items[2].layout() if items[2] else None
        assert isinstance(group_layout, QGridLayout)
        buttons = []
        while group_layout.count():
            item = group_layout.takeAt(0)
            if item and item.widget():
                buttons.append(item.widget())
        for i, button in enumerate(buttons):
            assert button is not None
            group_layout.addWidget(button, i // 2, i % 2)
        group_panel = QWidget()
        group_panel.setLayout(group_layout)
        layout.addWidget(group_panel)
        for title, index in (("Base appearance", 1), ("Motion", 3)):
            content = QWidget()
            section_item = items[index]
            form = section_item.layout() if section_item else None
            assert form is not None
            content.setLayout(form)
            toggle = QToolButton()
            toggle.setText(title)
            toggle.setCheckable(True)
            toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            toggle.setArrowType(Qt.ArrowType.RightArrow)
            toggle.toggled.connect(content.setVisible)
            toggle.toggled.connect(
                lambda checked, t=toggle: t.setArrowType(
                    Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow
                )
            )
            layout.addWidget(toggle)
            layout.addWidget(content)
            content.hide()
        layout.addWidget(self.layer_legend)

    def _build_comparison(self) -> None:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        row = QHBoxLayout()
        self.compare_before, self.compare_after = QComboBox(), QComboBox()
        self.compare_before.setAccessibleName("Before saved version")
        self.compare_after.setAccessibleName("After saved version")
        row.addWidget(self.compare_before, 1)
        row.addWidget(self.compare_after, 1)
        button = QPushButton("Compare")
        button.clicked.connect(self.compare_versions)
        row.addWidget(button)
        layout.addLayout(row)
        self.comparison = QTreeWidget()
        self.comparison.setHeaderLabels(["Kind", "Object / field", "Before", "After"])
        self.comparison.setAccessibleName("Structural version differences")
        self.comparison.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.comparison)
        self.review_context = QLabel(
            "Choose saved versions or named snapshots. Result calculations remain gated."
        )
        self.review_context.setWordWrap(True)
        layout.addWidget(self.review_context)
        self.compare_dock = self._dock("Compare / Review", "compare-dock", panel)

    def execute(self, name: str, parameters: c.CommandParameters) -> c.CommandOutcome:
        """All command surfaces share application admission and visible diagnostics."""
        if self.studio_ready and name in {"draft.list", "pfd.list"}:
            name = "history.list"
        return super().execute(name, parameters)

    def _target(self, *, entry_id: str = "", name: str = "") -> c.HistoryTarget:
        assert self.session is not None and self.active_id is not None
        return c.HistoryTarget(
            self.active_id, self.session.state.entries[-1].entry_id, entry_id, name
        )

    def _remember_view(self) -> None:
        if self.session is None:
            return
        point = self.canvas.mapToScene(self.canvas.viewport().rect().center())
        self.session.centre = (point.x(), point.y())
        self.session.scale = self.canvas.transform().m11()
        self.session.selection = self.canvas.selected_ids()
        if self.last_receipt and self.last_receipt.draft_id == self.active_id:
            self.session.last_receipt = self.last_receipt
        if self.last_run_view and self.last_run_view.case_id == self.active_id:
            self.session.last_run_view = self.last_run_view

    def _adopt(self, state: c.HistoryState, *, new: bool = False) -> None:
        identifier = state.document.draft.draft_id
        if identifier not in self.sessions:
            self.sessions[identifier] = CaseSession(state)
            self.case_tabs.blockSignals(True)
            index = self.case_tabs.addTab(identifier)
            self.case_tabs.setTabData(index, identifier)
            self.case_tabs.blockSignals(False)
        else:
            session = self.sessions[identifier]
            session.state = state
            session.preview = None
            if not new:
                current_pfd_hash = c.pfd_engineering_content_hash(state.document)
                if (
                    session._validated_pfd_hash is None
                    or session._validated_pfd_hash != current_pfd_hash
                ):
                    session.last_receipt = None
                    session.validated_engineering_hash = None
                    session._validated_pfd_hash = None
        self.active_id = identifier
        for i in range(self.case_tabs.count()):
            if self.case_tabs.tabData(i) == identifier:
                self.case_tabs.blockSignals(True)
                self.case_tabs.setCurrentIndex(i)
                self.case_tabs.blockSignals(False)
        self.document, self.current, self.dirty = state.document, state.document.draft, state.dirty
        self.last_receipt = self.sessions[identifier].last_receipt
        self.last_run_view = self.sessions[identifier].last_run_view
        self.refresh()
        if new:
            self.canvas.resetTransform()
            self.canvas.centerOn(*self.sessions[identifier].centre)
        self.refresh_catalog()
        self._persist_navigation()

    def create_draft(self, name: str) -> bool:
        if not self.studio_ready:
            return super().create_draft(name)
        if not self.flush_input_edits():
            return False
        self._remember_view()
        listing = self.execute("history.list", c.ListDraftsParameters())
        if not isinstance(listing.data, c.DraftListDto):
            return False
        if name in self.sessions or any(d.draft_id == name for d in listing.data.drafts):
            self.note("A draft already uses that name; open its existing history.")
            return False
        draft = self.execute("draft.create", c.CreateDraftParameters(name))
        if not isinstance(draft.data, c.DraftDto):
            return False
        document = self.execute("pfd.import", c.DraftParameters(draft.data))
        if not isinstance(document.data, c.PfdDocumentDto):
            return False
        outcome = self.execute("history.start", c.PfdDocumentParameters(document.data))
        if isinstance(outcome.data, c.HistoryState):
            self._adopt(outcome.data, new=True)
            return True
        return False

    def open_draft(self, draft_id: str) -> bool:
        if not self.studio_ready:
            return super().open_draft(draft_id)
        if not self.flush_input_edits():
            return False
        self._remember_view()
        if draft_id in self.sessions:
            for i in range(self.case_tabs.count()):
                if self.case_tabs.tabData(i) == draft_id:
                    self.case_tabs.setCurrentIndex(i)
            return True
        stored_views = self.workspace.settings.value("navigation/views", "{}")
        outcome = self.execute("history.open", c.HistoryTarget(draft_id))
        if isinstance(outcome.data, c.HistoryState):
            self.canvas.document = None
            self._adopt(outcome.data, new=True)
            self.workspace.settings.setValue("navigation/views", stored_views)
            self._restore_case_view(draft_id)
            self._persist_navigation()
            return True
        return False

    def _mutate(self, command: str, target: c.HistoryTarget | None = None) -> bool:
        if not self.flush_input_edits():
            return False
        if target is not None and self.session:
            target = replace(target, expected_head=self.session.state.entries[-1].entry_id)
        if not self.session or self.session.preview:
            self.note(
                "Historical view is read-only. Return to current or continue as an alternative."
            )
            return False
        self._remember_view()
        outcome = self.execute(command, target or self._target())
        if isinstance(outcome.data, c.HistoryState):
            self._adopt(outcome.data)
            return True
        return False

    def schedule_input_edit(self, edit: c.ConfigureInputEdit) -> None:
        """Retain the originating tab until a finished input edit reaches durable history."""
        self.last_receipt = None
        if self.active_id is not None:
            session = self.sessions.get(self.active_id)
            if session:
                session.last_receipt = None
                session.validated_engineering_hash = None
                session._validated_pfd_hash = None
            self.pending_inputs.append((self.active_id, edit))
            QTimer.singleShot(0, self.flush_input_edits)

    def flush_input_edits(self) -> bool:
        """Finish focused input before saving/navigating, never against another case."""
        if not self.studio_ready or self.flushing_inputs:
            return True
        self.flushing_inputs = True
        succeeded = True
        try:
            # A toolbar shortcut or pending native focus event can leave a modified
            # field without active focus. Finish all changed input rows before
            # rebuilding the form; their handlers capture the current object IDs.
            for field in self.input_panel.findChildren(QLineEdit):
                if field.isModified():
                    field.editingFinished.emit()
            focus = self.focusWidget()
            if focus is not None and self.input_panel.isAncestorOf(focus):
                focus.clearFocus()
            while self.pending_inputs:
                identifier, edit = self.pending_inputs.pop(0)
                session = self.sessions.get(identifier)
                if session is None:
                    self.note("Input's original case is unavailable; change was not applied.")
                    succeeded = False
                    continue
                if identifier == self.active_id:
                    succeeded = self.apply_edit(edit) and succeeded
                else:
                    outcome = self.execute(
                        "history.edit",
                        c.HistoryEditParameters(
                            c.HistoryTarget(identifier, session.state.entries[-1].entry_id), edit
                        ),
                    )
                    if isinstance(outcome.data, c.HistoryState):
                        session.state = outcome.data
                    else:
                        succeeded = False
            return succeeded
        finally:
            self.flushing_inputs = False

    def apply_edit(self, edit: c.PfdEdit) -> bool:
        if not self.studio_ready:
            return super().apply_edit(edit)
        if not self.flushing_inputs and not self.flush_input_edits():
            return False
        if not self.session or self.session.preview:
            self.note("Historical view is read-only; continue as an alternative to edit.")
            self.refresh()
            return False
        # Reject ambiguous shortcuts before committing case preferences.
        if isinstance(edit, c.SettingsEdit):
            prior = dict(self.action_registry.overrides)
            errors = self.action_registry.restore(dict(edit.settings.shortcuts))
            self.action_registry.restore({**self.default_bindings, **prior})
            if errors:
                self.note("; ".join(errors))
                return False
        self._remember_view()
        outcome = self.execute("history.edit", c.HistoryEditParameters(self._target(), edit))
        if isinstance(outcome.data, c.HistoryState):
            self._adopt(outcome.data)
            if isinstance(edit, c.SettingsEdit):
                self.action_registry.restore(dict(edit.settings.shortcuts))
            if (
                isinstance(edit, c.ConnectPortsEdit)
                and outcome.data.document.settings.prompt_stream_name
            ):
                self.canvas.select_ids((outcome.data.document.draft.connections[-1].object_id,))
                QTimer.singleShot(0, self.rename_dialog)
            return True
        self.refresh()
        return False

    def undo(self) -> None:
        self._mutate("history.undo")

    def redo(self) -> None:
        self._mutate("history.redo")

    def save_current(self) -> bool:
        return self._mutate("history.save") if self.studio_ready else super().save_current()

    def snapshot_named(self, name: str) -> bool:
        return bool(self.session) and self._mutate("history.snapshot", self._target(name=name))

    def snapshot_dialog(self) -> None:
        if not self.session:
            return
        name, accepted = QInputDialog.getText(self, "Named snapshot", "Checkpoint name")
        if accepted:
            self.snapshot_named(name)

    def switch_tab(self, index: int) -> None:
        if not self.studio_ready or self.switching or index < 0:
            return
        if not self.flush_input_edits():
            self.case_tabs.blockSignals(True)
            for i in range(self.case_tabs.count()):
                if self.case_tabs.tabData(i) == self.active_id:
                    self.case_tabs.setCurrentIndex(i)
            self.case_tabs.blockSignals(False)
            return
        identifier = str(self.case_tabs.tabData(index))
        if identifier == self.active_id:
            return
        self._remember_view()
        self.active_id = identifier
        self.canvas.document = None
        self.last_receipt = self.sessions[identifier].last_receipt
        self.last_run_view = self.sessions[identifier].last_run_view
        self.refresh()
        assert self.session is not None
        self.canvas.setTransform(QTransform.fromScale(self.session.scale, self.session.scale))
        self.canvas.centerOn(*self.session.centre)
        self.canvas.select_ids(self.session.selection)
        self.refresh_catalog()
        self._persist_navigation()

    def close_tab(self, index: int) -> None:
        if not self.flush_input_edits():
            return
        identifier = str(self.case_tabs.tabData(index))
        self._remember_view()
        self._persist_navigation()
        self.sessions.pop(identifier, None)
        self.case_tabs.blockSignals(True)
        self.case_tabs.removeTab(index)
        self.case_tabs.blockSignals(False)
        if self.active_id == identifier:
            self.active_id = None
            if self.case_tabs.count():
                self.switch_tab(self.case_tabs.currentIndex())
            else:
                self.document = self.current = None
                self.dirty = False
                self.refresh()
        self._persist_navigation()

    def close_draft(self) -> None:
        if self.studio_ready and self.case_tabs.count():
            self.close_tab(self.case_tabs.currentIndex())
        elif not self.studio_ready:
            super().close_draft()

    @staticmethod
    def _result_is_stale(session: CaseSession, run_id: str | None) -> bool:
        """Compare source content, independent of Save/dirty state and tab selection."""
        document = (session.preview or session.state).document
        return session.run_source_hashes.get(run_id or "") != c.pfd_engineering_content_hash(
            document
        )

    def refresh(self) -> None:
        if not self.studio_ready:
            super().refresh()
            return
        session = self.session
        desired_selection = session.selection if session else ()
        canonical = None
        if session:
            state = session.preview or session.state
            canonical = state.document
            self.current, self.dirty = canonical.draft, session.state.dirty
            effective = replace(
                canonical.layer_preferences, active_visual_group_id=session.active_group
            )
            groups = canonical.visual_groups
            if session.isolated_group:
                groups = tuple(
                    replace(g, visible=g.group_id == session.isolated_group) for g in groups
                )
            self.document = replace(canonical, layer_preferences=effective, visual_groups=groups)
        else:
            self.document = self.current = None
        super().refresh()
        self.document = canonical
        self.equipment.show()
        if session:
            assert canonical is not None
            self.last_receipt = session.last_receipt
            self.last_run_view = session.last_run_view
            self.workbook_view.set_workbook(
                session.workbook,
                is_stale=self._result_is_stale(session, session.workbook.run_id)
                if session.workbook
                else False,
            )
            overlays = session.overlays
            if overlays is not None:
                overlays = replace(
                    overlays,
                    selection=replace(
                        overlays.selection,
                        is_stale=self._result_is_stale(session, overlays.run_id),
                    ),
                )
            self.canvas.set_overlays(overlays)
            if session.last_run_view:
                rv = session.last_run_view
                validity_note = (
                    "" if self._is_valid_run(rv) else " · Retaining last valid flowsheet overlays"
                )
                status_text = (
                    f"Run: {rv.run_id} | "
                    f"Convergence: {rv.convergence.lower()} | "
                    f"Closure: {rv.closure.lower()} | "
                    f"Physical: {rv.physical_validity.lower()} | "
                    f"Correlation: {rv.correlation_validity.lower()}"
                    f"{validity_note}"
                )
                if self._result_is_stale(session, rv.run_id):
                    status_text += " · Stale result: engineering inputs changed"
                if overlays and overlays.selection.is_stale:
                    status_text += " · Stale canvas overlays"
                self.scientific_status.setText(status_text)
            head = session.state.entries[-1]
            versions = [e.saved_version for e in session.state.entries if e.saved_version]
            revision = f"r{versions[-1].revision}" if versions else "no saved version"
            view = "HISTORICAL · read-only" if session.preview else head.branch.name
            status = "Recovered locally · unsaved changes" if self.dirty else "Saved locally"
            self.case_identity.setText(f"{self.active_id}  /  {revision}  /  {view}  ·  {status}")
            self.save_status.setText("Historical view" if session.preview else status)
        else:
            self.last_receipt = None
            self.last_run_view = None
            self.workbook_view.set_workbook(None)
            self.canvas.set_overlays(None)
        if session:
            for i in range(self.case_tabs.count()):
                identifier = str(self.case_tabs.tabData(i))
                self.case_tabs.setTabText(
                    i, identifier + (" •" if self.sessions[identifier].state.dirty else "")
                )
            self.canvas.select_ids(desired_selection)
            if session.isolated_group:
                vgroups = canonical.visual_groups if canonical else ()
                group = next(
                    (g for g in vgroups if g.group_id == session.isolated_group),
                    None,
                )
                members = set(group.member_stream_ids) if group else set()
                for identifier in self.canvas.streams:
                    if identifier not in members:
                        for mapping in (
                            self.canvas.streams,
                            self.canvas.stream_labels,
                            self.canvas.stream_halos,
                            self.canvas.flow_markers,
                            self.canvas.stream_status_icons,
                        ):
                            mapping[identifier].hide()
            if session.preview:
                self.canvas.set_visualization_frame(None)
            self.history_tree.clear()
            for entry in reversed(session.state.entries):
                prefix = {"save": "Version", "snapshot": "Snapshot", "branch": "Alternative"}.get(
                    entry.kind, entry.kind.title()
                )
                item = QTreeWidgetItem(
                    [
                        f"{prefix} · {entry.label}",
                        "You" if entry.actor_id == self.workspace.actor_id() else entry.actor_id,
                        entry.branch.name,
                    ]
                )
                item.setData(0, Qt.ItemDataRole.UserRole, entry.entry_id)
                item.setToolTip(0, f"{entry.created_at}\n{entry.classification}\n{entry.entry_id}")
                self.history_tree.addTopLevelItem(item)
        editable = session is not None and session.preview is None
        self.canvas.setInteractive(editable)
        self.input_panel.setEnabled(editable)
        self.palette_dock.setEnabled(editable)
        self.layers_dock.setEnabled(editable)
        for identifier in self.action_registry.actions:
            if identifier.startswith("pfd.") and identifier not in {
                "pfd.focus",
                "pfd.fit",
                "pfd.zoom_reset",
                "pfd.groups",
                "pfd.layers",
                "pfd.copy",
                "pfd.export_image",
            }:
                self.action_registry.actions[identifier].setEnabled(editable)
        self.action_registry.actions["pfd.undo"].setEnabled(
            bool(editable and session and session.state.entries[-1].undo_ids)
        )
        self.action_registry.actions["pfd.redo"].setEnabled(
            bool(editable and session and session.state.entries[-1].redo_ids)
        )
        # Save also commits a focused field whose edit has not reached history yet.
        self.action_registry.actions["draft.save"].setEnabled(editable)
        self.action_registry.actions["history.snapshot"].setEnabled(editable)
        self.action_registry.actions["pfd.rename"].setEnabled(
            editable and len(self.canvas.selected_ids()) == 1
        )
        self.action_registry.actions["pfd.delete"].setEnabled(
            editable and bool(self.canvas.selected_ids())
        )

    def inspect_ids(self, identifiers: tuple[str, ...]) -> None:
        super().inspect_ids(identifiers)
        if not self.studio_ready:
            return
        if self.session:
            self.session.selection = identifiers
        for field in self.input_panel.findChildren(QLineEdit):
            field.textEdited.connect(self._on_input_text_edited)
        self.advanced_details.setText(
            "Object IDs: "
            + (", ".join(identifiers) or "No selection")
            + "\nCatalogue: reference test fixtures; scientific approval remains outstanding."
        )
        editable = self.session is not None and self.session.preview is None
        self.action_registry.actions["pfd.rename"].setEnabled(editable and len(identifiers) == 1)
        self.action_registry.actions["pfd.delete"].setEnabled(editable and bool(identifiers))

    def _on_input_text_edited(self) -> None:
        self.last_receipt = None
        if self.session:
            self.session.last_receipt = None
            self.session.validated_engineering_hash = None
            self.session._validated_pfd_hash = None
        if "run.start" in self.action_registry.actions:
            self.action_registry.actions["run.start"].setEnabled(False)

    def refresh_catalog(self) -> None:
        if not self.studio_ready:
            super().refresh_catalog()
            return
        super().refresh_catalog()
        cases = self.navigator.topLevelItem(0)
        if cases is not None:
            cases.setText(0, "Local cases")
            for index in range(cases.childCount()):
                item = cases.child(index)
                assert item is not None
                item.setText(
                    0,
                    item.text(0).removesuffix("  ·  r0")
                    + ("  ·  recovery only" if item.text(0).endswith("  ·  r0") else ""),
                )
        if self.document:
            root = QTreeWidgetItem(["Current flowsheet"])
            for obj in self.document.objects:
                item = QTreeWidgetItem([obj.tag])
                item.setData(0, Qt.ItemDataRole.UserRole, ("object", obj.object_id))
                root.addChild(item)
            self.navigator.addTopLevelItem(root)
            root.setExpanded(True)
        self.filter_browser(self.browser_search.text())

    def filter_browser(self, query: str) -> None:
        needle = query.casefold()
        for i in range(self.navigator.topLevelItemCount()):
            root = self.navigator.topLevelItem(i)
            assert root is not None
            visible_children = []
            for j in range(root.childCount()):
                item = root.child(j)
                assert item is not None
                visible_children.append(item)
                item.setHidden(
                    needle not in item.text(0).casefold() and needle not in root.text(0).casefold()
                )
            root.setHidden(all(item.isHidden() for item in visible_children))

    def _navigate(self, item: QTreeWidgetItem, column: int) -> None:
        value = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(value, tuple) and value[0] == "object":
            self.canvas.select_ids((str(value[1]),))
        else:
            super()._navigate(item, column)

    def layer_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        value = item.data(0, Qt.ItemDataRole.UserRole)
        if self.session and isinstance(value, tuple) and value[0] == "visual":
            self._remember_view()
            self.session.active_group = str(value[1])
            self.refresh()
        elif not self.studio_ready:
            super().layer_item_clicked(item, column)

    def isolate_visual_group(self) -> None:
        selected = self.selected_grouping()
        if self.session and selected and selected[0] == "visual":
            self.session.isolated_group = (
                None if self.session.isolated_group == selected[1] else selected[1]
            )
            self.refresh()

    def preview_selected(self) -> None:
        item = self.history_tree.currentItem()
        if item:
            self.preview_entry(str(item.data(0, Qt.ItemDataRole.UserRole)))

    def preview_entry(self, entry_id: str) -> None:
        if not self.flush_input_edits():
            return
        if not self.session:
            return
        self._remember_view()
        outcome = self.execute("history.view", self._target(entry_id=entry_id))
        if isinstance(outcome.data, c.HistoryState):
            self.session.preview = outcome.data
            self.refresh()
            self.review_context.setText(
                f"Read-only baseline: {entry_id}. HAZOP execution remains gated."
            )

    def return_current(self) -> None:
        if self.session:
            self.session.preview = None
            self.refresh()

    def branch_selected(self) -> None:
        if not self.session:
            return
        item = self.history_tree.currentItem()
        entry_id = (
            self.session.preview.entries[-1].entry_id
            if self.session.preview
            else (str(item.data(0, Qt.ItemDataRole.UserRole)) if item else "")
        )
        if not entry_id:
            return
        name, accepted = QInputDialog.getText(self, "Continue as alternative", "Alternative name")
        if accepted:
            outcome = self.execute("history.branch", self._target(entry_id=entry_id, name=name))
            if isinstance(outcome.data, c.HistoryState):
                self._adopt(outcome.data)

    def show_compare(self) -> None:
        self.compare_before.clear()
        self.compare_after.clear()
        listing = self.execute("history.list", c.ListDraftsParameters())
        if isinstance(listing.data, c.DraftListDto):
            for row in listing.data.drafts:
                outcome = self.execute("history.view", c.HistoryTarget(row.draft_id))
                if not isinstance(outcome.data, c.HistoryState):
                    continue
                for entry in outcome.data.entries:
                    if entry.saved_version or entry.snapshot:
                        name = (
                            entry.snapshot.name
                            if entry.snapshot
                            else (
                                f"r{entry.saved_version.revision}"
                                if entry.saved_version
                                else "checkpoint"
                            )
                        )
                        label = f"{row.draft_id} · {name} · {entry.branch.name}"
                        for combo in (self.compare_before, self.compare_after):
                            combo.addItem(label, (row.draft_id, entry.entry_id))
        if self.compare_after.count():
            self.compare_after.setCurrentIndex(self.compare_after.count() - 1)
        self.focus_panel(self.compare_dock, self.compare_before)

    def compare_versions(self) -> None:
        before, after = self.compare_before.currentData(), self.compare_after.currentData()
        if not before or not after:
            self.review_context.setText("Save two versions or create named snapshots to compare.")
            return
        outcome = self.execute(
            "history.compare",
            c.CompareHistoryParameters(
                c.HistoryTarget(before[0], entry_id=before[1]),
                c.HistoryTarget(after[0], entry_id=after[1]),
            ),
        )
        labels: dict[str, str] = {}
        units: list[dict[tuple[str, str], str]] = []
        for draft_id, entry_id in (before, after):
            view = self.execute("history.view", c.HistoryTarget(draft_id, entry_id=entry_id))
            quantity_units: dict[tuple[str, str], str] = {}
            if isinstance(view.data, c.HistoryState):
                labels.update({o.object_id: o.tag for o in view.data.document.objects})
                labels.update({g.group_id: g.name for g in view.data.document.visual_groups})
                labels.update(
                    {g.subsystem_id: g.name for g in view.data.document.engineering_subsystems}
                )
                quantity_units = {
                    (node.object_id, parameter.name): parameter.quantity.unit
                    for node in view.data.document.draft.equipment
                    for parameter in node.parameters
                }
            units.append(quantity_units)
        self.comparison.clear()
        if isinstance(outcome.data, c.HistoryComparison):
            for difference in outcome.data.differences:
                parts = difference.field.strip("/").split("/")[1:]
                title = " › ".join(labels.get(part, part.replace("_", " ")) for part in parts)
                values = [difference.before, difference.after]
                if (
                    len(parts) == 5
                    and parts[1] == "parameters"
                    and parts[-2:]
                    == [
                        "quantity",
                        "value",
                    ]
                ):
                    title = labels.get(parts[0], parts[0]) + " › " + parts[2].replace("_", " ")
                    values = [
                        value
                        + (" " + side[(parts[0], parts[2])] if (parts[0], parts[2]) in side else "")
                        for value, side in zip(values, units, strict=True)
                    ]
                item = QTreeWidgetItem([difference.category, title, *values])
                item.setToolTip(1, difference.field)
                self.comparison.addTopLevelItem(item)
            self.review_context.setText(
                f"{len(outcome.data.differences)} field differences · "
                "exact stored checkpoints · no calculations"
            )

    def apply_preset(self, name: str) -> None:
        if not self.studio_ready:
            return
        self.presets.blockSignals(True)
        self.presets.setCurrentText(name)
        self.presets.blockSignals(False)
        self.restore_default_layout()
        for dock in (self.palette_dock, self.layers_dock):
            dock.setFloating(False)
            self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
            self.tabifyDockWidget(self.navigator_dock, dock)
            dock.show()
        self.navigator_dock.raise_()
        for dock in (
            self.workbook_dock,
            self.graph_dock,
            self.history_dock,
            self.commands_dock,
            self.compare_dock,
        ):
            dock.setFloating(False)
            self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
            self.tabifyDockWidget(self.activity_dock, dock)
            dock.hide()
        self.activity_dock.hide()
        self.resizeDocks(
            [self.navigator_dock, self.inspector_dock], [260, 290], Qt.Orientation.Horizontal
        )
        if name == "Compare":
            self.show_compare()
        elif name == "Review":
            self.workbook_dock.show()
            self.workbook_dock.raise_()
            self.review_context.setText(
                "Choose a named snapshot as the review baseline. HAZOP execution remains gated."
            )
        self.workspace.settings.setValue("layout/preset", name)

    def restore_default_layout(self) -> None:
        super().restore_default_layout()
        if self.studio_ready:
            self.activity_dock.hide()

    def set_ribbon(self, enabled: bool) -> None:
        self.ribbon.setVisible(enabled)
        self.tools_bar.setVisible(not enabled)
        self.action_registry.actions["workspace.ribbon"].setChecked(enabled)
        self.workspace.settings.setValue("appearance/ribbon", enabled)

    def toggle_ribbon(self) -> None:
        self.set_ribbon(self.action_registry.actions["workspace.ribbon"].isChecked())

    def export_workspace(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export workspace template", "bh-workspace.json", "JSON (*.json)"
        )
        if not path:
            return
        try:
            Path(path).write_text(
                self.workspace.export_template(
                    self,
                    self.theme,
                    self.compact,
                    self.action_registry.overrides,
                    self.workspace.ribbon(),
                ),
                encoding="utf-8",
            )
        except OSError:
            self.note("Workspace template could not be written.")

    def apply_workspace_template(self, text: str) -> bool:
        """Apply all preferences atomically; corrupt layout or shortcuts retain prior state."""
        try:
            template = self.workspace.parse_template(text)
        except (ValueError, TypeError):
            self.note("Workspace template rejected; previous preferences retained.")
            return False
        prior = self.saveState(LAYOUT_VERSION)
        shortcuts = dict(self.action_registry.overrides)
        try:
            errors = self.action_registry.restore(
                {**self.default_bindings, **template["shortcuts"]}
            )
            if errors:
                raise ValueError("; ".join(errors))
            if not self.restoreState(template["layout"], LAYOUT_VERSION):
                raise ValueError("Invalid dock layout")
        except (ValueError, TypeError):
            self.restoreState(prior, LAYOUT_VERSION)
            self.action_registry.restore({**self.default_bindings, **shortcuts})
            self.note("Workspace template rejected; previous preferences retained.")
            return False
        self.theme, self.compact = template["theme"], template["compact"]
        self.action_registry.actions["workspace.compact"].setChecked(self.compact)
        self.set_ribbon(template["ribbon"])
        self.apply_appearance()
        return True

    def import_workspace(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Preview workspace template", "", "JSON (*.json)"
        )
        if not path:
            return
        try:
            with Path(path).open("r", encoding="utf-8") as handle:
                text = handle.read(100_001)
            value = self.workspace.parse_template(text)
            dialog = QDialog(self)
            dialog.setWindowTitle("Apply workspace template")
            layout = QVBoxLayout(dialog)
            preview = QPlainTextEdit()
            preview.setReadOnly(True)
            preview.setPlainText(
                json.dumps({k: v for k, v in value.items() if k != "layout"}, indent=2)
            )
            layout.addWidget(preview)
            buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Cancel
            )
            buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.apply_workspace_template(text)
        except (OSError, ValueError, TypeError):
            self.note("Workspace template is unreadable or invalid.")

    def export_image(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export visible flowsheet image", "flowsheet.png", "PNG (*.png)"
        )
        if path and not self.canvas.viewport().grab().save(path):
            self.note("Flowsheet image could not be written.")

    def _persist_navigation(self) -> None:
        """Personal views contain stable IDs only; recovery is not a named case save."""
        previous = self._navigation_values()
        for identifier, session in self.sessions.items():
            previous[identifier] = {
                "centre": list(session.centre),
                "scale": session.scale,
                "selection": list(session.selection),
                "group": session.active_group,
                "workspace": session.workspace,
            }
        self.workspace.settings.setValue("navigation/views", json.dumps(previous))
        self.workspace.settings.setValue("navigation/open", json.dumps(list(self.sessions)))
        self.workspace.settings.setValue("navigation/active", self.active_id or "")
        self.workspace.settings.sync()

    def _navigation_values(self) -> dict:
        try:
            value = json.loads(str(self.workspace.settings.value("navigation/views", "{}")))
            return value if isinstance(value, dict) else {}
        except ValueError:
            return {}

    def _restore_case_view(self, identifier: str) -> None:
        value = self._navigation_values().get(identifier, {})
        session = self.sessions[identifier]
        try:
            centre = value["centre"]
            scale = value["scale"]
            if (
                len(centre) != 2
                or not all(type(v) in (int, float) and abs(v) < 1e9 for v in centre)
                or not 0.1 <= scale <= 4
            ):
                return
            session.centre, session.scale = (float(centre[0]), float(centre[1])), scale
            session.selection = tuple(v for v in value["selection"] if isinstance(v, str))
            session.active_group = (
                value.get("group") if isinstance(value.get("group"), str) else None
            )
            self.canvas.setTransform(QTransform.fromScale(scale, scale))
            self.canvas.centerOn(*session.centre)
            self.canvas.select_ids(session.selection)
        except (KeyError, TypeError, ValueError):
            return

    def _restore_sessions(self) -> None:
        try:
            identifiers = json.loads(str(self.workspace.settings.value("navigation/open", "[]")))
            active = str(self.workspace.settings.value("navigation/active", ""))
            views = self.workspace.settings.value("navigation/views", "{}")
            if isinstance(identifiers, list):
                for identifier in identifiers[:30]:
                    if isinstance(identifier, str):
                        self.open_draft(identifier)
                        self.workspace.settings.setValue("navigation/views", views)
                        if identifier in self.sessions:
                            self._restore_case_view(identifier)
            if active in self.sessions:
                self.open_draft(active)
        except (ValueError, TypeError):
            self.note("Personal navigation preferences could not be restored.")

    def closeEvent(self, event: QCloseEvent) -> None:
        """Every committed edit is durable; closing never discards recovery or runs work."""
        if not self.studio_ready:
            super().closeEvent(event)
            return
        if not self.flush_input_edits():
            event.ignore()
            return
        self._remember_view()
        self._persist_navigation()
        self.workspace.settings.setValue("commands/recall", json.dumps(self.console.history))
        if not self.workspace.save(self, self.theme, self.compact, self.action_registry.overrides):
            QMessageBox.warning(
                self,
                "Layout not saved",
                "Workspace preferences could not be saved. Editing history remains durable.",
            )
        event.accept()

    def about(self) -> None:
        QMessageBox.about(
            self,
            "BH solver",
            "BH solver · DW3.2 native editor\n\n"
            "Local recovery, persistent history and native editing are available.\n"
            "Worker/results, HAZOP and live collaboration remain gated.\n\n"
            "Concept development only. No industrial or safety qualification.",
        )

    def _resolve_tag(self, tag: str) -> str:
        if not self.document:
            raise ValueError("Open a case first")
        matches = [
            o.object_id
            for o in self.document.objects
            if tag.casefold() in (o.tag.casefold(), o.object_id.casefold())
        ]
        if len(matches) != 1:
            raise ValueError("Object name is missing or ambiguous; use its stable ID")
        return matches[0]

    def run_command(self, text: str) -> str:
        """Parse a closed grammar and use the same handlers, units and confirmations."""
        help_text = (
            "select <tag> | add <model> | rename <tag> <new-tag> | delete <tag>\n"
            "connect <source> <output-port> <target> <input-port>\n"
            "set <tag> <input> <value> <unit> | snapshot <name>\n"
            "save | undo | redo | fit | history | compare | help\n"
            "Quote names containing spaces. Values are submitted inputs, never calculations."
        )
        try:
            parts = shlex.split(text)
            if not parts or len(text) > 4096:
                raise ValueError("Use a command of at most 4096 characters")
            command, args = parts[0].lower(), parts[1:]
            if command == "help":
                return help_text
            aliases = {
                "save": "draft.save",
                "undo": "pfd.undo",
                "redo": "pfd.redo",
                "fit": "pfd.fit",
                "history": "view.history",
                "compare": "view.compare",
            }
            if not args and (command in aliases or command in self.action_registry.actions):
                action = self.action_registry.actions[aliases.get(command, command)]
                if not action.isEnabled():
                    return "Unavailable: " + action.toolTip()
                action.trigger()
                return "Command submitted: " + action.text().replace("&", "")
            if command == "select" and len(args) == 1:
                self.canvas.select_ids((self._resolve_tag(args[0]),))
                return "Selected " + args[0]
            if command == "snapshot" and args:
                return (
                    "Snapshot recorded"
                    if self.snapshot_named(" ".join(args))
                    else "Snapshot not recorded; see diagnostics"
                )
            if command == "add" and len(args) == 1:
                index = next(
                    (i for i, m in enumerate(self.catalogue.models) if m.model_id == args[0]), None
                )
                if index is None:
                    raise ValueError("Unknown equipment model")
                self.equipment_palette.setCurrentRow(index)
                self.add_equipment()
            elif command == "rename" and len(args) == 2:
                self.canvas.select_ids((self._resolve_tag(args[0]),))
                self.rename_selected(args[1])
            elif command == "delete" and len(args) == 1:
                self.canvas.select_ids((self._resolve_tag(args[0]),))
                self.delete_selection()
            elif command == "connect" and len(args) == 4:
                if not self.apply_edit(
                    c.ConnectPortsEdit(
                        self._resolve_tag(args[0]), args[1], self._resolve_tag(args[2]), args[3]
                    )
                ):
                    return "Connection rejected; see diagnostics"
            elif command == "set" and len(args) == 4:
                if not self.apply_edit(
                    c.ConfigureInputEdit(self._resolve_tag(args[0]), args[1], args[2], args[3])
                ):
                    return "Input rejected; see diagnostics"
            else:
                raise ValueError("Unknown command or argument count. " + help_text)
            return "Command handled; cancelled or rejected changes remain unchanged."
        except (ValueError, StopIteration) as error:
            return "Command rejected: " + str(error)

    def complete_command(self, text: str) -> list[str]:
        """Complete names/arguments from the neutral catalogue; never infer a quantity."""
        names = [
            "select",
            "add",
            "rename",
            "delete",
            "connect",
            "set",
            "snapshot",
            "save",
            "undo",
            "redo",
            "fit",
            "history",
            "compare",
            "help",
        ]
        if " " not in text:
            return [n for n in (*names, *self.action_registry.actions) if n.startswith(text)]
        try:
            tokens = shlex.split(text)
        except ValueError:
            return []
        if text.endswith(" "):
            tokens.append("")
        if not tokens:
            return names
        command, position = tokens[0], len(tokens) - 1
        choices: list[str] = []
        if command == "add" and position == 1:
            choices = [m.model_id for m in self.catalogue.models]
        elif self.document:
            if (
                position == 1
                and command in {"select", "rename", "delete", "set", "connect"}
                or command == "connect"
                and position == 3
            ):
                choices = [o.tag for o in self.document.objects]
            elif command == "set" and position == 4:
                try:
                    identifier = self._resolve_tag(tokens[1])
                    node = next(
                        n for n in self.document.draft.equipment if n.object_id == identifier
                    )
                    model = next(m for m in self.catalogue.models if m.model_id == node.model_id)
                    parameter = next(p for p in model.parameters if p.name == tokens[2])
                    choices = [
                        parameter.canonical_unit,
                        *[p.quantity.unit for p in node.parameters if p.name == parameter.name],
                        *[
                            u.display_unit
                            for u in self.document.settings.units
                            if u.canonical_unit == parameter.canonical_unit
                        ],
                    ]
                except (ValueError, StopIteration):
                    pass
            elif command in {"set", "connect"} and position in (2, 4):
                try:
                    identifier = self._resolve_tag(tokens[1] if position == 2 else tokens[3])
                    node = next(
                        n for n in self.document.draft.equipment if n.object_id == identifier
                    )
                    model = next(m for m in self.catalogue.models if m.model_id == node.model_id)
                    choices = (
                        [p.name for p in model.parameters]
                        if command == "set"
                        else [
                            p.name
                            for p in model.ports
                            if p.direction == ("output" if position == 2 else "input")
                        ]
                    )
                except (ValueError, StopIteration):
                    pass
        prefix = " ".join(shlex.quote(t) for t in tokens[:-1]) + " "
        return [
            prefix + shlex.quote(choice)
            for choice in choices
            if choice.casefold().startswith(tokens[-1].casefold())
        ]

    def _on_workbook_unit_selected(self, unit_id: str) -> None:
        raw_id = unit_id.removeprefix("unit:")
        self.canvas.select_ids((raw_id,))

    def _on_workbook_stream_selected(self, stream_id: str) -> None:
        raw_id = stream_id.removeprefix("connection:")
        self.canvas.select_ids((raw_id,))

    def _on_inspector_plot_clicked(self) -> None:
        selected = self.canvas.selected_ids()
        if selected:
            self.plot_object(selected[0])
        else:
            self.note("Select an equipment or stream to plot.")

    def validate_current(self) -> bool:
        """Compile current inputs without saving, recording verified hashes for active session."""
        if not self.flush_input_edits():
            return False
        if self.current is None:
            return False
        outcome = self.execute("draft.validate", c.DraftParameters(self.current))
        if outcome.disposition == "COMPLETED" and isinstance(outcome.data, c.ValidationReceiptDto):
            self.last_receipt = outcome.data
            if self.session and self.document:
                self.session.last_receipt = outcome.data
                self.session.validated_engineering_hash = outcome.data.engineering_hash
                self.session._validated_pfd_hash = c.pfd_engineering_content_hash(self.document)
            if outcome.data.validation.valid:
                dof = outcome.data.validation.degrees_of_freedom
                msg = f"Validated · DOF: {dof} · Ready to run"
                self.scientific_status.setText(msg)
                self.note(f"Validation successful (DOF: {dof}).")
            else:
                diag_count = len(outcome.data.validation.diagnostics)
                first_msg = (
                    outcome.data.validation.diagnostics[0].message
                    if diag_count
                    else "Validation failed"
                )
                msg = f"Validation failed ({diag_count} issues) · {first_msg}"
                self.scientific_status.setText(msg)
                self.note(f"Validation failed: {first_msg}")
            self.refresh()
            return outcome.data.validation.valid
        elif self.session:
            self.session.last_receipt = None
            self.session.validated_engineering_hash = None
            self.session._validated_pfd_hash = None
            self.last_receipt = None
            self.refresh()
        return False

    def _check_receipt_engineering_identity(self) -> bool:
        """Verify current engineering content hash against last receipt."""
        if self.pending_inputs:
            return False
        if hasattr(self, "input_panel") and self.input_panel is not None:
            for field in self.input_panel.findChildren(QLineEdit):
                if field.isModified():
                    return False
        if self.session is not None and self.document is not None:
            if self.session._validated_pfd_hash is None:
                return False
            current_hash = c.pfd_engineering_content_hash(self.document)
            if self.session._validated_pfd_hash != current_hash:
                return False
        return True

    @staticmethod
    def _is_valid_run(view: c.RunViewDto) -> bool:
        """Evaluate full four-status scientific validity predicate."""
        return (
            view.convergence == "CONVERGED"
            and view.closure == "PASSED"
            and view.physical_validity == "VALID"
            and view.correlation_validity in ("VALID", "EXTRAPOLATED")
        )

    def run_current(self) -> bool:
        """Execute solver, routing results to originating case and retaining valid overlays."""
        if not self.flush_input_edits():
            return False
        if self.current is None:
            return False
        if not self.has_valid_receipt():
            self.note("Validation required before running flowsheet.")
            return False

        originating_id = self.active_id
        if originating_id is None:
            return False
        target_session = self.sessions.get(originating_id)
        if target_session is None:
            return False

        assert self.last_receipt is not None
        receipt = self.last_receipt
        draft = self.current
        source_hash = c.pfd_engineering_content_hash(target_session.state.document)

        self.active_run_id = "run:in-flight"
        self.scientific_status.setText("Solving in child worker process…")
        self.refresh()

        outcome_box: list[c.CommandOutcome] = []
        request = c.CommandRequest(
            "run.start",
            f"ui:{uuid4()}",
            self.workspace.actor_id(),
            c.StartRunParameters(draft, receipt.receipt_id),
        )

        def _worker() -> None:
            res = self.gateway.dispatch(request)
            outcome_box.append(res)

        thread = threading.Thread(target=_worker, daemon=True, name="WorkstationRunThread")
        thread.start()
        while thread.is_alive():
            app = QApplication.instance()
            if app is not None:
                app.processEvents()
            thread.join(timeout=0.02)

        self.active_run_id = None
        outcome = outcome_box[0] if outcome_box else None
        self.last_outcome = outcome

        if (
            outcome is not None
            and outcome.disposition == "COMPLETED"
            and isinstance(outcome.data, c.RunViewDto)
        ):
            run_view = outcome.data
            target_session.run_source_hashes[run_view.run_id] = source_hash
            target_session.last_run_view = run_view
            target_session.selected_run_id = run_view.run_id
            self.load_run_results(run_view.run_id, case_id=originating_id)

            is_valid = self._is_valid_run(run_view)
            if is_valid:
                target_session.last_valid_run_view = run_view
                target_session.last_valid_workbook = target_session.workbook
                target_session.last_valid_overlays = target_session.overlays
                if self.active_id == originating_id:
                    self.canvas.set_overlays(target_session.overlays)
                    if target_session.workbook:
                        self.workbook_view.set_workbook(
                            target_session.workbook,
                            is_stale=self._result_is_stale(target_session, run_view.run_id),
                        )
            else:
                target_session.overlays = target_session.last_valid_overlays
                if self.active_id == originating_id:
                    self.canvas.set_overlays(target_session.last_valid_overlays)
                    if target_session.workbook:
                        self.workbook_view.set_workbook(
                            target_session.workbook,
                            is_stale=self._result_is_stale(target_session, run_view.run_id),
                        )

            if self.active_id == originating_id:
                self.last_run_view = run_view
                status_text = (
                    f"Run: {run_view.run_id} | "
                    f"Convergence: {run_view.convergence.lower()} | "
                    f"Closure: {run_view.closure.lower()} | "
                    f"Physical: {run_view.physical_validity.lower()} | "
                    f"Correlation: {run_view.correlation_validity.lower()}"
                )
                if not is_valid:
                    status_text += " · Retaining last valid flowsheet overlays"
                self.scientific_status.setText(status_text)
                self.note(
                    f"Run completed: {run_view.convergence.lower()}."
                    if is_valid
                    else "Run completed with scientific deficits; retaining last valid overlays."
                )
            else:
                self.last_run_view = self.session.last_run_view if self.session else None
                self.last_receipt = self.session.last_receipt if self.session else None

            self.refresh()
            return True
        elif outcome is not None and outcome.disposition == "REJECTED":
            message = "; ".join(f"{item.code}: {item.message}" for item in outcome.diagnostics)
            self.scientific_status.setText(f"Run failed · {message}")
            self.note(f"Run failed: {message}")
            self.activity_dock.show()
            self.statusBar().showMessage(message, 15000)
            self.refresh()
            return False

        self.refresh()
        return False

    def load_run_results(self, run_id: str, case_id: str | None = None) -> None:
        """Query workbook and overlays for the completed run and populate UI."""
        target_case_id = (
            case_id or self.active_id or (self.current.draft_id if self.current else "")
        )
        session = self.sessions.get(target_case_id) if target_case_id else self.session
        if not session:
            return
        session.selected_run_id = run_id

        outcome_wb = self.execute(
            "workbook.inspect", c.InspectWorkbookParameters(case_id=target_case_id, run_id=run_id)
        )
        if outcome_wb.disposition == "COMPLETED" and isinstance(outcome_wb.data, c.WorkbookDto):
            session.workbook = outcome_wb.data
            if self.active_id == target_case_id:
                self.workbook_view.set_workbook(
                    outcome_wb.data, is_stale=self._result_is_stale(session, run_id)
                )

        outcome_ov = self.execute(
            "result.overlays", c.GetOverlaysParameters(case_id=target_case_id, run_id=run_id)
        )
        if outcome_ov.disposition == "COMPLETED" and isinstance(outcome_ov.data, c.OverlaysDto):
            is_valid = session.last_run_view is not None and self._is_valid_run(
                session.last_run_view
            )
            if is_valid:
                session.overlays = outcome_ov.data
                if self.active_id == target_case_id:
                    self.canvas.set_overlays(outcome_ov.data)
            else:
                session.overlays = session.last_valid_overlays
                if self.active_id == target_case_id:
                    self.canvas.set_overlays(session.last_valid_overlays)

    def plot_object(self, object_id: str, run_id: str | None = None) -> None:
        """Fetch and display plot data for a stream or unit in the graph dock."""
        case_id = self.active_id or (self.current.draft_id if self.current else "")
        target_run_id = run_id or (self.session.selected_run_id if self.session else None)
        if not target_run_id and self.last_run_view:
            target_run_id = self.last_run_view.run_id
        if not target_run_id:
            self.note("No run artifact available to plot.")
            return

        outcome = self.execute(
            "graph.plot",
            c.PlotDataParameters(case_id=case_id, run_id=target_run_id, unit_id=object_id),
        )
        if outcome.disposition == "COMPLETED" and isinstance(outcome.data, c.PlotDefinitionDto):
            plot_def = outcome.data
            if self.session:
                self.session.active_plot = plot_def
            self.graph_viewer.set_plot(plot_def)
            self.graph_dock.show()
            self.graph_dock.raise_()
        else:
            msg = "; ".join(d.message for d in outcome.diagnostics) or "Plot data not available"
            self.note(f"Cannot plot {object_id}: {msg}")

    def open_graph_window(self, plot_def: c.PlotDefinitionDto | None = None) -> GraphDialog | None:
        """Spawn an independent floating non-modal GraphDialog."""
        active_plot = (
            plot_def
            or (self.session.active_plot if self.session else None)
            or self.graph_viewer.plot_canvas.plot_def
        )
        if not active_plot:
            self.note("No plot data available to open in window.")
            return None

        dialog = GraphDialog(active_plot, self)
        dialog.show()
        self._floating_graphs.append(dialog)
        dialog.finished.connect(
            lambda: (
                self._floating_graphs.remove(dialog) if dialog in self._floating_graphs else None
            )
        )
        return dialog

    def toggle_canvas_overlays(self) -> None:
        """Toggle visibility of PFD canvas stream and equipment result overlays."""
        visible = self.canvas.toggle_overlays()
        self.note(f"Canvas result overlays: {'Visible' if visible else 'Hidden'}")
