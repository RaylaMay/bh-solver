"""DW2 native shell over a neutral command gateway.

The shell owns focus, selection, docking and presentation preferences. It contains
no engineering equations, graph algorithms, unit conversion or storage adapter.
The current preview advertises draft commands only; no synthetic results appear.
"""

from datetime import datetime
from uuid import uuid4

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QDialogButtonBox,
    QDockWidget,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from bh_sim.boundary.contracts import (
    CommandOutcome,
    CommandParameters,
    CommandRequest,
    CreateDraftParameters,
    DraftDto,
    DraftListDto,
    DraftParameters,
    ListDraftsParameters,
    OpenDraftParameters,
)
from bh_sim.boundary.ports import CommandGateway

from .actions import ActionRegistry, CommandPalette, ShortcutEditor
from .design import THEMES, apply_design
from .workspace import WorkspaceSettings


def label(text: str, name: str = "") -> QLabel:
    """Create a plain-text label; case names cannot become rich-text instructions."""
    widget = QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(True)
    widget.setObjectName(name)
    return widget


class WorkstationWindow(QMainWindow):
    """Dockable, keyboard-accessible draft workspace with injected application commands."""

    def __init__(self, gateway: CommandGateway, settings: WorkspaceSettings) -> None:
        super().__init__()
        self.gateway = gateway
        self.workspace = settings
        self.current: DraftDto | None = None
        self.dirty = False
        self.last_outcome: CommandOutcome | None = None
        self.theme, self.compact = settings.appearance()
        self.setObjectName("bh-workstation")
        self.setWindowTitle("BH solver")
        self.resize(1360, 900)
        self.setMinimumSize(1040, 720)
        self.setDockNestingEnabled(True)
        self.action_registry = ActionRegistry(self)
        self._build_centre()
        self._build_docks()
        self._build_actions()
        self._build_menus_toolbar()
        self._build_status()
        self.restore_default_layout()
        self.workspace.restore(self)
        self._keep_on_screen()
        for error in self.action_registry.restore(settings.shortcuts()):
            self.note("Shortcut preference not restored: " + error)
        self.apply_appearance()
        self.refresh_catalog()
        self.refresh()
        self.note("Workspace ready. Solver connection is unavailable in this preview.")

    def _build_centre(self) -> None:
        self.pages = QStackedWidget()
        self.pages.setObjectName("process-workspace")
        self.setCentralWidget(self.pages)
        welcome = QWidget()
        layout = QVBoxLayout(welcome)
        layout.setContentsMargins(44, 48, 44, 40)
        layout.addStretch()
        layout.addWidget(label("BH / LOCAL WORKSPACE", "eyebrow"))
        layout.addSpacing(14)
        layout.addWidget(label("Your engineering workspace", "title"))
        layout.addWidget(
            label(
                "Create a draft or return to saved work.\nYour cases stay on this computer.",
                "muted",
            )
        )
        layout.addSpacing(24)
        buttons = QHBoxLayout()
        self.welcome_new = QPushButton("New draft")
        self.welcome_new.setObjectName("primary")
        self.welcome_open = QPushButton("Open draft")
        self.welcome_new.setAccessibleName("Create a new draft")
        self.welcome_open.setAccessibleName("Open a saved draft")
        buttons.addWidget(self.welcome_new)
        buttons.addWidget(self.welcome_open)
        buttons.addStretch()
        layout.addLayout(buttons)
        layout.addSpacing(32)
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.addWidget(label("WORKSTATION PREVIEW", "eyebrow"))
        card_layout.addWidget(label("Draft management and workspace customization are available."))
        card_layout.addWidget(
            label(
                "The flowsheet canvas and calculation services are not connected yet. "
                "No engineering results are generated here.",
                "muted",
            )
        )
        layout.addWidget(card)
        layout.addStretch(2)
        self.pages.addWidget(welcome)

        draft_page = QWidget()
        content = QVBoxLayout(draft_page)
        content.setContentsMargins(30, 30, 30, 24)
        content.addWidget(label("PROCESS WORKSPACE", "eyebrow"))
        self.draft_title = label("", "title")
        self.draft_state = label("", "muted")
        content.addWidget(self.draft_title)
        content.addWidget(self.draft_state)
        content.addSpacing(24)
        self.object_counts = label("")
        content.addWidget(self.object_counts)
        self.equipment = QTableWidget(0, 3)
        self.equipment.setAccessibleName("Equipment in the current draft")
        self.equipment.setHorizontalHeaderLabels(["Equipment", "Model", "Identifier"])
        self.equipment.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.equipment.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.equipment.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.equipment.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.equipment.verticalHeader().hide()
        self.equipment.itemSelectionChanged.connect(self.inspect_selection)
        content.addWidget(self.equipment, 1)
        self.empty_draft = label(
            "Your draft is ready.\n\nSave it now, or open an existing draft "
            "to inspect its equipment.\nThe editable flowsheet canvas is not available "
            "in this preview.",
            "muted",
        )
        self.empty_draft.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content.addWidget(self.empty_draft, 1)
        content.addWidget(
            label("Concept development only • No industrial or safety qualification", "muted")
        )
        self.pages.addWidget(draft_page)

    def _dock(self, title: str, name: str, widget: QWidget) -> QDockWidget:
        dock = QDockWidget(title, self)
        dock.setObjectName(name)
        dock.setWidget(widget)
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        return dock

    def _build_docks(self) -> None:
        self.navigator = QTreeWidget()
        self.navigator.setHeaderHidden(True)
        self.navigator.setAccessibleName("Workspace navigator")
        self.navigator.itemActivated.connect(self._navigate)
        self.navigator.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.navigator.customContextMenuRequested.connect(self._navigator_menu)
        self.navigator_dock = self._dock("Navigator", "navigator-dock", self.navigator)

        inspector = QWidget()
        form = QVBoxLayout(inspector)
        form.setContentsMargins(16, 18, 16, 18)
        form.addWidget(label("SELECTION", "eyebrow"))
        self.selection_title = label("No draft selected")
        self.selection_title.setAccessibleDescription("Selection details")
        self.selection_details = label("Open or create a draft to inspect it.", "muted")
        form.addWidget(self.selection_title)
        form.addWidget(self.selection_details)
        self.parameters = QTableWidget(0, 3)
        self.parameters.setAccessibleName("Submitted input quantities")
        self.parameters.setHorizontalHeaderLabels(["Input", "Value", "Unit"])
        self.parameters.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.parameters.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.parameters.horizontalHeader().setStretchLastSection(True)
        self.parameters.verticalHeader().hide()
        form.addWidget(self.parameters)
        form.addWidget(
            label(
                "Inputs shown as submitted. No calculation or unit conversion "
                "is performed in this view.",
                "muted",
            )
        )
        self.inspector_dock = self._dock("Inspector", "inspector-dock", inspector)

        self.activity = QListWidget()
        self.activity.setAccessibleName("Session activity and diagnostics")
        self.activity_dock = self._dock("Activity & diagnostics", "activity-dock", self.activity)

    def _build_actions(self) -> None:
        add = self.action_registry.add
        standard = QKeySequence.StandardKey
        add("draft.create", "&New draft…", self._new_dialog, QKeySequence(standard.New))
        add("draft.open", "&Open draft…", self._open_dialog, QKeySequence(standard.Open))
        add("draft.save", "&Save draft", self.save_current, QKeySequence(standard.Save))
        add("draft.close", "&Close draft", self.close_draft, QKeySequence(standard.Close))
        quit_shortcut = QKeySequence(standard.Quit)
        if quit_shortcut.isEmpty():
            # Some platform plugins (including offscreen) omit StandardKey.Quit.
            # Qt maps Ctrl to Command on macOS; keep an explicit keyboard exit.
            quit_shortcut = QKeySequence("Ctrl+Q")
        add("app.quit", "&Quit BH", self.close, quit_shortcut)
        self.action_registry.actions["app.quit"].setMenuRole(QAction.MenuRole.QuitRole)
        reason = "Solver connection is unavailable in this preview; no calculation is performed."
        for identifier, title in (("draft.validate", "Validate"), ("run.start", "Run")):
            action = add(identifier, title, lambda: None, reason=reason)
            action.setEnabled(False)
        add("commands.palette", "&Commands…", self.show_palette, QKeySequence("Ctrl+Shift+P"))
        add("commands.shortcuts", "Keyboard &shortcuts…", self.show_shortcuts)
        add("workspace.restore", "Restore default &layout", self.restore_default_layout)
        for identifier, title, dock, target, shortcut in (
            ("navigator", "Navigator", self.navigator_dock, self.navigator, "Ctrl+1"),
            ("inspector", "Inspector", self.inspector_dock, self.parameters, "Ctrl+2"),
            ("activity", "Activity and diagnostics", self.activity_dock, self.activity, "Ctrl+3"),
        ):
            self.action_registry.register_existing("view." + identifier, dock.toggleViewAction())
            add(
                "focus." + identifier,
                "Focus " + title,
                lambda panel=dock, widget=target: self.focus_panel(panel, widget),
                QKeySequence(shortcut),
            )
        for theme in THEMES:
            add("theme." + theme, theme + " theme", lambda name=theme: self.set_theme(name))
        compact = add("workspace.compact", "Compact density", self.toggle_density)
        compact.setCheckable(True)
        compact.setChecked(self.compact)
        add("app.about", "About BH solver", self.about)
        self.action_registry.actions["app.about"].setMenuRole(QAction.MenuRole.AboutRole)
        self.welcome_new.clicked.connect(self.action_registry.actions["draft.create"].trigger)
        self.welcome_open.clicked.connect(self.action_registry.actions["draft.open"].trigger)

    def _build_menus_toolbar(self) -> None:
        menus = {
            "&File": ("draft.create", "draft.open", "draft.save", "draft.close", "app.quit"),
            "&View": (
                "view.navigator",
                "view.inspector",
                "view.activity",
                "focus.navigator",
                "focus.inspector",
                "focus.activity",
            ),
            "&Workspace": (
                "commands.palette",
                "commands.shortcuts",
                "workspace.restore",
                "workspace.compact",
                *["theme." + name for name in THEMES],
            ),
            "&Help": ("app.about",),
        }
        for title, identifiers in menus.items():
            menu = self.menuBar().addMenu(title)
            for identifier in identifiers:
                menu.addAction(self.action_registry.actions[identifier])
        toolbar = QToolBar("Main commands", self)
        toolbar.setObjectName("main-toolbar")
        toolbar.setMovable(False)
        toolbar.addWidget(label("BH", "eyebrow"))
        toolbar.addSeparator()
        for identifier in ("draft.create", "draft.open", "draft.save"):
            toolbar.addAction(self.action_registry.actions[identifier])
        toolbar.addSeparator()
        toolbar.addAction(self.action_registry.actions["draft.validate"])
        toolbar.addAction(self.action_registry.actions["run.start"])
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)
        toolbar.addWidget(label("LOCAL  /  PREVIEW", "muted"))
        toolbar.addAction(self.action_registry.actions["commands.palette"])
        self.addToolBar(toolbar)

    def _build_status(self) -> None:
        self.save_status = label("No draft selected")
        self.statusBar().addWidget(self.save_status, 1)
        self.scientific_status = label(
            "Not validated  |  Convergence: not run  |  Closure: not checked  |  "
            "Physical: unknown  |  Correlation: unknown"
        )
        self.scientific_status.setAccessibleDescription("Independent engineering states")
        self.scientific_status.setWordWrap(False)
        self.scientific_status.setStyleSheet("font-size: 11px;")
        self.statusBar().addPermanentWidget(self.scientific_status)

    def execute(self, name: str, parameters: CommandParameters) -> CommandOutcome:
        """Issue one attributable request and keep command rejection visible."""
        outcome = self.gateway.dispatch(
            CommandRequest(name, f"ui:{uuid4()}", "local-user", parameters)
        )
        self.last_outcome = outcome
        if outcome.disposition == "REJECTED":
            message = "; ".join(f"{item.code}: {item.message}" for item in outcome.diagnostics)
            self.note(message)
            self.activity_dock.show()
            self.statusBar().showMessage(message, 15000)
        return outcome

    def create_draft(self, name: str) -> bool:
        """Create through application policy; the returned draft remains unsaved."""
        if not self._confirm_discard():
            return False
        outcome = self.execute("draft.create", CreateDraftParameters(name))
        if outcome.disposition == "COMPLETED" and isinstance(outcome.data, DraftDto):
            self.current, self.dirty = outcome.data, True
            self.note("Created draft " + name + ". Save explicitly to retain it.")
            self.refresh()
            return True
        return False

    def _new_dialog(self) -> None:
        name, accepted = QInputDialog.getText(
            self, "New draft", "Draft name", QLineEdit.EchoMode.Normal, "Untitled draft"
        )
        if accepted:
            self.create_draft(name)

    def open_draft(self, draft_id: str) -> bool:
        """Open a selected saved identity; never validate or run on open."""
        if not self._confirm_discard():
            return False
        outcome = self.execute("draft.open", OpenDraftParameters(draft_id))
        if outcome.disposition == "COMPLETED" and isinstance(outcome.data, DraftDto):
            self.current, self.dirty = outcome.data, False
            self.note(f"Opened {draft_id}, revision {outcome.data.revision}.")
            self.refresh()
            return True
        return False

    def _open_dialog(self) -> None:
        outcome = self.execute("draft.list", ListDraftsParameters())
        if outcome.disposition != "COMPLETED" or not isinstance(outcome.data, DraftListDto):
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Open draft")
        dialog.setMinimumSize(520, 380)
        layout = QVBoxLayout(dialog)
        layout.addWidget(
            label(
                "Select saved work"
                if outcome.data.drafts
                else "No saved drafts yet. Create and save a draft first."
            )
        )
        choices = QListWidget()
        choices.setAccessibleName("Saved drafts")
        for draft in outcome.data.drafts:
            item = QListWidgetItem(f"{draft.draft_id}    ·    revision {draft.revision}")
            item.setData(Qt.ItemDataRole.UserRole, draft.draft_id)
            choices.addItem(item)
        layout.addWidget(choices)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Open | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Open).setEnabled(bool(outcome.data.drafts))
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        choices.itemActivated.connect(lambda _item: dialog.accept())
        layout.addWidget(buttons)
        choices.setCurrentRow(0)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            item = choices.currentItem()
            if item is not None:
                self.open_draft(str(item.data(Qt.ItemDataRole.UserRole)))

    def save_current(self) -> bool:
        """Acknowledge Save only after the application returns the persisted draft."""
        if self.current is None:
            return False
        outcome = self.execute("draft.save", DraftParameters(self.current))
        if outcome.disposition == "COMPLETED" and isinstance(outcome.data, DraftDto):
            self.current, self.dirty = outcome.data, False
            self.note(f"Saved {self.current.draft_id}, revision {self.current.revision}.")
            self.refresh_catalog()
            self.refresh()
            return True
        return False

    def _confirm_discard(self) -> bool:
        if not self.dirty:
            return True
        box = QMessageBox(
            QMessageBox.Icon.Question,
            "Unsaved draft",
            "Save this draft before continuing?",
            parent=self,
        )
        box.setTextFormat(Qt.TextFormat.PlainText)
        box.setStandardButtons(
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel
        )
        box.setDefaultButton(QMessageBox.StandardButton.Save)
        answer = box.exec()
        if answer == QMessageBox.StandardButton.Save:
            return self.save_current()
        return answer == QMessageBox.StandardButton.Discard

    def close_draft(self) -> None:
        """Leave saved work intact; protect an unsaved draft with explicit choices."""
        if self._confirm_discard():
            self.current, self.dirty = None, False
            self.refresh()

    def refresh_catalog(self) -> None:
        """Refresh navigation from the repository, preserving no hidden calculation state."""
        outcome = self.execute("draft.list", ListDraftsParameters())
        if outcome.disposition != "COMPLETED" or not isinstance(outcome.data, DraftListDto):
            return
        self.navigator.clear()
        root = QTreeWidgetItem(["Saved drafts"])
        self.navigator.addTopLevelItem(root)
        for draft in outcome.data.drafts:
            item = QTreeWidgetItem([f"{draft.draft_id}  ·  r{draft.revision}"])
            item.setData(0, Qt.ItemDataRole.UserRole, draft.draft_id)
            root.addChild(item)
        if not outcome.data.drafts:
            root.addChild(QTreeWidgetItem(["No saved drafts yet"]))
        root.setExpanded(True)

    def _navigate(self, item: QTreeWidgetItem, _column: int) -> None:
        identifier = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(identifier, str):
            self.open_draft(identifier)

    def _navigator_menu(self, position: QPoint) -> None:
        menu = QMenu(self)
        for name in ("draft.create", "draft.open", "draft.save"):
            menu.addAction(self.action_registry.actions[name])
        menu.exec(self.navigator.viewport().mapToGlobal(position))

    def refresh(self) -> None:
        """Present submitted DTO values and independent unavailable scientific states."""
        for name in ("draft.create", "draft.open"):
            self.action_registry.actions[name].setEnabled(name in self.gateway.command_names)
        self.action_registry.actions["draft.save"].setEnabled(
            self.current is not None and self.dirty and "draft.save" in self.gateway.command_names
        )
        self.action_registry.actions["draft.close"].setEnabled(self.current is not None)
        self.welcome_new.setEnabled(self.action_registry.actions["draft.create"].isEnabled())
        self.welcome_open.setEnabled(self.action_registry.actions["draft.open"].isEnabled())
        self.pages.setCurrentIndex(0 if self.current is None else 1)
        self.parameters.setRowCount(0)
        if self.current is None:
            self.setWindowTitle("BH solver")
            self.save_status.setText("No draft selected")
            self.selection_title.setText("No draft selected")
            self.selection_details.setText("Open or create a draft to inspect it.")
            return
        draft = self.current
        self.setWindowTitle(
            f"{draft.draft_id}{' • Unsaved' if self.dirty else ''} — BH solver"
        )
        self.draft_title.setText(draft.draft_id)
        state = "Unsaved draft" if self.dirty else f"Saved locally · Revision {draft.revision}"
        self.draft_state.setText(state + "  /  Review profile")
        self.save_status.setText(state)
        self.object_counts.setText(
            f"{len(draft.equipment)} equipment objects     /     "
            f"{len(draft.connections)} connections"
        )
        self.equipment.setRowCount(len(draft.equipment))
        labels = {
            (item.object_id, item.occurrence): item.label
            for item in draft.presentation.objects
            if item.object_kind == "equipment"
        }
        occurrences: dict[str, int] = {}
        for row, node in enumerate(draft.equipment):
            occurrence = occurrences.get(node.object_id, 0)
            occurrences[node.object_id] = occurrence + 1
            title = labels.get((node.object_id, occurrence))
            for column, value in enumerate(
                (title if title is not None else node.object_id, node.model_id, node.object_id)
            ):
                self.equipment.setItem(row, column, QTableWidgetItem(value))
        self.equipment.setVisible(bool(draft.equipment))
        self.empty_draft.setVisible(not draft.equipment)
        self.selection_title.setText(draft.draft_id)
        self.selection_details.setText(
            f"Revision {draft.revision}\nNot validated\nNo result selected"
        )

    def inspect_selection(self) -> None:
        """Show input values/units without conversion or interpretation as results."""
        if self.current is None or not 0 <= self.equipment.currentRow() < len(
            self.current.equipment
        ):
            return
        node = self.current.equipment[self.equipment.currentRow()]
        self.selection_title.setText(node.object_id)
        self.selection_details.setText(node.model_id + "\nSubmitted inputs · Not calculated")
        self.parameters.setRowCount(len(node.parameters))
        for row, parameter in enumerate(node.parameters):
            for column, value in enumerate(
                (parameter.name, str(parameter.quantity.value), parameter.quantity.unit)
            ):
                self.parameters.setItem(row, column, QTableWidgetItem(value))

    def note(self, message: str) -> None:
        """Keep visible session feedback, without claiming a durable audit ledger."""
        self.activity.addItem(datetime.now().strftime("%H:%M") + "   " + message)
        self.activity.scrollToBottom()

    def restore_default_layout(self) -> None:
        """Restore dock visibility/placement; never touch the current draft."""
        for dock in (self.navigator_dock, self.inspector_dock, self.activity_dock):
            dock.setFloating(False)
            self.removeDockWidget(dock)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.navigator_dock)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.inspector_dock)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.activity_dock)
        for dock in (self.navigator_dock, self.inspector_dock, self.activity_dock):
            dock.show()
        self.resizeDocks(
            [self.navigator_dock, self.inspector_dock], [220, 300], Qt.Orientation.Horizontal
        )
        self.resizeDocks([self.activity_dock], [150], Qt.Orientation.Vertical)

    def _keep_on_screen(self) -> None:
        app = QApplication.instance()
        if isinstance(app, QApplication) and not any(
            screen.availableGeometry().intersects(self.frameGeometry()) for screen in app.screens()
        ):
            screen = app.primaryScreen()
            if screen is not None:
                self.move(screen.availableGeometry().topLeft())

    def focus_panel(self, dock: QDockWidget, target: QWidget) -> None:
        """Make hidden docks reachable from keyboard commands."""
        dock.show()
        dock.raise_()
        target.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def set_theme(self, name: str) -> None:
        self.theme = name
        self.apply_appearance()

    def toggle_density(self) -> None:
        self.compact = self.action_registry.actions["workspace.compact"].isChecked()
        self.apply_appearance()

    def apply_appearance(self) -> None:
        """Apply saved visual preferences; motion is absent in every theme."""
        app = QApplication.instance()
        if isinstance(app, QApplication):
            apply_design(app, self.theme, self.compact)

    def show_palette(self) -> None:
        CommandPalette(self.action_registry, self).exec()

    def show_shortcuts(self) -> None:
        ShortcutEditor(self.action_registry, self).exec()

    def about(self) -> None:
        QMessageBox.about(
            self,
            "BH solver",
            "BH solver · Native workstation preview\n\n"
            "Draft workflow and workspace controls are available.\n"
            "Solver, PFD editing, AI and speech are not connected.\n\n"
            "Concept development only. Not qualified for industrial or safety-critical use.\n\n"
            "Qt/PySide 6.11.2 is used through its LGPLv3 route.\n"
            "See the repository's Qt adoption and licence records.",
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        """Protect unsaved draft work and persist presentation preferences only."""
        if not self._confirm_discard():
            event.ignore()
            return
        if not self.workspace.save(self, self.theme, self.compact, self.action_registry.overrides):
            QMessageBox.warning(
                self,
                "Layout not saved",
                "The workspace layout could not be saved. Saved drafts are unchanged.",
            )
        event.accept()
