"""One QAction registry for menus, toolbar, palette and keyboard bindings.

Engineering actions call the injected command gateway through the main window.
Dock/focus/theme actions remain presentation operations; widgets never enter the
application-policy registry. Shortcut conflict checks prevent ambiguous dispatch.
"""

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QKeySequenceEdit,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)


class ActionRegistry:
    """Own presentation bindings once, including unavailable command explanations."""

    def __init__(self, owner: QWidget) -> None:
        self.owner = owner
        self.actions: dict[str, QAction] = {}
        self.overrides: dict[str, str] = {}

    def add(
        self,
        identifier: str,
        title: str,
        callback: Callable[[], object],
        shortcut: QKeySequence | None = None,
        reason: str = "",
    ) -> QAction:
        """Create a reusable action; its handler is shared by every input surface."""
        action = QAction(title, self.owner)
        action.setObjectName(identifier)
        action.setToolTip(reason or title.replace("&", ""))
        action.setStatusTip(action.toolTip())
        if shortcut is not None:
            action.setShortcut(shortcut)
        action.triggered.connect(lambda _checked=False: callback())
        self.owner.addAction(action)
        self.actions[identifier] = action
        return action

    def register_existing(self, identifier: str, action: QAction) -> None:
        """Include native dock toggle actions in the same discovery/binding registry."""
        action.setObjectName(identifier)
        self.actions[identifier] = action

    def assign(self, identifier: str, sequence: QKeySequence) -> str | None:
        """Apply an unambiguous one-stroke shortcut or return a readable rejection."""
        if identifier not in self.actions:
            return "Command is unavailable."
        error = self._binding_error(
            identifier, sequence, {key: action.shortcut() for key, action in self.actions.items()}
        )
        if error:
            return error
        self.actions[identifier].setShortcut(sequence)
        self.overrides[identifier] = sequence.toString(QKeySequence.SequenceFormat.PortableText)
        return None

    def _binding_error(
        self, identifier: str, sequence: QKeySequence, bindings: dict[str, QKeySequence]
    ) -> str | None:
        """Check the proposed final map, so restored swaps are order independent."""
        if sequence.count() > 1:
            return "Use a single key combination."
        if not sequence.isEmpty():
            if not sequence.toString(QKeySequence.SequenceFormat.PortableText):
                return "Shortcut is not a recognized key combination."
            for key, assigned in bindings.items():
                if (
                    key != identifier
                    and sequence.matches(assigned) != QKeySequence.SequenceMatch.NoMatch
                ):
                    return "Already assigned to " + self.actions[key].text().replace("&", "") + "."
        return None

    def restore(self, overrides: dict[str, str]) -> tuple[str, ...]:
        """Restore a valid complete map atomically; retain defaults on any conflict.

        A user can swap two defaults by clearing one first in the editor. Checking
        each restored preference against the defaults would lose that valid swap.
        Removed command IDs are ignored with a diagnostic and never dispatched.
        """
        candidate = {key: action.shortcut() for key, action in self.actions.items()}
        known = {key: value for key, value in overrides.items() if key in candidate}
        messages = ["Unknown command: " + key for key in overrides if key not in candidate]
        for key, value in known.items():
            sequence = QKeySequence(value, QKeySequence.SequenceFormat.PortableText)
            if value and sequence.isEmpty():
                return (*messages, "Unrecognized shortcut for " + key + ".")
            candidate[key] = sequence
        for key, sequence in candidate.items():
            error = self._binding_error(key, sequence, candidate)
            if error:
                return (*messages, "Shortcuts retained at defaults: " + error)
        for key in known:
            self.actions[key].setShortcut(candidate[key])
        self.overrides = known
        return tuple(messages)


class CommandPalette(QDialog):
    """Search the real action registry, preserving enablement and dispatch identity."""

    def __init__(self, registry: ActionRegistry, parent: QWidget) -> None:
        super().__init__(parent)
        self.registry = registry
        self.setWindowTitle("Commands")
        self.setMinimumWidth(560)
        layout = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Find a command…")
        self.search.setAccessibleName("Find a command")
        self.results = QListWidget()
        self.results.setAccessibleName("Matching commands")
        layout.addWidget(self.search)
        layout.addWidget(self.results)
        self.search.textChanged.connect(self.refresh)
        self.search.returnPressed.connect(self.activate_selected)
        self.results.itemActivated.connect(lambda _item: self.activate_selected())
        self.refresh("")

    def refresh(self, query: str) -> None:
        """Filter without creating duplicate action handlers."""
        self.results.clear()
        for identifier, action in self.registry.actions.items():
            title = action.text().replace("&", "")
            if query.casefold() not in (title + " " + identifier).casefold():
                continue
            shortcut = action.shortcut().toString(QKeySequence.SequenceFormat.NativeText)
            suffix = ("    " + shortcut) if shortcut else ""
            if not action.isEnabled():
                suffix += "    — unavailable"
            item = QListWidgetItem(title + suffix)
            item.setData(Qt.ItemDataRole.UserRole, identifier)
            item.setToolTip(action.toolTip())
            self.results.addItem(item)
        if self.results.count():
            self.results.setCurrentRow(0)

    def activate_selected(self) -> None:
        """Trigger the selected existing action only when it is enabled."""
        item = self.results.currentItem()
        if item is None:
            return
        action = self.registry.actions[str(item.data(Qt.ItemDataRole.UserRole))]
        if action.isEnabled():
            self.accept()
            action.trigger()


class ShortcutEditor(QDialog):
    """Edit keyboard bindings with visible conflict feedback before application."""

    def __init__(self, registry: ActionRegistry, parent: QWidget) -> None:
        super().__init__(parent)
        self.registry = registry
        self.setWindowTitle("Keyboard shortcuts")
        self.setMinimumWidth(480)
        form = QFormLayout(self)
        self.commands = QComboBox()
        self.commands.setAccessibleName("Command to customize")
        for identifier, action in registry.actions.items():
            self.commands.addItem(action.text().replace("&", ""), identifier)
        self.sequence = QKeySequenceEdit()
        self.sequence.setMaximumSequenceLength(1)
        self.sequence.setAccessibleName("New shortcut")
        self.feedback = QLabel("Menu and command-palette access remains available.")
        self.feedback.setTextFormat(Qt.TextFormat.PlainText)
        self.feedback.setWordWrap(True)
        form.addRow("&Command", self.commands)
        form.addRow("&Shortcut", self.sequence)
        form.addRow(self.feedback)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Close
        )
        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)
        self.commands.currentIndexChanged.connect(self.select)
        self.select()

    def select(self) -> None:
        """Show the selected command's current binding."""
        self.sequence.setKeySequence(
            self.registry.actions[str(self.commands.currentData())].shortcut()
        )

    def apply(self) -> None:
        """Keep conflicts visible; save successful preferences with the workspace."""
        error = self.registry.assign(str(self.commands.currentData()), self.sequence.keySequence())
        self.feedback.setText(error or "Shortcut applied. It will be retained with this workspace.")
