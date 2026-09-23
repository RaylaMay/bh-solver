"""Native editor orchestration through the shared neutral command gateway.

Selection, undo history and input focus belong here. All document mutations and
quantity conversion are application commands; no calculation is performed by Qt.
"""

from __future__ import annotations

import json
from dataclasses import replace
from uuid import uuid4

from PySide6.QtCore import QMimeData, QPoint, Qt, QTimer
from PySide6.QtGui import QColor, QDrag, QFocusEvent, QKeySequence, QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidgetItem,
    QToolBar,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from bh_sim.boundary import contracts as c
from bh_sim.boundary.json_codec import boundary_from_json, boundary_json
from bh_sim.boundary.ports import CommandGateway

from .pfd_canvas import PfdCanvas
from .pfd_settings import PfdSettingsDialog
from .window import WorkstationWindow
from .workspace import WorkspaceSettings


class QuantityInput(QLineEdit):
    """Show submitted notation on focus; unchanged focus/blur never emits an edit."""

    def __init__(self, displayed: str, original: str, original_on_edit: bool) -> None:
        super().__init__(displayed)
        self.displayed, self.original = displayed, original
        self.original_on_edit = original_on_edit
        self.setPlaceholderText("Input required")

    def focusInEvent(self, event: QFocusEvent) -> None:
        if self.original_on_edit:
            self.setText(self.original)
        self.setModified(False)
        super().focusInEvent(event)

    def focusOutEvent(self, event: QFocusEvent) -> None:
        modified = self.isModified()
        super().focusOutEvent(event)
        if not modified:
            self.setText(self.displayed)


class EquipmentPaletteList(QListWidget):
    """Equipment palette supporting keyboard activation and drag-and-drop onto the PFD canvas."""

    MIME_TYPE = "application/vnd.bh.equipment-model+json"

    def __init__(self, catalogue: c.PfdCatalogueDto, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.catalogue = catalogue
        self.setAccessibleName("Equipment palette; drag onto canvas or activate to add equipment")
        self.setDragEnabled(True)
        self.drag_start_pos: QPoint | None = None
        self.populate(catalogue)

    def populate(self, catalogue: c.PfdCatalogueDto) -> None:
        self.catalogue = catalogue
        self.clear()
        for model in catalogue.models:
            item = QListWidgetItem(model.title)
            item.setData(Qt.ItemDataRole.UserRole, model.model_id)
            self.addItem(item)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not (event.buttons() & Qt.MouseButton.LeftButton) or self.drag_start_pos is None:
            super().mouseMoveEvent(event)
            return
        distance = (event.position().toPoint() - self.drag_start_pos).manhattanLength()
        if distance < QApplication.startDragDistance():
            super().mouseMoveEvent(event)
            return
        item = self.itemAt(self.drag_start_pos)
        if item is None:
            super().mouseMoveEvent(event)
            return
        model_id = item.data(Qt.ItemDataRole.UserRole)
        model = next((m for m in self.catalogue.models if m.model_id == model_id), None)
        if model is None:
            super().mouseMoveEvent(event)
            return
        payload = json.dumps(
            {
                "model_id": model.model_id,
                "title": model.title,
                "version": "1.0",
            }
        ).encode("utf-8")
        mime = QMimeData()
        mime.setData(self.MIME_TYPE, payload)
        mime.setText(model.title)
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)


