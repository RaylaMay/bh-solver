"""Unit tests for DW5-B GraphViewer, GraphPlotWidget, exports, and GraphDialog."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import cast

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtCore import QRectF
from PySide6.QtWidgets import QApplication

from bh_sim.boundary import contracts as c
from bh_sim.uix.graph_viewer import GraphDialog, GraphPlotWidget, GraphViewer


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return cast(QApplication, QApplication.instance() or QApplication([]))


def sample_plot_definition() -> c.PlotDefinitionDto:
    pts_hot = (
        c.SeriesDataPointDto(0.0, 400.0, "HX hot in"),
        c.SeriesDataPointDto(25000.0, 360.0, "HX hot mid"),
        c.SeriesDataPointDto(50000.0, 320.0, "HX hot out"),
    )
    pts_cold = (
        c.SeriesDataPointDto(0.0, 290.0, "HX cold in"),
        c.SeriesDataPointDto(25000.0, 310.0, "HX cold mid"),
        c.SeriesDataPointDto(50000.0, 330.0, "HX cold out"),
    )
    series_hot = c.SeriesDescriptorDto(
        series_id="s:hot",
        label="Hot Stream T",
        unit_x="W",
        unit_y="K",
        line_style="solid",
        color_hex="#F0B673",
        points=pts_hot,
    )
    series_cold = c.SeriesDescriptorDto(
        series_id="s:cold",
        label="Cold Stream T",
        unit_x="W",
        unit_y="K",
        line_style="solid",
        color_hex="#82D7CC",
        points=pts_cold,
    )
    return c.PlotDefinitionDto(
        plot_id="plot:hx-1",
        title="Heat Exchanger T-Q Profile",
        x_label="Heat Transferred Q (W)",
        y_label="Temperature T (K)",
        plot_kind="T_Q",
        series=(series_hot, series_cold),
        run_id="run:test-1234",
        unit_id="unit:hx",
        provenance_hash="abc1234567890def",
        notes="Solver status: CONVERGED · Heat exchanger effectiveness 0.8",
    )


def test_graph_plot_widget_bounds_and_transforms(qapp: QApplication) -> None:
    widget = GraphPlotWidget()
    widget.resize(600, 400)
    plot_def = sample_plot_definition()
    widget.set_plot(plot_def)

    assert len(widget.visible_series) == 2
    min_x, max_x, min_y, max_y = widget._compute_bounds()

    # Data X range is 0 to 50000, Y range is 290 to 400
    assert min_x < 0.0
    assert max_x > 50000.0
    assert min_y < 290.0
    assert max_y > 400.0

    plot_rect = QRectF(widget.rect().adjusted(70, 32, -24, -48))
    screen_pt = widget._data_to_screen(25000.0, 350.0, min_x, max_x, min_y, max_y, plot_rect)
    assert plot_rect.left() < screen_pt.x() < plot_rect.right()
    assert plot_rect.top() < screen_pt.y() < plot_rect.bottom()

    rev_x, rev_y = widget._screen_to_data(
        screen_pt.x(), screen_pt.y(), min_x, max_x, min_y, max_y, plot_rect
    )
    assert pytest.approx(rev_x, abs=1e-3) == 25000.0
    assert pytest.approx(rev_y, abs=1e-3) == 350.0

    # Toggle series visibility
    widget.toggle_series("s:hot", False)
    assert "s:hot" not in widget.visible_series
    # Now only cold series is visible: min_y/max_y bounds shrink to cold series range
    min_x_c, max_x_c, min_y_c, max_y_c = widget._compute_bounds()
    assert max_y_c < 360.0  # Cold stream maximum is 330 K


def test_graph_plot_widget_csv_export(qapp: QApplication) -> None:
    widget = GraphPlotWidget()
    plot_def = sample_plot_definition()
    widget.set_plot(plot_def)

    with tempfile.TemporaryDirectory() as tmp_dir:
        csv_path = Path(tmp_dir) / "test_export.csv"
        widget.export_csv(str(csv_path))

        assert csv_path.exists()
        content = csv_path.read_text(encoding="utf-8")

        # Verify comment headers with complete provenance metadata
        assert "# Bound Horizons Technical Suite - Engineering Plot Data Export" in content
        assert "# Plot ID: plot:hx-1" in content
        assert "# Run ID: run:test-1234" in content
        assert "# Unit ID: unit:hx" in content
        assert "# Provenance Hash: abc1234567890def" in content
        assert "# Plot Kind: T_Q" in content
        assert "Solver status: CONVERGED" in content
        assert "# Plot Title: Heat Exchanger T-Q Profile" in content

        # Verify column headers and data rows
        lines = [
            line.strip()
            for line in content.splitlines()
            if line.strip() and not line.startswith("#")
        ]
        assert len(lines) >= 4  # Header + 3 data points
        header = lines[0]
        assert "Heat Transferred Q (W) [W]" in header
        assert "Hot Stream T [K]" in header
        assert "Cold Stream T [K]" in header


def test_graph_plot_widget_svg_export(qapp: QApplication) -> None:
    widget = GraphPlotWidget()
    plot_def = sample_plot_definition()
    widget.set_plot(plot_def)

    with tempfile.TemporaryDirectory() as tmp_dir:
        svg_path = Path(tmp_dir) / "test_export.svg"
        widget.export_svg(str(svg_path))

        assert svg_path.exists()
        content = svg_path.read_text(encoding="utf-8")

        assert "<?xml version=" in content
        assert "<svg" in content
        assert "</svg>" in content
        assert "Run ID: run:test-1234" in content
        assert "Provenance Hash: abc1234567890def" in content
        assert "Heat Transferred Q (W)" in content
        assert "Temperature T (K)" in content
        assert "<polyline" in content


def test_graph_viewer_and_dialog_integration(qapp: QApplication) -> None:
    viewer = GraphViewer()
    plot_def = sample_plot_definition()
    viewer.set_plot(plot_def)

    assert viewer.title_label.text() == "Heat Exchanger T-Q Profile"
    assert "run:test-1234" in viewer.source_badge.text()
    assert "abc123456789" in viewer.provenance_label.text()
    assert "T_Q" in viewer.provenance_label.text()
    assert viewer.pinned_btn.isChecked()

    # Check series checkboxes
    assert len(viewer._series_checkboxes) == 2
    assert "s:hot" in viewer._series_checkboxes
    assert "s:cold" in viewer._series_checkboxes

    # Test floating dialog
    dialog = GraphDialog(plot_def)
    assert dialog.windowTitle() == "Bound Horizons — Graph: Heat Exchanger T-Q Profile"
    assert dialog.viewer.plot_canvas.plot_def is not None
    assert dialog.viewer.pop_out_btn.isHidden()
    dialog.close()
