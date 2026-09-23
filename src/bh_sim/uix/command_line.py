"""Optional in-app command entry; this is a closed grammar, never a shell or REPL."""

from collections.abc import Callable

from PySide6.QtCore import QStringListModel, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QCompleter, QLineEdit, QPlainTextEdit, QVBoxLayout, QWidget


class CommandLine(QWidget):
    """Accessible command entry with context completion and bounded local recall."""

    def __init__(
        self,
        execute: Callable[[str], str],
        complete: Callable[[str], list[str]],
        history: list[str],
    ) -> None:
        super().__init__()
        self.execute_command, self.complete = execute, complete
        self.history = history[-100:]
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMaximumBlockCount(300)
        self.output.setAccessibleName("Command responses")
        self.input = RecallInput(self.history)
        self.input.setAccessibleName("BH command line")
        self.input.setPlaceholderText("BH > help · select <tag> · set <tag> <input> <value> <unit>")
        self.model = QStringListModel()
        completer = QCompleter(self.model, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.input.setCompleter(completer)
        self.input.textEdited.connect(self.refresh_completion)
        self.input.returnPressed.connect(self.submit)
        layout.addWidget(self.output)
        layout.addWidget(self.input)

    def refresh_completion(self, value: str) -> None:
        """Suggestions come only from registered actions and the current document."""
        self.model.setStringList(self.complete(value))

    def submit(self) -> None:
        """Submit once, retain entered text in local recall, and report rejections."""
        text = self.input.text().strip()
        if not text:
            return
        response = self.execute_command(text)
        self.output.appendPlainText("BH > " + text + "\n" + response)
        self.history.append(text)
        del self.history[:-100]
        self.input.recall_index = len(self.history)
        self.input.clear()


class RecallInput(QLineEdit):
    """Up/down recall without evaluating previous entries automatically."""

    def __init__(self, history: list[str]) -> None:
        super().__init__()
        self.history, self.recall_index = history, len(history)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        completer = self.completer()
        popup = completer.popup() if completer else None
        if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down) and not (popup and popup.isVisible()):
            self.recall_index = max(
                0,
                min(
                    len(self.history),
                    self.recall_index + (-1 if event.key() == Qt.Key.Key_Up else 1),
                ),
            )
            self.setText(
                self.history[self.recall_index] if self.recall_index < len(self.history) else ""
            )
            return
        super().keyPressEvent(event)
