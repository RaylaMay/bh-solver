"""Unified 2D graph viewer for Bound Horizons simulation results and profiles.

Provides a dockable GraphViewer widget, an interactive QPainter plot canvas,
SVG and CSV exports with full provenance headers, and a non-modal floating
GraphDialog for persistent multi-run comparison.
"""

from __future__ import annotations

import csv
import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QCursor,
    QFont,
    QFontMetrics,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from bh_sim.boundary.contracts import (
    PlotDefinitionDto,
    SeriesDataPointDto,
)

# Standard palette for process simulation curves
PALETTE = (
    "#82D7CC",  # Teal / Cold / Primary
    "#F0B673",  # Amber / Hot / Secondary
    "#38BDF8",  # Sky / Utility
    "#E06C75",  # Coral / Wall
    "#98C379",  # Mint / Generation
    "#C678DD",  # Violet
    "#D19A66",  # Orange
    "#61AFEF",  # Light Blue
)


class GraphPlotWidget(QWidget):
    """Interactive 2D Cartesian plot canvas implemented with QPainter."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.plot_def: PlotDefinitionDto | None = None
        self.visible_series: set[str] = set()

        # Canvas navigation state
        self.pan_offset = QPointF(0.0, 0.0)
        self.zoom_factor = 1.0
        self.last_mouse_pos: QPointF | None = None
        self.hover_point: tuple[str, SeriesDataPointDto, str, str, QPointF] | None = None

        self.setMouseTracking(True)
        self.setMinimumSize(320, 220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_plot(self, plot_def: PlotDefinitionDto | None) -> None:
        """Load a plot definition and reset navigation."""
        self.plot_def = plot_def
        if plot_def is not None:
            self.visible_series = {s.series_id for s in plot_def.series}
        else:
            self.visible_series.clear()
        self.reset_view()

    def reset_view(self) -> None:
        """Reset pan and zoom back to default auto-scaled bounds."""
        self.pan_offset = QPointF(0.0, 0.0)
        self.zoom_factor = 1.0
        self.hover_point = None
        self.update()

    def toggle_series(self, series_id: str, visible: bool) -> None:
        """Show or hide a specific data trace."""
        if visible:
            self.visible_series.add(series_id)
        else:
            self.visible_series.discard(series_id)
        self.update()

    def _compute_bounds(self) -> tuple[float, float, float, float]:
        """Determine min/max X and Y across all visible series."""
        if not self.plot_def:
            return 0.0, 1.0, 0.0, 1.0

        all_points = [
            pt
            for s in self.plot_def.series
            if s.series_id in self.visible_series
            for pt in s.points
        ]
        if not all_points:
            return 0.0, 1.0, 0.0, 1.0

        xs = [pt.x for pt in all_points]
        ys = [pt.y for pt in all_points]

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        if math.isclose(min_x, max_x, abs_tol=1e-9):
            min_x -= 0.5
            max_x += 0.5
        if math.isclose(min_y, max_y, abs_tol=1e-9):
            min_y -= 0.5
            max_y += 0.5

        # 5% padding
        dx = (max_x - min_x) * 0.05
        dy = (max_y - min_y) * 0.05
        return min_x - dx, max_x + dx, min_y - dy, max_y + dy

    def _data_to_screen(
        self,
        x: float,
        y: float,
        min_x: float,
        max_x: float,
        min_y: float,
        max_y: float,
        plot_rect: QRectF,
    ) -> QPointF:
        """Map data coordinates to screen coordinates with pan and zoom."""
        range_x = max_x - min_x
        range_y = max_y - min_y

        norm_x = (x - min_x) / range_x
        norm_y = (y - min_y) / range_y

        # Apply zoom around center and pan offset
        cx = plot_rect.left() + plot_rect.width() * 0.5 + self.pan_offset.x()
        cy = plot_rect.top() + plot_rect.height() * 0.5 + self.pan_offset.y()

        sx = cx + (norm_x - 0.5) * plot_rect.width() * self.zoom_factor
        sy = cy - (norm_y - 0.5) * plot_rect.height() * self.zoom_factor
        return QPointF(sx, sy)

    def _screen_to_data(
        self,
        sx: float,
        sy: float,
        min_x: float,
        max_x: float,
        min_y: float,
        max_y: float,
        plot_rect: QRectF,
    ) -> tuple[float, float]:
        """Map screen coordinates to data coordinates."""
        cx = plot_rect.left() + plot_rect.width() * 0.5 + self.pan_offset.x()
        cy = plot_rect.top() + plot_rect.height() * 0.5 + self.pan_offset.y()

        norm_x = 0.5 + (sx - cx) / (plot_rect.width() * self.zoom_factor)
        norm_y = 0.5 - (sy - cy) / (plot_rect.height() * self.zoom_factor)

        x = min_x + norm_x * (max_x - min_x)
        y = min_y + norm_y * (max_y - min_y)
        return x, y

    def paintEvent(self, _event: object) -> None:
        """Render the 2D engineering plot."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()

        # Canvas background
        painter.fillRect(0, 0, w, h, QColor("#14212A"))

        if not self.plot_def:
            painter.setPen(QColor("#7E8B92"))
            painter.drawText(
                QRectF(0, 0, w, h),
                Qt.AlignmentFlag.AlignCenter,
                "No graph data loaded.\nSelect an equipment or stream and click 'Plot Selected…'",
            )
            return

        # Margins for axes, labels, and ticks
        margin_left = 70.0
        margin_right = 24.0
        margin_top = 32.0
        margin_bottom = 48.0

        plot_rect = QRectF(
            margin_left,
            margin_top,
            max(10.0, w - margin_left - margin_right),
            max(10.0, h - margin_top - margin_bottom),
        )

        min_x, max_x, min_y, max_y = self._compute_bounds()

        # Draw plot area background
        painter.fillRect(plot_rect, QColor("#1A2630"))
        painter.setPen(QPen(QColor("#2E3D49"), 1))
        painter.drawRect(plot_rect)

        # Draw grid lines and axis ticks
        painter.setFont(QFont("sans-serif", 9))
        grid_pen = QPen(QColor("#23313D"), 1, Qt.PenStyle.DotLine)
        text_pen = QPen(QColor("#A0AEC0"), 1)

        num_ticks_x = 5
        for i in range(num_ticks_x + 1):
            gx = plot_rect.left() + plot_rect.width() * i / num_ticks_x
            painter.setPen(grid_pen)
            painter.drawLine(QPointF(gx, plot_rect.top()), QPointF(gx, plot_rect.bottom()))

            val_x, _ = self._screen_to_data(gx, 0, min_x, max_x, min_y, max_y, plot_rect)
            painter.setPen(text_pen)
            label = f"{val_x:.3g}"
            painter.drawText(
                QRectF(gx - 35, plot_rect.bottom() + 4, 70, 16),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                label,
            )

        num_ticks_y = 5
        for i in range(num_ticks_y + 1):
            gy = plot_rect.bottom() - plot_rect.height() * i / num_ticks_y
            painter.setPen(grid_pen)
            painter.drawLine(QPointF(plot_rect.left(), gy), QPointF(plot_rect.right(), gy))

            _, val_y = self._screen_to_data(0, gy, min_x, max_x, min_y, max_y, plot_rect)
            painter.setPen(text_pen)
            label = f"{val_y:.3g}"
            painter.drawText(
                QRectF(4, gy - 8, margin_left - 8, 16),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                label,
            )

        # Axis Titles
        painter.setPen(QColor("#EDF3F5"))
        painter.setFont(QFont("sans-serif", 10, QFont.Weight.Bold))

        # X axis title (bottom)
        painter.drawText(
            QRectF(plot_rect.left(), h - 22, plot_rect.width(), 20),
            Qt.AlignmentFlag.AlignCenter,
            self.plot_def.x_label,
        )

        # Y axis title (top left of plot)
        painter.drawText(
            QRectF(plot_rect.left(), 8, plot_rect.width(), 20),
            Qt.AlignmentFlag.AlignLeft,
            self.plot_def.y_label,
        )

        # Clip painter to plot area for series
        painter.setClipRect(plot_rect)

        # Draw series traces
        for s_idx, series in enumerate(self.plot_def.series):
            if series.series_id not in self.visible_series or not series.points:
                continue

            color = QColor(series.color_hex or PALETTE[s_idx % len(PALETTE)])
            pen_style = Qt.PenStyle.SolidLine
            if series.line_style == "dashed":
                pen_style = Qt.PenStyle.DashLine
            elif series.line_style == "dotted":
                pen_style = Qt.PenStyle.DotLine

            series_pen = QPen(color, 2, pen_style)
            painter.setPen(series_pen)

            screen_pts = [
                self._data_to_screen(pt.x, pt.y, min_x, max_x, min_y, max_y, plot_rect)
                for pt in series.points
            ]

            if series.line_style != "scatter":
                path = QPainterPath(screen_pts[0])
                for pt in screen_pts[1:]:
                    path.lineTo(pt)
                painter.drawPath(path)

            # Draw point markers
            painter.setBrush(color)
            for pt in screen_pts:
                painter.drawEllipse(pt, 3.5, 3.5)

        # Reset clipping for overlay / hover HUD
        painter.setClipping(False)

        # Draw Hover HUD / Tooltip
        if self.hover_point is not None:
            s_name, pt, ux, uy, screen_pt = self.hover_point
            if plot_rect.contains(screen_pt):
                # Crosshair
                painter.setPen(QPen(QColor("#7E8B92"), 1, Qt.PenStyle.DashLine))
                painter.drawLine(
                    QPointF(screen_pt.x(), plot_rect.top()),
                    QPointF(screen_pt.x(), plot_rect.bottom()),
                )
                painter.drawLine(
                    QPointF(plot_rect.left(), screen_pt.y()),
                    QPointF(plot_rect.right(), screen_pt.y()),
                )

                # Callout bubble
                hud_text = f"{s_name}\nX: {pt.x:.4g} {ux}\nY: {pt.y:.4g} {uy}"
                fm = QFontMetrics(painter.font())
                lines = hud_text.splitlines()
                box_w = max(fm.horizontalAdvance(line) for line in lines) + 16
                box_h = len(lines) * 16 + 10

                bx = screen_pt.x() + 10
                by = screen_pt.y() - box_h - 10
                if bx + box_w > plot_rect.right():
                    bx = screen_pt.x() - box_w - 10
                if by < plot_rect.top():
                    by = screen_pt.y() + 10

                hud_rect = QRectF(bx, by, box_w, box_h)
                painter.fillRect(hud_rect, QColor(20, 33, 42, 220))
                painter.setPen(QPen(QColor("#82D7CC"), 1))
                painter.drawRect(hud_rect)

                painter.setPen(QColor("#EDF3F5"))
                for idx, line in enumerate(lines):
                    painter.drawText(
                        QRectF(bx + 8, by + 5 + idx * 16, box_w - 16, 16),
                        Qt.AlignmentFlag.AlignLeft,
                        line,
                    )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Start pan gesture."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.last_mouse_pos = event.position()
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self.reset_view()
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle panning or hover inspection."""
        if event.buttons() & Qt.MouseButton.LeftButton and self.last_mouse_pos is not None:
            delta = event.position() - self.last_mouse_pos
            self.last_mouse_pos = event.position()
            self.pan_offset += delta
            self.update()
            event.accept()
            return

        # Check for nearest data point under cursor
        if self.plot_def:
            w, h = self.width(), self.height()
            plot_rect = QRectF(70.0, 32.0, max(10.0, w - 94.0), max(10.0, h - 80.0))
            if plot_rect.contains(event.position()):
                min_x, max_x, min_y, max_y = self._compute_bounds()
                closest_point = None
                min_dist_sq = 144.0  # 12px snap distance

                for series in self.plot_def.series:
                    if series.series_id not in self.visible_series:
                        continue
                    for pt in series.points:
                        s_pt = self._data_to_screen(
                            pt.x, pt.y, min_x, max_x, min_y, max_y, plot_rect
                        )
                        d_sq = (s_pt.x() - event.position().x()) ** 2 + (
                            s_pt.y() - event.position().y()
                        ) ** 2
                        if d_sq < min_dist_sq:
                            min_dist_sq = d_sq
                            closest_point = (series.label, pt, series.unit_x, series.unit_y, s_pt)

                if closest_point != self.hover_point:
                    self.hover_point = closest_point
                    self.update()
            elif self.hover_point is not None:
                self.hover_point = None
                self.update()

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """End pan gesture."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.last_mouse_pos = None
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            event.accept()
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Zoom in or out around cursor."""
        angle = event.angleDelta().y()
        if angle != 0:
            factor = 1.15 if angle > 0 else 1.0 / 1.15
            self.zoom_factor = max(0.2, min(50.0, self.zoom_factor * factor))
            self.update()
            event.accept()
        super().wheelEvent(event)

    def export_csv(self, filepath: str) -> None:
        """Export plotted series to CSV with complete provenance headers."""
        if not self.plot_def:
            raise ValueError("No plot data to export")

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            # Metadata comments
            f.write("# Bound Horizons Technical Suite - Engineering Plot Data Export\n")
            f.write(f"# Plot ID: {self.plot_def.plot_id}\n")
            f.write(f"# Run ID: {self.plot_def.run_id or 'None'}\n")
            f.write(f"# Unit ID: {self.plot_def.unit_id or 'None'}\n")
            f.write(f"# Provenance Hash: {self.plot_def.provenance_hash or 'None'}\n")
            f.write(f"# Plot Kind: {self.plot_def.plot_kind}\n")
            f.write(f"# Notes: {self.plot_def.notes or ''}\n")
            f.write(f"# Plot Title: {self.plot_def.title}\n")
            f.write("#\n")

            writer = csv.writer(f)
            # Find all unique X coordinates across series
            active_series = [s for s in self.plot_def.series if s.series_id in self.visible_series]
            if not active_series:
                active_series = list(self.plot_def.series)

            # Build headers
            ux = active_series[0].unit_x if active_series else ""
            header = [f"{self.plot_def.x_label} [{ux}]"]
            for s in active_series:
                header.append(f"{s.label} [{s.unit_y}]")
            writer.writerow(header)

            # For identical X grids, tabulate rows
            x_vals = sorted({pt.x for s in active_series for pt in s.points})
            for x in x_vals:
                row = [f"{x:g}"]
                for s in active_series:
                    pt = next((p for p in s.points if math.isclose(p.x, x, abs_tol=1e-9)), None)
                    row.append(f"{pt.y:g}" if pt else "")
                writer.writerow(row)

    def export_svg(self, filepath: str) -> None:
        """Export plot graphic to vector SVG with embedded metadata."""
        if not self.plot_def:
            raise ValueError("No plot data to export")

        w, h = 800, 500
        margin_left = 80.0
        margin_right = 30.0
        margin_top = 40.0
        margin_bottom = 60.0

        plot_w = w - margin_left - margin_right
        plot_h = h - margin_top - margin_bottom

        min_x, max_x, min_y, max_y = self._compute_bounds()
        range_x = max(1e-9, max_x - min_x)
        range_y = max(1e-9, max_y - min_y)

        svg_lines = [
            '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
            "<!-- Bound Horizons Simulation Plot Export -->",
            f"<!-- Plot ID: {self.plot_def.plot_id} -->",
            f"<!-- Run ID: {self.plot_def.run_id or 'None'} -->",
            f"<!-- Unit ID: {self.plot_def.unit_id or 'None'} -->",
            f"<!-- Provenance Hash: {self.plot_def.provenance_hash or 'None'} -->",
            f"<!-- Plot Kind: {self.plot_def.plot_kind} -->",
            (
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
                f'viewBox="0 0 {w} {h}">'
            ),
            "<style>",
            "  .bg { fill: #14212A; }",
            "  .plot-bg { fill: #1A2630; stroke: #2E3D49; stroke-width: 1; }",
            "  .grid { stroke: #23313D; stroke-width: 1; stroke-dasharray: 2,2; }",
            "  .axis-text { fill: #A0AEC0; font-family: sans-serif; font-size: 11px; }",
            (
                "  .title-text { fill: #EDF3F5; font-family: sans-serif; "
                "font-size: 14px; font-weight: bold; }"
            ),
            (
                "  .trace { fill: none; stroke-width: 2; "
                "stroke-linejoin: round; stroke-linecap: round; }"
            ),
            "</style>",
            f'<rect width="{w}" height="{h}" class="bg"/>',
            (
                f'<rect x="{margin_left}" y="{margin_top}" '
                f'width="{plot_w}" height="{plot_h}" class="plot-bg"/>'
            ),
        ]

        # Grid and Ticks
        for i in range(6):
            gx = margin_left + plot_w * i / 5.0
            vx = min_x + (i / 5.0) * range_x
            svg_lines.append(
                f'<line x1="{gx}" y1="{margin_top}" x2="{gx}" y2="{margin_top + plot_h}" '
                'class="grid"/>'
            )
            svg_lines.append(
                f'<text x="{gx}" y="{margin_top + plot_h + 18}" text-anchor="middle" '
                f'class="axis-text">{vx:.3g}</text>'
            )

        for i in range(6):
            gy = margin_top + plot_h - plot_h * i / 5.0
            vy = min_y + (i / 5.0) * range_y
            svg_lines.append(
                f'<line x1="{margin_left}" y1="{gy}" x2="{margin_left + plot_w}" y2="{gy}" '
                'class="grid"/>'
            )
            svg_lines.append(
                f'<text x="{margin_left - 10}" y="{gy + 4}" text-anchor="end" '
                f'class="axis-text">{vy:.3g}</text>'
            )

        # Titles
        svg_lines.append(
            f'<text x="{margin_left + plot_w / 2}" y="{h - 15}" text-anchor="middle" '
            f'class="title-text">{self.plot_def.x_label}</text>'
        )
        title_str = f"{self.plot_def.y_label} — {self.plot_def.title}"
        svg_lines.append(
            f'<text x="{margin_left}" y="{margin_top - 12}" text-anchor="start" '
            f'class="title-text">{title_str}</text>'
        )

        # Series traces
        for s_idx, series in enumerate(self.plot_def.series):
            if series.series_id not in self.visible_series or not series.points:
                continue
            color = series.color_hex or PALETTE[s_idx % len(PALETTE)]
            dash_attr = (
                ' stroke-dasharray="4,4"'
                if series.line_style == "dashed"
                else (' stroke-dasharray="2,2"' if series.line_style == "dotted" else "")
            )
            pts_svg = []
            for pt in series.points:
                sx = margin_left + (pt.x - min_x) / range_x * plot_w
                sy = margin_top + plot_h - (pt.y - min_y) / range_y * plot_h
                pts_svg.append(f"{sx:.1f},{sy:.1f}")

            points_attr = " ".join(pts_svg)
            if series.line_style != "scatter":
                svg_lines.append(
                    f'<polyline points="{points_attr}" class="trace" stroke="{color}"{dash_attr}/>'
                )
            for p_str in pts_svg:
                px, py = p_str.split(",")
                svg_lines.append(f'<circle cx="{px}" cy="{py}" r="3.5" fill="{color}"/>')

        svg_lines.append("</svg>")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(svg_lines))


class GraphViewer(QWidget):
    """Unified graph viewer dock widget with controls, provenance badges and exports."""

    pop_out_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("graph-viewer")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Top Control Bar
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(4, 2, 4, 2)
        header_layout.setSpacing(6)

        self.title_label = QLabel("Graph Viewer")
        self.title_label.setStyleSheet("font-weight: bold; color: #EDF3F5;")
        header_layout.addWidget(self.title_label)

        self.source_badge = QLabel("Source: None")
        self.source_badge.setStyleSheet(
            "background-color: #23313D; color: #82D7CC; "
            "border-radius: 3px; padding: 2px 6px; font-size: 11px;"
        )
        header_layout.addWidget(self.source_badge)

        self.pinned_btn = QToolButton()
        self.pinned_btn.setText("Pin to Run")
        self.pinned_btn.setCheckable(True)
        self.pinned_btn.setChecked(True)
        self.pinned_btn.setToolTip(
            "When pinned, plot retains its run data even if active selection changes"
        )
        header_layout.addWidget(self.pinned_btn)

        header_layout.addStretch()

        self.pop_out_btn = QPushButton("Open in Window")
        self.pop_out_btn.setToolTip("Open plot in an independent floating comparison window")
        self.pop_out_btn.clicked.connect(self.pop_out_requested.emit)
        header_layout.addWidget(self.pop_out_btn)

        self.csv_btn = QPushButton("Export CSV…")
        self.csv_btn.clicked.connect(self._on_export_csv)
        header_layout.addWidget(self.csv_btn)

        self.svg_btn = QPushButton("Export SVG…")
        self.svg_btn.clicked.connect(self._on_export_svg)
        header_layout.addWidget(self.svg_btn)

        self.reset_btn = QPushButton("Reset View")
        self.reset_btn.clicked.connect(self._on_reset_view)
        header_layout.addWidget(self.reset_btn)

        layout.addWidget(header_widget)

        # Plot Canvas
        self.plot_canvas = GraphPlotWidget(self)
        layout.addWidget(self.plot_canvas, 1)

        # Bottom Series Bar & Provenance
        self.series_bar = QWidget()
        self.series_layout = QHBoxLayout(self.series_bar)
        self.series_layout.setContentsMargins(4, 2, 4, 2)
        self.series_layout.setSpacing(8)

        self.provenance_label = QLabel("Provenance: -")
        self.provenance_label.setStyleSheet("color: #7E8B92; font-size: 11px;")
        self.series_layout.addWidget(self.provenance_label)
        self.series_layout.addStretch()

        layout.addWidget(self.series_bar)

        self._series_checkboxes: dict[str, QCheckBox] = {}

    def set_plot(self, plot_def: PlotDefinitionDto | None) -> None:
        """Update displayed plot definition and configure series checkboxes."""
        self.plot_canvas.set_plot(plot_def)

        # Clear existing series checkboxes
        for cb in self._series_checkboxes.values():
            self.series_layout.removeWidget(cb)
            cb.deleteLater()
        self._series_checkboxes.clear()

        if plot_def is None:
            self.title_label.setText("Graph Viewer")
            self.source_badge.setText("Source: None")
            self.provenance_label.setText("Provenance: -")
            return

        self.title_label.setText(plot_def.title)
        self.source_badge.setText(f"Run: {plot_def.run_id or 'Unsaved'}")
        hash_str = (plot_def.provenance_hash or "")[:12]
        self.provenance_label.setText(
            f"Hash: {hash_str}… · Kind: {plot_def.plot_kind} · {plot_def.notes or ''}"
        )

        # Add checkboxes for toggling traces
        for s_idx, series in enumerate(plot_def.series):
            cb = QCheckBox(series.label)
            cb.setChecked(True)
            color = series.color_hex or PALETTE[s_idx % len(PALETTE)]
            cb.setStyleSheet(f"color: {color}; font-size: 11px;")
            cb.toggled.connect(
                lambda checked, s_id=series.series_id: self.plot_canvas.toggle_series(s_id, checked)
            )
            self.series_layout.addWidget(cb)
            self._series_checkboxes[series.series_id] = cb

    def _on_reset_view(self) -> None:
        self.plot_canvas.reset_view()

    def _on_export_csv(self) -> None:
        if not self.plot_canvas.plot_def:
            QMessageBox.information(self, "Export CSV", "No plot data is available to export.")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Plot Data to CSV", "plot_data.csv", "CSV Files (*.csv)"
        )
        if filename:
            try:
                self.plot_canvas.export_csv(filename)
                QMessageBox.information(
                    self, "Export CSV", f"Successfully exported plot data to:\n{filename}"
                )
            except Exception as ex:
                QMessageBox.critical(self, "Export CSV Error", f"Failed to export CSV: {ex}")

    def _on_export_svg(self) -> None:
        if not self.plot_canvas.plot_def:
            QMessageBox.information(self, "Export SVG", "No plot data is available to export.")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Plot to SVG", "plot_graphic.svg", "SVG Files (*.svg)"
        )
        if filename:
            try:
                self.plot_canvas.export_svg(filename)
                QMessageBox.information(
                    self, "Export SVG", f"Successfully exported SVG image to:\n{filename}"
                )
            except Exception as ex:
                QMessageBox.critical(self, "Export SVG Error", f"Failed to export SVG: {ex}")


class GraphDialog(QDialog):
    """Non-modal floating comparison window containing a pinned GraphViewer."""

    def __init__(self, plot_def: PlotDefinitionDto, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle(f"Bound Horizons — Graph: {plot_def.title}")
        self.resize(720, 480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.viewer = GraphViewer(self)
        self.viewer.pop_out_btn.hide()  # Already floating
        self.viewer.set_plot(plot_def)
        layout.addWidget(self.viewer)