class PfdEditorWindow(WorkstationWindow):
    """DW3 native document workspace; retains the independently testable DW2 shell."""

    def __init__(self, gateway: CommandGateway, settings: WorkspaceSettings) -> None:
        self.document: c.PfdDocumentDto | None = None
        self.catalogue = c.PfdCatalogueDto(())
        self.undo_documents: list[c.PfdDocumentDto] = []
        self.redo_documents: list[c.PfdDocumentDto] = []
        self.ready = False
        self.loading_layers = False
        super().__init__(gateway, settings)
        outcome = self.execute("pfd.catalog", c.ListDraftsParameters())
        if isinstance(outcome.data, c.PfdCatalogueDto):
            self.catalogue = outcome.data
        self.canvas = self.create_canvas()
        self.canvas.edit_requested.connect(self.apply_edit)
        self.canvas.selection_changed.connect(self.inspect_ids)
        self.canvas.legend_changed.connect(self.update_layer_legend)
        self.canvas.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.canvas.customContextMenuRequested.connect(self.context_menu)
        page = self.pages.widget(1)
        assert page is not None
        layout = page.layout()
        assert isinstance(layout, QVBoxLayout)
        self.workspace_switcher = QWidget()
        switch_layout = QHBoxLayout(self.workspace_switcher)
        switch_layout.setContentsMargins(0, 0, 0, 0)
        switch_layout.addWidget(QLabel("Workspace"))
        self.workspace_buttons: dict[str, QPushButton] = {}
        for name, enabled, explanation in (
            ("Flowsheet", True, "Editable PFD document"),
            ("Dynamics", False, "Unavailable: dynamic document and M7 engine are not implemented"),
            ("Controls", False, "Unavailable: control persistence and M7/M9 engine gates remain"),
        ):
            button = QPushButton(name)
            button.setCheckable(True)
            button.setChecked(name == "Flowsheet")
            button.setEnabled(enabled)
            button.setToolTip(explanation)
            button.setAccessibleDescription(explanation)
            switch_layout.addWidget(button)
            self.workspace_buttons[name.lower()] = button
        switch_layout.addStretch()
        layout.insertWidget(4, self.workspace_switcher)
        layout.insertWidget(5, self.canvas, 4)
        self.equipment.setAccessibleName("Equipment and streams in the current draft")
        self.equipment.setMaximumHeight(120)
        self.equipment.setSelectionMode(self.equipment.SelectionMode.ExtendedSelection)
        self.equipment_palette = EquipmentPaletteList(self.catalogue)
        self.equipment_palette.itemActivated.connect(lambda _item: self.add_equipment())
        self.palette_dock = self._dock(
            "Equipment palette · test fixtures", "equipment-palette", self.equipment_palette
        )
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.palette_dock)
        self.tabifyDockWidget(self.navigator_dock, self.palette_dock)
        self.palette_dock.raise_()
        self._build_layers_dock()
        self.input_panel = QWidget()
        self.input_form = QFormLayout(self.input_panel)
        inspector = self.inspector_dock.widget()
        assert inspector is not None
        inspector_layout = inspector.layout()
        assert inspector_layout is not None
        self.parameters.hide()
        for caption in inspector.findChildren(QLabel):
            if "Inputs shown as submitted" in caption.text():
                caption.setText(
                    "Display units follow case preferences. Editing reveals submitted notation."
                )
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.input_panel)
        inspector_layout.addWidget(scroll)
        add = self.action_registry.add
        standard = QKeySequence.StandardKey
        for name, title, callback, shortcut in (
            ("pfd.focus", "Focus PFD canvas", self.canvas.setFocus, "Ctrl+4"),
            ("pfd.route_adjust", "Adjust route segment…", self.adjust_route, ""),
            ("pfd.zoom_reset", "100% zoom", self.canvas.resetTransform, "Ctrl+0"),
            ("pfd.fit", "Fit flowsheet", self.fit_flowsheet, "Ctrl+Shift+F"),
            ("pfd.add", "Add selected equipment", self.add_equipment, "Ctrl+Shift+A"),
            ("pfd.connect", "Connect typed ports…", self.connect_dialog, "Ctrl+L"),
            ("pfd.rename", "Rename selected object…", self.rename_dialog, "F2"),
            ("pfd.delete", "Delete selection…", self.delete_selection, "Backspace"),
            ("pfd.undo", "Undo edit", self.undo, QKeySequence(standard.Undo)),
            ("pfd.redo", "Redo edit", self.redo, QKeySequence(standard.Redo)),
            ("pfd.copy", "Copy equipment", self.copy_selection, QKeySequence(standard.Copy)),
            (
                "pfd.paste",
                "Paste equipment and parameters",
                self.paste,
                QKeySequence(standard.Paste),
            ),
            (
                "pfd.paste_connected",
                "Paste with internal connections",
                lambda: self.paste(connections=True),
                "",
            ),
            (
                "pfd.paste_defaults",
                "Paste equipment with unset inputs",
                lambda: self.paste(reset=True),
                "",
            ),
            ("pfd.route_reset", "Reset automatic route", self.reset_route, ""),
            ("pfd.details", "Expand/collapse details", self.toggle_details, ""),
            ("pfd.pin", "Pin/unpin details", lambda: self.toggle_details(pin=True), ""),
            ("pfd.groups", "Show visual groups", self.show_layers_dock, ""),
            ("pfd.layers", "Show PFD layers", self.show_layers_dock, ""),
            ("pfd.settings", "PFD settings and templates…", self.settings_dialog, ""),
        ):
            add(
                name,
                title,
                callback,
                shortcut if isinstance(shortcut, QKeySequence) else QKeySequence(shortcut),
            )
        menu = self.menuBar().addMenu("&Edit PFD")
        for name in self.action_registry.actions:
            if name.startswith("pfd."):
                menu.addAction(self.action_registry.actions[name])
        self.action_registry.register_existing(
            "view.layers_groups", self.layers_dock.toggleViewAction()
        )
        for action in self.menuBar().actions():
            view_menu = action.menu()
            if action.text().replace("&", "") == "View" and isinstance(view_menu, QMenu):
                view_menu.addAction(self.layers_dock.toggleViewAction())
        toolbar = QToolBar("PFD editing", self)
        toolbar.setObjectName("pfd-editing-toolbar")
        toolbar.setMovable(False)
        for name, short_title in (
            ("pfd.focus", "Select"),
            ("pfd.connect", "Connect"),
            ("pfd.rename", "Rename"),
            ("pfd.delete", "Delete"),
            ("pfd.undo", "Undo"),
            ("pfd.redo", "Redo"),
            ("pfd.fit", "Fit"),
            ("pfd.zoom_reset", "100%"),
            ("pfd.groups", "Groups"),
            ("pfd.layers", "Layers"),
            ("pfd.settings", "Settings"),
        ):
            button = QToolButton(toolbar)
            action = self.action_registry.actions[name]
            button.setText(short_title)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            button.setToolTip(action.text())
            button.setAccessibleName(action.text().replace("&", ""))
            button.setEnabled(action.isEnabled())
            button.clicked.connect(action.trigger)
            action.changed.connect(
                lambda action=action, button=button: button.setEnabled(action.isEnabled())
            )
            toolbar.addWidget(button)
        self.addToolBarBreak(Qt.ToolBarArea.TopToolBarArea)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)
        self.action_registry.restore(settings.shortcuts())
        self.default_bindings = {
            key: action.shortcut().toString(QKeySequence.SequenceFormat.PortableText)
            for key, action in self.action_registry.actions.items()
        }
        for caption in self.pages.findChildren(QLabel):
            if "The flowsheet canvas and calculation services" in caption.text():
                caption.setText(
                    "The native flowsheet editor is available. Calculation services "
                    "await the worker stage; no engineering results are generated here."
                )
        self.ready = True
        self.refresh()
        self.note(
            "Native PFD editor ready. Catalogue models remain test fixtures; "
            "Validate and Run await DW4."
        )

    def create_canvas(self) -> PfdCanvas:
        """Construct the presentation canvas; measurement harnesses may instrument painting."""
        return PfdCanvas()

    def _build_layers_dock(self) -> None:
        """Create persistent presentation controls and explicit engineering group actions."""

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        self.layers_tree = QTreeWidget()
        self.layers_tree.setHeaderLabels(["Layers & groups", "State"])
        self.layers_tree.setMinimumHeight(220)
        self.layers_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.layers_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.layers_tree.setColumnWidth(1, 100)
        self.layers_tree.setAccessibleName("PFD layers, visual groups, and engineering subsystems")
        self.layers_tree.itemClicked.connect(self.layer_item_clicked)
        self.layers_tree.itemChanged.connect(self.layer_item_changed)
        layout.addWidget(self.layers_tree, 1)

        base_form = QFormLayout()
        self.base_colour_button = QPushButton("Choose…")
        self.base_colour_button.clicked.connect(self.choose_stream_colour)
        self.labels_check = QCheckBox("Show")
        self.labels_check.toggled.connect(lambda _checked: self.apply_layer_controls())
        self.line_style_combo = QComboBox()
        self.line_style_combo.addItems(("solid", "dash", "dot"))
        self.line_style_combo.currentTextChanged.connect(lambda _value: self.apply_layer_controls())
        self.line_width_spin = QDoubleSpinBox()
        self.line_width_spin.setRange(0.5, 12.0)
        self.line_width_spin.setSingleStep(0.5)
        self.line_width_spin.valueChanged.connect(lambda _value: self.apply_layer_controls())
        base_form.addRow("Stream colour", self.base_colour_button)
        base_form.addRow("Labels", self.labels_check)
        base_form.addRow("Line style", self.line_style_combo)
        base_form.addRow("Line width", self.line_width_spin)
        layout.addLayout(base_form)

        group_actions = QGridLayout()
        for title, callback in (
            ("New group", self.create_visual_group),
            ("New subsystem", self.create_engineering_subsystem),
            ("Select members", self.select_group_members),
            ("Isolate", self.isolate_visual_group),
            ("Remove", self.remove_grouping),
        ):
            button = QPushButton(title)
            button.clicked.connect(callback)
            index = group_actions.count()
            group_actions.addWidget(button, index, 0)
        layout.addLayout(group_actions)

        motion_form = QFormLayout()
        self.animation_combo = QComboBox()
        for label_text, fps in (
            ("Off", 0),
            ("15 fps", 15),
            ("30 fps", 30),
            ("60 fps · exploratory", 60),
        ):
            self.animation_combo.addItem(label_text, fps)
        self.animation_combo.currentIndexChanged.connect(lambda _index: self.apply_layer_controls())
        self.animation_speed = QDoubleSpinBox()
        self.animation_speed.setRange(0.1, 10.0)
        self.animation_speed.setSingleStep(0.1)
        self.animation_speed.valueChanged.connect(lambda _value: self.apply_layer_controls())
        self.reduced_motion = QCheckBox("Pause moving markers")
        self.reduced_motion.toggled.connect(lambda _checked: self.apply_layer_controls())
        motion_form.addRow("Motion", self.animation_combo)
        motion_form.addRow("Speed scale", self.animation_speed)
        motion_form.addRow("Reduced motion", self.reduced_motion)
        layout.addLayout(motion_form)
        self.layer_legend = QLabel("Static direction arrows · no run artifact selected")
        self.layer_legend.setWordWrap(True)
        layout.addWidget(self.layer_legend)
        outer = QWidget()
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(panel)
        outer_layout.addWidget(scroll)
        self.layers_dock = self._dock("Layers && Groups", "layers-groups-dock", outer)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.layers_dock)
        self.tabifyDockWidget(self.navigator_dock, self.layers_dock)

    def update_layer_legend(self, text: str) -> None:
        self.layer_legend.setText(text)

    def show_layers_dock(self) -> None:
        self.layers_dock.show()
        self.layers_dock.raise_()
        self.layers_tree.setFocus()

    def refresh_layers(self) -> None:
        """Render grouping identity and layer availability without changing the document."""

        self.loading_layers = True
        self.layers_tree.clear()
        base = QTreeWidgetItem(["Base appearance", "Presentation"])
        visual = QTreeWidgetItem(["Visual groups", "Presentation"])
        engineering = QTreeWidgetItem(["Engineering subsystems", "Hash-affecting"])
        results = QTreeWidgetItem(["Result layers", "Artifact required"])
        motion = QTreeWidgetItem(["Motion", "Artifact required"])
        self.layers_tree.addTopLevelItems((base, visual, engineering, results, motion))
        for name in ("Temperature", "Pressure", "Mass flow", "Duty", "Validity"):
            item = QTreeWidgetItem([name, "Unavailable before DW4/DW5"])
            item.setDisabled(True)
            item.setToolTip(0, "Requires an attributable run artifact or telemetry frame")
            results.addChild(item)
        if self.document is not None:
            for group in sorted(self.document.visual_groups, key=lambda item: item.order):
                item = QTreeWidgetItem([group.name, f"{len(group.member_stream_ids)} streams"])
                item.setData(0, Qt.ItemDataRole.UserRole, ("visual", group.group_id))
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(
                    0, Qt.CheckState.Checked if group.visible else Qt.CheckState.Unchecked
                )
                item.setToolTip(
                    0, "Click to highlight; use Select members for engineering selection"
                )
                visual.addChild(item)
                if group.group_id == self.document.layer_preferences.active_visual_group_id:
                    self.layers_tree.setCurrentItem(item)
            for subsystem in self.document.engineering_subsystems:
                item = QTreeWidgetItem(
                    [subsystem.name, f"{len(subsystem.member_object_ids)} objects"]
                )
                item.setData(0, Qt.ItemDataRole.UserRole, ("engineering", subsystem.subsystem_id))
                item.setToolTip(0, subsystem.purpose or "Engineering grouping")
                engineering.addChild(item)
            prefs = self.document.layer_preferences
            self.base_colour_button.setStyleSheet(
                f"background-color: {prefs.base_stream_colour}; color: #111111"
            )
            self.base_colour_button.setProperty("selected-colour", prefs.base_stream_colour)
            self.labels_check.setChecked(prefs.show_labels)
            self.line_style_combo.setCurrentText(prefs.line_style)
            self.line_width_spin.setValue(prefs.line_width)
            index = self.animation_combo.findData(prefs.animation_fps)
            self.animation_combo.setCurrentIndex(max(0, index))
            self.animation_speed.setValue(prefs.animation_speed_scale)
            self.reduced_motion.setChecked(prefs.reduced_motion)
            motion.setText(
                1,
                "Reduced motion"
                if prefs.reduced_motion
                else f"{prefs.animation_fps} fps preference",
            )
        for item in (base, visual, engineering, results, motion):
            item.setExpanded(True)
        self.loading_layers = False

    def apply_layer_controls(self) -> None:
        if self.loading_layers or self.document is None:
            return
        current = self.document.layer_preferences
        colour = str(
            self.base_colour_button.property("selected-colour") or current.base_stream_colour
        )
        preferences = replace(
            current,
            base_stream_colour=colour,
            show_labels=self.labels_check.isChecked(),
            line_style=self.line_style_combo.currentText(),
            line_width=self.line_width_spin.value(),
            animation_fps=int(self.animation_combo.currentData()),
            animation_speed_scale=self.animation_speed.value(),
            reduced_motion=self.reduced_motion.isChecked(),
        )
        if preferences != current:
            self.apply_edit(c.SetPfdLayerPreferencesEdit(preferences))

    def choose_stream_colour(self) -> None:
        if self.document is None:
            return
        colour = QColorDialog.getColor(
            QColor(self.document.layer_preferences.base_stream_colour), self, "Stream colour"
        )
        if colour.isValid():
            self.base_colour_button.setProperty("selected-colour", colour.name())
            self.apply_layer_controls()

    def create_visual_group(self) -> None:
        if self.document is None:
            return
        stream_ids = {stream.object_id for stream in self.document.draft.connections}
        members = tuple(
            identifier for identifier in self.selected_ids() if identifier in stream_ids
        )
        if not members:
            self.note("Select at least one stream before creating a visual group.")
            return
        name, accepted = QInputDialog.getText(self, "New visual group", "Group name")
        if not accepted or not name.strip():
            return
        colour = QColorDialog.getColor(QColor("#FFD166"), self, "Highlight colour")
        if not colour.isValid():
            return
        group = c.VisualStreamGroup(
            "visual-group:" + uuid4().hex,
            name.strip(),
            members,
            colour.name(),
            len(self.document.visual_groups),
        )
        self.apply_edit(c.UpsertVisualStreamGroupEdit(group))

    def create_engineering_subsystem(self) -> None:
        if self.document is None:
            return
        members = self.selected_ids()
        if not members:
            self.note("Select at least one flowsheet object before creating a subsystem.")
            return
        name, accepted = QInputDialog.getText(self, "New engineering subsystem", "Subsystem name")
        if accepted and name.strip():
            self.apply_edit(
                c.UpsertEngineeringSubsystemEdit(
                    c.EngineeringSubsystem(
                        "subsystem:" + uuid4().hex,
                        name.strip(),
                        members,
                        "User-defined engineering subsystem",
                        revision_provenance=f"draft-revision:{self.document.draft.revision}",
                    )
                )
            )

    def selected_grouping(self) -> tuple[str, str] | None:
        item = self.layers_tree.currentItem()
        value = item.data(0, Qt.ItemDataRole.UserRole) if item else None
        return value if isinstance(value, tuple) and len(value) == 2 else None

    def layer_item_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        value = item.data(0, Qt.ItemDataRole.UserRole)
        if self.loading_layers or self.document is None or not isinstance(value, tuple):
            return
        kind, identifier = value
        if (
            kind == "visual"
            and identifier != self.document.layer_preferences.active_visual_group_id
        ):
            self.apply_edit(
                c.SetPfdLayerPreferencesEdit(
                    replace(self.document.layer_preferences, active_visual_group_id=identifier)
                )
            )

    def layer_item_changed(self, item: QTreeWidgetItem, _column: int) -> None:
        value = item.data(0, Qt.ItemDataRole.UserRole)
        if self.loading_layers or self.document is None or not isinstance(value, tuple):
            return
        kind, identifier = value
        if kind != "visual":
            return
        group = next(group for group in self.document.visual_groups if group.group_id == identifier)
        visible = item.checkState(0) == Qt.CheckState.Checked
        if visible != group.visible:
            self.apply_edit(c.UpsertVisualStreamGroupEdit(replace(group, visible=visible)))

    def select_group_members(self) -> None:
        selected = self.selected_grouping()
        if selected is None or self.document is None:
            return
        kind, identifier = selected
        if kind == "visual":
            members = next(
                group.member_stream_ids
                for group in self.document.visual_groups
                if group.group_id == identifier
            )
        else:
            members = next(
                group.member_object_ids
                for group in self.document.engineering_subsystems
                if group.subsystem_id == identifier
            )
        self.canvas.select_ids(members)

    def isolate_visual_group(self) -> None:
        selected = self.selected_grouping()
        if selected is None or selected[0] != "visual" or self.document is None:
            return
        for group in self.document.visual_groups:
            visible = group.group_id == selected[1]
            if group.visible != visible:
                self.apply_edit(c.UpsertVisualStreamGroupEdit(replace(group, visible=visible)))

    def remove_grouping(self) -> None:
        selected = self.selected_grouping()
        if selected is None:
            return
        kind, identifier = selected
        edit: c.PfdEdit = (
            c.RemoveVisualStreamGroupEdit(identifier)
            if kind == "visual"
            else c.RemoveEngineeringSubsystemEdit(identifier)
        )
        self.apply_edit(edit)

    def restore_shortcut_preferences(self) -> tuple[str, ...]:
        """Defer native bindings until the extended action registry is complete."""
        if not self.ready:
            return ()
        return super().restore_shortcut_preferences()

    def _accept_document(self, document: c.PfdDocumentDto, *, dirty: bool) -> None:
        errors = self.action_registry.restore(
            {**self.default_bindings, **dict(document.settings.shortcuts)}
        )
        for error in errors:
            self.note("Case shortcut preference: " + error)
        self.document, self.current, self.dirty = document, document.draft, dirty
        if dirty:
            self.last_receipt = None
        self.refresh()

    def create_draft(self, name: str) -> bool:
        listing = self.execute("pfd.list", c.ListDraftsParameters())
        if isinstance(listing.data, c.DraftListDto) and any(
            s.draft_id == name for s in listing.data.drafts
        ):
            self.note("A saved draft already uses this name.")
            return False
        if not super().create_draft(name):
            return False
        assert self.current is not None
        outcome = self.execute("pfd.import", c.DraftParameters(self.current))
        if isinstance(outcome.data, c.PfdDocumentDto):
            self.undo_documents.clear()
            self.redo_documents.clear()
            self._accept_document(outcome.data, dirty=True)
            return True
        return False

    def open_draft(self, draft_id: str) -> bool:
        if not self._confirm_discard():
            return False
        outcome = self.execute("pfd.open", c.OpenDraftParameters(draft_id))
        if outcome.disposition == "COMPLETED" and isinstance(outcome.data, c.PfdDocumentDto):
            self.undo_documents.clear()
            self.redo_documents.clear()
            self.canvas.document = None
            self._accept_document(outcome.data, dirty=False)
            return True
        return False

    def save_current(self) -> bool:
        if self.document is None:
            return False
        centre = self.canvas.mapToScene(self.canvas.viewport().rect().center())
        snapshot = replace(
            self.document,
            viewport_centre=c.CanvasPointDto(centre.x(), centre.y()),
            viewport_scale=self.canvas.transform().m11(),
        )
        outcome = self.execute("pfd.save", c.PfdDocumentParameters(snapshot))
        if outcome.disposition == "COMPLETED" and isinstance(outcome.data, c.PfdDocumentDto):
            self._accept_document(outcome.data, dirty=False)
            self.refresh_catalog()
            return True
        return False

    def execute(self, name: str, parameters: c.CommandParameters) -> c.CommandOutcome:
        # Shared shell navigation uses the native+legacy catalogue in this client.
        return super().execute("pfd.list" if name == "draft.list" else name, parameters)

    def refresh(self) -> None:
        super().refresh()
        if not self.ready:
            return
        self.empty_draft.hide()
        for name, action in self.action_registry.actions.items():
            if name.startswith("pfd."):
                action.setEnabled(self.current is not None)
        self.action_registry.actions["pfd.undo"].setEnabled(
            bool(self.undo_documents) and self.current is not None
        )
        self.action_registry.actions["pfd.redo"].setEnabled(
            bool(self.redo_documents) and self.current is not None
        )
        if self.current is None:
            self.document = None
        elif self.document is not None and self.document.draft.draft_id == self.current.draft_id:
            self.canvas.set_document(self.document, self.catalogue)
            self.equipment.blockSignals(True)
            self.equipment.setRowCount(
                len(self.document.draft.equipment) + len(self.document.draft.connections)
            )
            objects = {o.object_id: o for o in self.document.objects}
            for row, stream in enumerate(
                self.document.draft.connections, len(self.document.draft.equipment)
            ):
                status = (
                    "Material stream"
                    if stream.object_id in self.canvas.routes
                    else "Unroutable stream"
                )
                for column, value in enumerate(
                    (objects[stream.object_id].tag, status, stream.object_id)
                ):
                    self.equipment.setItem(row, column, QTableWidgetItem(value))
            self.equipment.setVisible(bool(self.document.objects))
            self.equipment.blockSignals(False)
            self.inspect_ids(self.canvas.selected_ids())
        self.refresh_layers()

    def apply_edit(self, edit: c.PfdEdit) -> bool:
        """Apply an application edit and retain the prior immutable snapshot for Undo."""
        if self.document is None:
            return False
        before = self.document
        if isinstance(edit, c.SettingsEdit):
            prior = {
                key: action.shortcut().toString(QKeySequence.SequenceFormat.PortableText)
                for key, action in self.action_registry.actions.items()
            }
            errors = self.action_registry.restore(
                {**self.default_bindings, **dict(edit.settings.shortcuts)}
            )
            self.action_registry.restore(prior)
            if errors:
                self.note("; ".join(errors))
                return False
        outcome = self.execute("pfd.edit", c.PfdEditParameters(before, edit))
        if outcome.disposition != "COMPLETED" or not isinstance(outcome.data, c.PfdDocumentDto):
            self.canvas.set_document(before, self.catalogue)
            return False
        if outcome.data != before:
            self.undo_documents.append(before)
            self.redo_documents.clear()
            self._accept_document(outcome.data, dirty=True)
            if isinstance(edit, c.ConnectPortsEdit) and before.settings.prompt_stream_name:
                stream_id = outcome.data.draft.connections[-1].object_id
                self.canvas.scene_data.clearSelection()
                self.canvas.streams[stream_id].setSelected(True)
                QTimer.singleShot(0, self.rename_dialog)
        return True

    def undo(self) -> None:
        self._restore(self.undo_documents, self.redo_documents)

    def redo(self) -> None:
        self._restore(self.redo_documents, self.undo_documents)

    def _restore(self, source: list[c.PfdDocumentDto], target: list[c.PfdDocumentDto]) -> None:
        if not source or self.document is None:
            return
        outcome = self.execute("pfd.restore", c.PfdDocumentParameters(source[-1]))
        if outcome.disposition == "COMPLETED" and isinstance(outcome.data, c.PfdDocumentDto):
            target.append(self.document)
            source.pop()
            self._accept_document(outcome.data, dirty=True)

    def add_equipment(self) -> None:
        index = self.equipment_palette.currentRow()
        if index < 0:
            index = 0
        if not self.catalogue.models or self.document is None:
            return
        centre = self.canvas.mapToScene(self.canvas.viewport().rect().center())
        self.apply_edit(
            c.AddEquipmentEdit(
                self.catalogue.models[index].model_id, c.CanvasPointDto(centre.x(), centre.y())
            )
        )

    def selected_ids(self) -> tuple[str, ...]:
        ids = self.canvas.selected_ids()
        if ids:
            return ids
        return tuple(
            str(self.equipment.model().index(row.row(), 2).data())
            for row in self.equipment.selectionModel().selectedRows()
        )

    def inspect_selection(self) -> None:
        super().inspect_selection()
        if self.ready:
            ids = tuple(
                str(self.equipment.model().index(row.row(), 2).data())
                for row in self.equipment.selectionModel().selectedRows()
            )
            self.canvas.blockSignals(True)
            self.canvas.scene_data.clearSelection()
            for identifier in ids:
                item = self.canvas.nodes.get(identifier) or self.canvas.streams.get(identifier)
                if item is not None:
                    item.setSelected(True)
            self.canvas.blockSignals(False)
            self.inspect_ids(ids)

    def inspect_ids(self, identifiers: tuple[str, ...]) -> None:
        """Show input rows with separate units; missing inputs have no numerical default."""
        while self.input_form.rowCount():
            self.input_form.removeRow(0)
        if not self.document or len(identifiers) != 1:
            return
        identifier = identifiers[0]
        obj = next((o for o in self.document.objects if o.object_id == identifier), None)
        if obj is None:
            return
        self.selection_title.setText(obj.tag)
        self.selection_details.setText("Submitted inputs · Not validated · No results")
        node = next((n for n in self.document.draft.equipment if n.object_id == identifier), None)
        if node is None:
            self.selection_details.setText(
                "Material stream · Not run"
                if identifier in self.canvas.routes
                else "Unroutable stream: missing equipment or unsupported port. "
                "Saved input is retained."
            )
            return
        model = next((m for m in self.catalogue.models if m.model_id == node.model_id), None)
        if model is None:
            return
        for parameter in model.parameters:
            quantity = next((p.quantity for p in node.parameters if p.name == parameter.name), None)
            notation = next((n for n in obj.notation if n.name == parameter.name), None)
            preferred = next(
                (
                    u.display_unit
                    for u in self.document.settings.units
                    if u.canonical_unit == parameter.canonical_unit
                ),
                parameter.canonical_unit,
            )
            display_unit = (
                notation.display_unit if notation and notation.display_unit else preferred
            )
            original = notation.text if notation else str(quantity.value) if quantity else ""
            displayed = ""
            if quantity:
                outcome = self.execute(
                    "quantity.display", c.QuantityDisplayParameters(quantity, display_unit)
                )
                if isinstance(outcome.data, c.QuantityDto):
                    digits = self.document.settings.display_precision
                    displayed = f"{outcome.data.value:.{digits}g}"
            editor = QuantityInput(displayed, original, self.document.settings.original_on_edit)
            editor.setAccessibleName(parameter.title + " value")
            editor.setStyleSheet(
                f"QLineEdit {{ color: {self.document.settings.missing_colour}; }}"
                if quantity is None
                else ""
            )
            unit = QLineEdit(
                (quantity.unit if self.document.settings.original_on_edit else display_unit)
                if quantity
                else parameter.canonical_unit
            )
            unit.setAccessibleName(parameter.title + " input unit")
            editor.setToolTip(f"Display: {display_unit}; edit/submission: {unit.text()}")

            def commit(e=editor, u=unit, name=parameter.name, raw=original) -> None:
                if e.isModified() or u.isModified():
                    text = e.text() if e.isModified() else raw
                    edit = c.ConfigureInputEdit(identifier, name, text, u.text())
                    e.setModified(False)
                    u.setModified(False)
                    self.schedule_input_edit(edit)

            editor.editingFinished.connect(commit)
            unit.editingFinished.connect(commit)
            self.input_form.addRow(parameter.title + f" [{display_unit}]", editor)
            self.input_form.addRow("Submitted unit", unit)
            if quantity:
                override = QPushButton("Display unit override…")
                override.clicked.connect(
                    lambda _checked=False, name=parameter.name, initial=display_unit: (
                        self.display_override(identifier, name, initial)
                    )
                )
                self.input_form.addRow("", override)

    def schedule_input_edit(self, edit: c.ConfigureInputEdit) -> None:
        """Defer rebuilding the form until its editing-finished signal has returned."""
        QTimer.singleShot(0, lambda: self.apply_edit(edit))

    def display_override(self, identifier: str, name: str, initial: str) -> None:
        value, accepted = QInputDialog.getText(
            self, "Display unit", "Unit (blank uses case preference)", text=initial
        )
        if accepted:
            self.apply_edit(c.DisplayUnitEdit(identifier, name, value or None))

    def connect_dialog(self) -> None:
        if not self.document:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Connect typed ports")
        form = QFormLayout(dialog)
        output, incoming = QComboBox(), QComboBox()
        objects = {o.object_id: o for o in self.document.objects}
        models = {m.model_id: m for m in self.catalogue.models}
        for node in self.document.draft.equipment:
            if node.model_id not in models:
                continue
            for port in models[node.model_id].ports:
                choice = output if port.direction == "output" else incoming
                choice.addItem(
                    f"{objects[node.object_id].tag} / {port.name} / {port.kind}",
                    (node.object_id, port.name),
                )
        form.addRow("Output", output)
        form.addRow("Input", incoming)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if (
            dialog.exec() == QDialog.DialogCode.Accepted
            and output.currentData()
            and incoming.currentData()
        ):
            source, target = output.currentData(), incoming.currentData()
            self.apply_edit(c.ConnectPortsEdit(source[0], source[1], target[0], target[1]))

    def rename_dialog(self) -> None:
        ids = self.selected_ids()
        if not self.document or len(ids) != 1:
            return
        obj = next(o for o in self.document.objects if o.object_id == ids[0])
        family = [o.tag for o in self.document.objects if o.parent_stream_id == obj.object_id]
        value, accepted = QInputDialog.getText(
            self,
            "Rename object",
            "Unique tag"
            + (" · linked branches will follow: " + ", ".join(family) if family else ""),
            text=obj.tag,
        )
        if not accepted or value == obj.tag:
            return
        self.rename_selected(value)

    def rename_selected(self, value: str) -> None:
        """Use the same family/swap confirmation for GUI and command-line renaming."""
        ids = self.selected_ids()
        if not self.document or len(ids) != 1:
            return
        obj = next(o for o in self.document.objects if o.object_id == ids[0])
        family = [o.tag for o in self.document.objects if o.parent_stream_id == obj.object_id]
        if (
            family
            and QMessageBox.question(
                self,
                "Rename family",
                f"Rename {obj.tag} to {value} and linked branches to "
                + ", ".join(
                    value + (o.branch_suffix or "")
                    for o in self.document.objects
                    if o.parent_stream_id == obj.object_id
                )
                + "?",
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        if (
            not self.apply_edit(c.RenameObjectEdit(obj.object_id, value))
            and self.last_outcome
            and any(d.code == "TAG_CONFLICT" for d in self.last_outcome.diagnostics)
        ) and (
            QMessageBox.question(
                self,
                "Tag conflict",
                "Swap this tag with the conflicting stream? Choose No to keep both unchanged.",
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.apply_edit(c.RenameObjectEdit(obj.object_id, value, swap=True))

    def delete_selection(self) -> None:
        ids = self.selected_ids()
        if not ids or not self.document:
            return
        connected = [
            s for s in self.document.draft.connections if s.source_id in ids or s.target_id in ids
        ]
        if (
            connected
            and QMessageBox.question(
                self,
                "Delete connected equipment",
                f"Remove selected equipment and {len(connected)} connected streams? "
                "This edit can be undone.",
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        self.apply_edit(c.RemoveObjectsEdit(ids, bool(connected)))

    def copy_selection(self) -> None:
        """Copy text in a field, or selected equipment when the canvas owns the action."""
        focus = QApplication.focusWidget()
        if isinstance(focus, QLineEdit):
            focus.copy()
            return
        if not self.document:
            return
        ids = self.selected_ids()
        selected = [n for n in self.document.draft.equipment if n.object_id in ids]
        if not selected:
            return
        # Clipboard is a bounded local tagged snapshot, never a command or executable template.
        payload = boundary_json(
            c.PasteEquipmentEdit(self.document, tuple(n.object_id for n in selected))
        )
        mime = QMimeData()
        mime.setData("application/x-bh-pfd-selection", payload.encode())
        QApplication.clipboard().setMimeData(mime)

    def paste(self, *, connections: bool = False, reset: bool = False) -> None:
        """Paste into the active input field or create new equipment identities."""
        focus = QApplication.focusWidget()
        if isinstance(focus, QLineEdit) and not connections and not reset:
            focus.paste()
            return
        mime = QApplication.clipboard().mimeData()
        payload = bytes(mime.data("application/x-bh-pfd-selection").data())
        if not payload or len(payload) > 2_000_000:
            self.note("No supported equipment selection on clipboard (maximum 2 MB).")
            return
        try:
            selection = boundary_from_json(payload.decode())
            if not isinstance(selection, c.PasteEquipmentEdit):
                raise ValueError("Unsupported clipboard type")
            self.apply_edit(replace(selection, connections=connections, reset_inputs=reset))
        except (ValueError, TypeError, UnicodeError):
            self.note("Clipboard selection is invalid.")

    def adjust_route(self) -> None:
        """Keyboard alternative to Alt-drag for an orthogonal middle segment."""
        identifiers = self.selected_ids()
        if len(identifiers) != 1:
            return
        points = self.canvas.routes.get(identifiers[0])
        if not points:
            return
        value, accepted = QInputDialog.getDouble(
            self,
            "Adjust route segment",
            "Scene x coordinate",
            points[1].x(),
            -1_000_000,
            1_000_000,
            2,
        )
        if accepted:
            self.apply_edit(
                c.RouteStreamEdit(
                    identifiers[0],
                    (
                        c.CanvasPointDto(value, points[0].y()),
                        c.CanvasPointDto(value, points[-1].y()),
                    ),
                )
            )

    def reset_route(self) -> None:
        if not self.document:
            return
        for identifier in self.selected_ids():
            if identifier in {s.object_id for s in self.document.draft.connections}:
                self.apply_edit(c.RouteStreamEdit(identifier, ()))

    def toggle_details(self, *, pin: bool = False) -> None:
        if not self.document:
            return
        for identifier in self.selected_ids():
            obj = next(o for o in self.document.objects if o.object_id == identifier)
            self.apply_edit(
                c.DetailsEdit(
                    identifier,
                    obj.expanded if pin else not obj.expanded,
                    not obj.pinned if pin else obj.pinned,
                )
            )

    def settings_dialog(self) -> None:
        if not self.document:
            return
        dialog = PfdSettingsDialog(
            replace(
                self.document.settings, shortcuts=tuple(self.action_registry.overrides.items())
            ),
            self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.apply_edit(c.SettingsEdit(dialog.result_settings))

    def fit_flowsheet(self) -> None:
        """Fit visible symbols and labels without changing their saved coordinates."""
        self.canvas.fitInView(
            self.canvas.scene_data.itemsBoundingRect().adjusted(-40, -40, 40, 40),
            Qt.AspectRatioMode.KeepAspectRatio,
        )
        scale = self.canvas.transform().m11()
        if scale < 0.1 or scale > 4.0:
            self.canvas.scale(max(0.1, min(4.0, scale)) / scale, max(0.1, min(4.0, scale)) / scale)

    def context_menu(self, point: QPoint) -> None:
        menu = QMenu(self)
        for name in (
            "pfd.rename",
            "pfd.delete",
            "pfd.copy",
            "pfd.paste",
            "pfd.paste_connected",
            "pfd.paste_defaults",
            "pfd.route_adjust",
            "pfd.route_reset",
            "pfd.details",
            "pfd.pin",
            "pfd.settings",
        ):
            menu.addAction(self.action_registry.actions[name])
        menu.exec(self.canvas.viewport().mapToGlobal(point))
