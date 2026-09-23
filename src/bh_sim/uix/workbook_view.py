"""Process Workbook View dock widget for flowsheet streams, units, and balances."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from bh_sim.boundary.contracts import WorkbookDto


class WorkbookView(QWidget):
    """Dockable engineering spreadsheet displaying streams, unit metrics, and balances."""

    unit_selected = Signal(str)
    stream_selected = Signal(str)
    plot_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("workbook-view")
        self.workbook: WorkbookDto | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Header banner with run info and 4 uncollapsed status badges
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(4, 2, 4, 2)
        header_layout.setSpacing(6)

        self.run_label = QLabel("No result loaded")
        self.run_label.setStyleSheet("font-weight: bold; color: #EDF3F5;")
        header_layout.addWidget(self.run_label)

        self.badge_conv = QLabel("Conv: -")
        self.badge_clos = QLabel("Clos: -")
        self.badge_phys = QLabel("Phys: -")
        self.badge_corr = QLabel("Corr: -")
        badge_style = (
            "background-color: #23313D; color: #EDF3F5; "
            "border-radius: 3px; padding: 2px 6px; font-size: 11px;"
        )
        for badge in (self.badge_conv, self.badge_clos, self.badge_phys, self.badge_corr):
            badge.setStyleSheet(badge_style)
            header_layout.addWidget(badge)

        self.stale_label = QLabel("")
        self.stale_label.setStyleSheet("color: #E5C07B; font-weight: bold; font-size: 11px;")
        header_layout.addWidget(self.stale_label)

        header_layout.addStretch()

        self.plot_btn = QPushButton("Plot Selected…")
        self.plot_btn.setEnabled(False)
        self.plot_btn.clicked.connect(self._on_plot_clicked)
        header_layout.addWidget(self.plot_btn)

        layout.addWidget(header_widget)

        # Tabs for Streams, Equipment, Balances
        self.tabs = QTabWidget()
        self.streams_table = QTableWidget()
        self.equipment_table = QTableWidget()
        self.balances_table = QTableWidget()

        self._configure_table(
            self.streams_table,
            (
                "Stream Tag",
                "From",
                "Port",
                "To",
                "Port",
                "Fluid",
                "Mass Flow (kg/s)",
                "Temp (K)",
                "Pressure (bar)",
                "Enthalpy (kJ/kg)",
                "Vapor Frac",
            ),
        )
        self._configure_table(
            self.equipment_table,
            (
                "Unit ID",
                "Label",
                "Model",
                "Duty (kW)",
                "Delta P (kPa)",
                "Convergence",
                "Closure",
                "Physical",
                "Correlation",
            ),
        )
        self._configure_table(
            self.balances_table,
            (
                "Balance Dimension",
                "Inlet Total",
                "Outlet Total",
                "Duty / Generation",
                "Residual",
                "Tolerance",
                "Status",
                "Units",
            ),
        )

        self.streams_table.itemSelectionChanged.connect(self._on_stream_selection_changed)
        self.equipment_table.itemSelectionChanged.connect(self._on_equipment_selection_changed)

        self.tabs.addTab(self.streams_table, "Streams")
        self.tabs.addTab(self.equipment_table, "Equipment")
        self.tabs.addTab(self.balances_table, "Process Balances")

        layout.addWidget(self.tabs)

    def _configure_table(self, table: QTableWidget, headers: tuple[str, ...]) -> None:
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(list(headers))
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)

    def set_workbook(self, workbook: WorkbookDto | None, is_stale: bool = False) -> None:
        self.workbook = workbook
        if workbook is None:
            self.clear()
            return

        # Update run info
        self.run_label.setText(f"Run: {workbook.run_id}")

        def style_status(
            badge: QLabel, text: str, ok_val: str, warn_val: str | None = None
        ) -> None:
            badge.setText(text)
            val = text.split(":")[-1].strip().upper()
            if val == ok_val:
                badge.setStyleSheet(
                    "background-color: #2D5A43; color: #A8E6CF; "
                    "border-radius: 3px; padding: 2px 6px;"
                )
            elif warn_val and val == warn_val:
                badge.setStyleSheet(
                    "background-color: #614D24; color: #FFEAA7; "
                    "border-radius: 3px; padding: 2px 6px;"
                )
            elif val in ("FAILED", "INVALID"):
                badge.setStyleSheet(
                    "background-color: #632C2C; color: #FFB8B8; "
                    "border-radius: 3px; padding: 2px 6px;"
                )
            else:
                badge.setStyleSheet(
                    "background-color: #23313D; color: #EDF3F5; "
                    "border-radius: 3px; padding: 2px 6px;"
                )

        style_status(self.badge_conv, f"Conv: {workbook.convergence}", "CONVERGED")
        style_status(self.badge_clos, f"Clos: {workbook.closure}", "PASSED")
        style_status(
            self.badge_phys, f"Phys: {workbook.physical_validity}", "VALID", "EXTRAPOLATED"
        )
        style_status(
            self.badge_corr, f"Corr: {workbook.correlation_validity}", "VALID", "EXTRAPOLATED"
        )

        stale = is_stale or (workbook.selection is not None and workbook.selection.is_stale)
        if stale:
            self.stale_label.setText("⚠ Stale (modified flowsheet / earlier run)")
        else:
            self.stale_label.setText("")

        # Populate Streams Table
        self.streams_table.setRowCount(len(workbook.streams))
        for row, s in enumerate(workbook.streams):
            m_flow_str = f"{s.mass_flow_kg_s:.4f}" if s.mass_flow_kg_s is not None else "-"
            t_k_str = f"{s.temperature_k:.2f}" if s.temperature_k is not None else "-"
            p_bar_str = f"{(s.pressure_pa / 100000.0):.3f}" if s.pressure_pa is not None else "-"
            h_kj_str = f"{(s.enthalpy_j_kg / 1000.0):.2f}" if s.enthalpy_j_kg is not None else "-"
            vf_str = f"{s.vapor_fraction:.3f}" if s.vapor_fraction is not None else "-"

            items = (
                s.tag,
                s.from_unit_id or "-",
                s.from_port or "-",
                s.to_unit_id or "-",
                s.to_port or "-",
                s.fluid or "-",
                m_flow_str,
                t_k_str,
                p_bar_str,
                h_kj_str,
                vf_str,
            )
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, s.stream_id)
                self.streams_table.setItem(row, col, item)

        # Populate Equipment Table
        self.equipment_table.setRowCount(len(workbook.equipment))
        for row, e in enumerate(workbook.equipment):
            duty_kw_str = f"{(e.duty_w / 1000.0):.2f}" if e.duty_w is not None else "-"
            dp_kpa_str = f"{(e.delta_p_pa / 1000.0):.2f}" if e.delta_p_pa is not None else "-"
            items = (
                e.unit_id,
                e.label,
                e.model_id,
                duty_kw_str,
                dp_kpa_str,
                e.convergence,
                e.closure,
                e.physical_validity,
                e.correlation_validity,
            )
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, e.unit_id)
                self.equipment_table.setItem(row, col, item)

        # Populate Balances Table
        self.balances_table.setRowCount(len(workbook.balances))
        for row, b in enumerate(workbook.balances):
            items = (
                b.balance_type,
                f"{b.inlet_total:.6g}",
                f"{b.outlet_total:.6g}",
                f"{b.generation_or_duty:.6g}",
                f"{b.residual:.4e}",
                f"{b.tolerance:.4e}",
                b.status,
                b.units,
            )
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                if col == 6:  # Status column
                    if b.status == "PASSED":
                        item.setForeground(QColor("#A8E6CF"))
                    else:
                        item.setForeground(QColor("#FFB8B8"))
                self.balances_table.setItem(row, col, item)

    def clear(self) -> None:
        self.workbook = None
        self.run_label.setText("No result loaded")
        self.badge_conv.setText("Conv: -")
        self.badge_clos.setText("Clos: -")
        self.badge_phys.setText("Phys: -")
        self.badge_corr.setText("Corr: -")
        self.stale_label.setText("")
        self.streams_table.setRowCount(0)
        self.equipment_table.setRowCount(0)
        self.balances_table.setRowCount(0)
        self.plot_btn.setEnabled(False)

    def _on_stream_selection_changed(self) -> None:
        selected = self.streams_table.selectedItems()
        if selected:
            stream_id = str(selected[0].data(Qt.ItemDataRole.UserRole))
            self.stream_selected.emit(stream_id)
            self.plot_btn.setEnabled(True)

    def _on_equipment_selection_changed(self) -> None:
        selected = self.equipment_table.selectedItems()
        if selected:
            unit_id = str(selected[0].data(Qt.ItemDataRole.UserRole))
            self.unit_selected.emit(unit_id)
            self.plot_btn.setEnabled(True)

    def _on_plot_clicked(self) -> None:
        # Determine which tab is active
        idx = self.tabs.currentIndex()
        if idx == 0:  # Streams
            selected = self.streams_table.selectedItems()
            if selected:
                stream_id = str(selected[0].data(Qt.ItemDataRole.UserRole))
                self.plot_requested.emit(stream_id)
        elif idx == 1:  # Equipment
            selected = self.equipment_table.selectedItems()
            if selected:
                unit_id = str(selected[0].data(Qt.ItemDataRole.UserRole))
                self.plot_requested.emit(unit_id)
