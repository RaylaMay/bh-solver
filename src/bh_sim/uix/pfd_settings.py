"""Editable, versioned local preference templates with explicit preview and application."""

from __future__ import annotations

from dataclasses import fields
from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from bh_sim.boundary.contracts import PfdSettingsDto, UnitPreferenceDto
from bh_sim.boundary.json_codec import boundary_from_json, boundary_json


class PfdSettingsDialog(QDialog):
    """Edit case preferences; importing fills this preview and never applies automatically."""

    def __init__(self, settings: PfdSettingsDto, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("PFD settings · case preferences / template preview")
        self.resize(600, 700)
        self.result_settings = settings
        self.controls: dict[str, QWidget] = {}
        layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        panel = QWidget()
        form = QFormLayout(panel)
        choices = {
            "crossing": ("vertical-gap", "bridge"),
            "branch_names": ("suffix", "independent"),
            "collision": ("resolve", "next-available"),
        }
        for field in fields(settings):
            if field.name == "schema_version":
                continue
            value = getattr(settings, field.name)
            if isinstance(value, bool):
                widget = QCheckBox()
                widget.setChecked(value)
            elif field.name in choices:
                widget = QComboBox()
                widget.addItems(choices[field.name])
                widget.setCurrentText(value)
            else:
                text = (
                    ", ".join(value)
                    if field.name == "detail_fields"
                    else (
                        ", ".join(f"{u.canonical_unit}={u.display_unit}" for u in value)
                        if field.name == "units"
                        else ", ".join(f"{key}={binding}" for key, binding in value)
                        if field.name == "shortcuts"
                        else str(value)
                    )
                )
                widget = QLineEdit(text)
            widget.setAccessibleName(field.name.replace("_", " "))
            if field.name == "units":
                widget.setToolTip("Case display units, e.g. Pa=bar, K=degC, W=kW; blank uses SI")
            if field.name == "detail_fields":
                widget.setToolTip("Comma-separated inputs, status, or named catalogue input fields")
            self.controls[field.name] = widget
            form.addRow(field.name.replace("_", " ").capitalize(), widget)
        scroll.setWidget(panel)
        layout.addWidget(scroll)
        for title, callback in (
            ("Import local template…", self.import_template),
            ("Export preview as template…", self.export_template),
            ("Reset preview to baseline", lambda: self.populate(PfdSettingsDto())),
        ):
            button = QPushButton(title)
            button.clicked.connect(callback)
            layout.addWidget(button)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def read(self) -> PfdSettingsDto:
        """Parse controls into validated immutable preferences; no engineering values allowed."""
        values = {}
        defaults = PfdSettingsDto()
        for name, widget in self.controls.items():
            if isinstance(widget, QCheckBox):
                value = widget.isChecked()
            elif isinstance(widget, QComboBox):
                value = widget.currentText()
            elif isinstance(widget, QLineEdit):
                text = widget.text()
                if name == "units":
                    pairs = [p.strip().split("=", 1) for p in text.split(",") if p.strip()]
                    value = tuple(UnitPreferenceDto(*pair) for pair in pairs)
                elif name == "shortcuts":
                    value = tuple(
                        tuple(p.strip().split("=", 1)) for p in text.split(",") if p.strip()
                    )
                elif name == "detail_fields":
                    value = tuple(p.strip() for p in text.split(",") if p.strip())
                else:
                    default = getattr(defaults, name)
                    value = (
                        int(text)
                        if type(default) is int
                        else float(text)
                        if type(default) is float
                        else text
                    )
            else:
                raise ValueError("Unsupported preference control")
            values[name] = value
        return PfdSettingsDto(**values)

    def populate(self, settings: PfdSettingsDto) -> None:
        """Preview a complete template with all fields visible before Apply."""
        for name, widget in self.controls.items():
            value = getattr(settings, name)
            if isinstance(widget, QCheckBox):
                widget.setChecked(value)
            elif isinstance(widget, QComboBox):
                widget.setCurrentText(value)
            elif isinstance(widget, QLineEdit):
                widget.setText(
                    ", ".join(value)
                    if name == "detail_fields"
                    else ", ".join(f"{u.canonical_unit}={u.display_unit}" for u in value)
                    if name == "units"
                    else ", ".join(f"{key}={binding}" for key, binding in value)
                    if name == "shortcuts"
                    else str(value)
                )

    def apply(self) -> None:
        try:
            self.result_settings = self.read()
        except (ValueError, TypeError) as error:
            QMessageBox.warning(self, "Invalid preference", str(error))
            return
        self.accept()

    def import_template(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import preference template", "", "JSON (*.json)"
        )
        if not path:
            return
        try:
            if Path(path).stat().st_size > 100_000:
                raise ValueError("Template exceeds 100 KB")
            settings = boundary_from_json(Path(path).read_text(encoding="utf-8"))
            if not isinstance(settings, PfdSettingsDto):
                raise ValueError("Expected bh-pfd-settings-v1 template")
            self.populate(settings)
        except (ValueError, TypeError, OSError) as error:
            QMessageBox.warning(self, "Template not imported", str(error))

    def export_template(self) -> None:
        try:
            text = boundary_json(self.read()) + "\n"
        except (ValueError, TypeError) as error:
            QMessageBox.warning(self, "Invalid preference", str(error))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export preference template", "pfd-settings.json", "JSON (*.json)"
        )
        if path:
            try:
                Path(path).write_text(text, encoding="utf-8")
            except OSError as error:
                QMessageBox.warning(self, "Export failed", str(error))
