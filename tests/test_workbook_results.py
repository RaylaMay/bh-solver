"""Unit tests for DW5-A result read model, workbooks, overlays, and plot data."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bh_sim.adapters.desktop_preview import create_supervised_gateway
from bh_sim.boundary import contracts as c
from bh_sim.boundary.contracts import (
    CommandRequest,
    GetOverlaysParameters,
    InspectWorkbookParameters,
    PlotDataParameters,
    StartRunParameters,
)


def make_heater_draft(draft_id: str) -> c.DraftDto:
    source = c.EquipmentDto(
        "u:src",
        "source",
        (
            c.ParameterDto("massFlow", c.QuantityDto(10.0, "kg/s")),
            c.ParameterDto("temperature", c.QuantityDto(350.0, "K")),
            c.ParameterDto("pressure", c.QuantityDto(200000.0, "Pa")),
        ),
    )
    heater = c.EquipmentDto(
        "u:heat",
        "heater",
        (c.ParameterDto("duty", c.QuantityDto(50000.0, "W")),),
    )
    sink = c.EquipmentDto("u:snk", "sink", ())
    s1 = c.ConnectionDto("c:1", "u:src", "u:heat", "out-0", "in-0")
    s2 = c.ConnectionDto("c:2", "u:heat", "u:snk", "out-0", "in-0")
    return c.DraftDto(
        draft_id=draft_id,
        revision=1,
        base_case_id=None,
        updated_at="2026-09-15T00:00:00Z",
        equipment=(source, heater, sink),
        connections=(s1, s2),
        presentation=c.PresentationDto(()),
    )


def make_hx_draft(draft_id: str) -> c.DraftDto:
    hot_src = c.EquipmentDto(
        "u:hot_src",
        "source",
        (
            c.ParameterDto("massFlow", c.QuantityDto(5.0, "kg/s")),
            c.ParameterDto("temperature", c.QuantityDto(400.0, "K")),
            c.ParameterDto("pressure", c.QuantityDto(300000.0, "Pa")),
        ),
    )
    cold_src = c.EquipmentDto(
        "u:cold_src",
        "source",
        (
            c.ParameterDto("massFlow", c.QuantityDto(8.0, "kg/s")),
            c.ParameterDto("temperature", c.QuantityDto(300.0, "K")),
            c.ParameterDto("pressure", c.QuantityDto(250000.0, "Pa")),
        ),
    )
    hx = c.EquipmentDto(
        "u:hx",
        "heat_exchanger",
        (c.ParameterDto("effectiveness", c.QuantityDto(0.8, "1")),),
    )
    hot_snk = c.EquipmentDto("u:hot_snk", "sink", ())
    cold_snk = c.EquipmentDto("u:cold_snk", "sink", ())
    c1 = c.ConnectionDto("c:hot_in", "u:hot_src", "u:hx", "out-0", "in-0")
    c2 = c.ConnectionDto("c:cold_in", "u:cold_src", "u:hx", "out-0", "in-1")
    c3 = c.ConnectionDto("c:hot_out", "u:hx", "u:hot_snk", "out-0", "in-0")
    c4 = c.ConnectionDto("c:cold_out", "u:hx", "u:cold_snk", "out-1", "in-0")
    return c.DraftDto(
        draft_id=draft_id,
        revision=1,
        base_case_id=None,
        updated_at="2026-09-15T00:00:00Z",
        equipment=(hot_src, cold_src, hx, hot_snk, cold_snk),
        connections=(c1, c2, c3, c4),
        presentation=c.PresentationDto(()),
    )


class WorkbookResultsTests(unittest.TestCase):
    def test_gateway_advertises_dw5_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            gateway = create_supervised_gateway(Path(temp_dir))
            for expected in (
                "workbook.inspect",
                "result.select_display",
                "result.overlays",
                "graph.plot",
            ):
                self.assertIn(expected, gateway.command_names)

    def test_workbook_generation_heater_case(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            gateway = create_supervised_gateway(Path(temp_dir))
            draft = make_heater_draft("HeaterProcess")

            # Validate
            val_req = CommandRequest(
                "draft.validate", "req-1", "test-actor", c.DraftParameters(draft)
            )
            val_out = gateway.dispatch(val_req)
            self.assertEqual(val_out.disposition, "COMPLETED")
            receipt = val_out.data
            assert isinstance(receipt, c.ValidationReceiptDto)

            # Run
            run_req = CommandRequest(
                "run.start", "req-2", "test-actor", StartRunParameters(draft, receipt.receipt_id)
            )
            run_out = gateway.dispatch(run_req)
            self.assertEqual(run_out.disposition, "COMPLETED")
            run_view = run_out.data
            assert isinstance(run_view, c.RunViewDto)

            # Inspect workbook
            wb_req = CommandRequest(
                "workbook.inspect",
                "req-3",
                "test-actor",
                InspectWorkbookParameters(case_id=draft.draft_id, run_id=run_view.run_id),
            )
            wb_out = gateway.dispatch(wb_req)
            self.assertEqual(wb_out.disposition, "COMPLETED")
            wb = wb_out.data
            assert isinstance(wb, c.WorkbookDto)

            # Verify uncollapsed 4-status dimensions
            self.assertEqual(wb.convergence, "CONVERGED")
            self.assertEqual(wb.closure, "PASSED")
            self.assertEqual(wb.physical_validity, "VALID")
            self.assertIn(wb.correlation_validity, ("VALID", "EXTRAPOLATED"))

            # Verify streams table
            self.assertEqual(len(wb.streams), 2)
            s1 = next(s for s in wb.streams if s.stream_id == "c:1")
            self.assertIsNotNone(s1.mass_flow_kg_s)
            self.assertAlmostEqual(s1.mass_flow_kg_s or 0.0, 10.0, places=4)
            self.assertIsNotNone(s1.temperature_k)
            self.assertAlmostEqual(s1.temperature_k or 0.0, 350.0, places=2)
            self.assertIsNotNone(s1.pressure_pa)
            self.assertAlmostEqual(s1.pressure_pa or 0.0, 200000.0, places=1)
            self.assertIsNotNone(s1.enthalpy_j_kg)

            s2 = next(s for s in wb.streams if s.stream_id == "c:2")
            self.assertAlmostEqual(s2.mass_flow_kg_s or 0.0, 10.0, places=4)
            # Heated stream temperature should be strictly greater than inlet
            self.assertGreater(s2.temperature_k or 0.0, s1.temperature_k or 0.0)

            # Verify equipment table
            self.assertEqual(len(wb.equipment), 3)
            heater_row = next(e for e in wb.equipment if e.unit_id == "u:heat")
            self.assertEqual(heater_row.model_id, "heater")
            self.assertIsNotNone(heater_row.duty_w)
            self.assertAlmostEqual(heater_row.duty_w or 0.0, 50000.0, places=2)
            self.assertEqual(heater_row.convergence, "CONVERGED")
            self.assertEqual(heater_row.closure, "PASSED")
            self.assertEqual(heater_row.physical_validity, "VALID")

            # Verify process balances
            self.assertEqual(len(wb.balances), 2)
            mass_b = next(b for b in wb.balances if b.balance_type == "MASS")
            self.assertEqual(mass_b.status, "PASSED")
            self.assertAlmostEqual(mass_b.inlet_total, 10.0, places=4)
            self.assertAlmostEqual(mass_b.outlet_total, 10.0, places=4)
            self.assertAlmostEqual(mass_b.residual, 0.0, places=6)

            energy_b = next(b for b in wb.balances if b.balance_type == "ENERGY")
            self.assertEqual(energy_b.status, "PASSED")
            self.assertAlmostEqual(energy_b.generation_or_duty, 50000.0, places=2)
            self.assertAlmostEqual(energy_b.residual, 0.0, places=4)

    def test_canvas_overlays(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            gateway = create_supervised_gateway(Path(temp_dir))
            draft = make_heater_draft("OverlayTest")

            # Validate and run
            val_out = gateway.dispatch(
                CommandRequest("draft.validate", "r-1", "a", c.DraftParameters(draft))
            )
            receipt = val_out.data
            assert isinstance(receipt, c.ValidationReceiptDto)

            run_out = gateway.dispatch(
                CommandRequest(
                    "run.start", "r-2", "a", StartRunParameters(draft, receipt.receipt_id)
                )
            )
            run_view = run_out.data
            assert isinstance(run_view, c.RunViewDto)

            # Request overlays
            ov_out = gateway.dispatch(
                CommandRequest(
                    "result.overlays",
                    "r-3",
                    "a",
                    GetOverlaysParameters(case_id=draft.draft_id, run_id=run_view.run_id),
                )
            )
            self.assertEqual(ov_out.disposition, "COMPLETED")
            overlays = ov_out.data
            assert isinstance(overlays, c.OverlaysDto)

            self.assertEqual(overlays.run_id, run_view.run_id)
            self.assertEqual(len(overlays.streams), 2)
            for s_ov in overlays.streams:
                self.assertTrue(s_ov.is_valid)
                self.assertIsNotNone(s_ov.temperature_k)
                self.assertIsNotNone(s_ov.mass_flow_kg_s)

            self.assertEqual(len(overlays.equipment), 3)
            heat_ov = next(e for e in overlays.equipment if e.unit_id == "u:heat")
            self.assertEqual(heat_ov.convergence, "CONVERGED")
            self.assertEqual(heat_ov.duty_w, 50000.0)

            # Selection DTO
            sel = overlays.selection
            self.assertEqual(sel.active_run_id, run_view.run_id)
            self.assertFalse(sel.is_stale)
            self.assertEqual(sel.latest_valid_run_id, run_view.run_id)

    def test_heat_exchanger_tq_plot_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            gateway = create_supervised_gateway(Path(temp_dir))
            draft = make_hx_draft("HxCase")

            val_out = gateway.dispatch(
                CommandRequest("draft.validate", "r-1", "a", c.DraftParameters(draft))
            )
            receipt = val_out.data
            assert isinstance(receipt, c.ValidationReceiptDto)

            run_out = gateway.dispatch(
                CommandRequest(
                    "run.start", "r-2", "a", StartRunParameters(draft, receipt.receipt_id)
                )
            )
            run_view = run_out.data
            assert isinstance(run_view, c.RunViewDto)

            # Request T-Q plot for heat exchanger
            plot_out = gateway.dispatch(
                CommandRequest(
                    "graph.plot",
                    "r-3",
                    "a",
                    PlotDataParameters(
                        case_id=draft.draft_id,
                        run_id=run_view.run_id,
                        plot_kind="T_Q",
                        unit_id="u:hx",
                    ),
                )
            )
            self.assertEqual(plot_out.disposition, "COMPLETED")
            plot = plot_out.data
            assert isinstance(plot, c.PlotDefinitionDto)

            self.assertEqual(plot.plot_kind, "T_Q")
            self.assertIn("T-Q", plot.title)
            self.assertEqual(len(plot.series), 2)

            hot_series = next(s for s in plot.series if s.series_id == "hot_stream")
            cold_series = next(s for s in plot.series if s.series_id == "cold_stream")

            # 2nd Law Check: Hot fluid cools, cold fluid heats, hot is warmer than cold everywhere
            hot_in = hot_series.points[0].y
            hot_out = hot_series.points[1].y
            cold_in = cold_series.points[0].y
            cold_out = cold_series.points[1].y

            self.assertGreater(hot_in, hot_out, "Hot fluid must cool across heat exchanger")
            self.assertGreater(cold_out, cold_in, "Cold fluid must warm across heat exchanger")
            self.assertGreater(hot_out, cold_in, "Hot fluid outlet must exceed cold fluid inlet")

            # Residual convergence plot
            conv_out = gateway.dispatch(
                CommandRequest(
                    "graph.plot",
                    "r-4",
                    "a",
                    PlotDataParameters(
                        case_id=draft.draft_id,
                        run_id=run_view.run_id,
                        plot_kind="RESIDUAL_CONVERGENCE",
                    ),
                )
            )
            self.assertEqual(conv_out.disposition, "COMPLETED")
            conv_plot = conv_out.data
            assert isinstance(conv_plot, c.PlotDefinitionDto)
            self.assertEqual(conv_plot.plot_kind, "RESIDUAL_CONVERGENCE")
            # Acyclic solve has no iterative residuals;
            # points must be empty without fabricated points
            self.assertEqual(len(conv_plot.series[0].points), 0)

    def test_four_status_truth_table_uncollapsed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            gateway = create_supervised_gateway(Path(temp_dir))
            draft = make_heater_draft("StatusMatrix")

            val_out = gateway.dispatch(
                CommandRequest("draft.validate", "r-1", "a", c.DraftParameters(draft))
            )
            receipt = val_out.data
            assert isinstance(receipt, c.ValidationReceiptDto)

            run_out = gateway.dispatch(
                CommandRequest(
                    "run.start", "r-2", "a", StartRunParameters(draft, receipt.receipt_id)
                )
            )
            run_view = run_out.data
            assert isinstance(run_view, c.RunViewDto)

            wb_out = gateway.dispatch(
                CommandRequest(
                    "workbook.inspect",
                    "r-3",
                    "a",
                    InspectWorkbookParameters(case_id=draft.draft_id, run_id=run_view.run_id),
                )
            )
            wb = wb_out.data
            assert isinstance(wb, c.WorkbookDto)

            # Four distinct status dimensions must exist as independent fields
            statuses = {
                "convergence": wb.convergence,
                "closure": wb.closure,
                "physical_validity": wb.physical_validity,
                "correlation_validity": wb.correlation_validity,
            }
            self.assertEqual(len(statuses), 4)
            self.assertIn(statuses["convergence"], ("CONVERGED", "FAILED", "NOT_RUN"))
            self.assertIn(statuses["closure"], ("PASSED", "FAILED", "NOT_CHECKED"))
            self.assertIn(
                statuses["physical_validity"], ("VALID", "EXTRAPOLATED", "INVALID", "UNKNOWN")
            )
            self.assertIn(
                statuses["correlation_validity"], ("VALID", "EXTRAPOLATED", "INVALID", "UNKNOWN")
            )

    def test_deleted_or_missing_elements_graceful(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            gateway = create_supervised_gateway(Path(temp_dir))
            # Case with no runs yet
            ov_out = gateway.dispatch(
                CommandRequest(
                    "result.overlays",
                    "r-1",
                    "a",
                    GetOverlaysParameters(case_id="NonExistentCase"),
                )
            )
            self.assertEqual(ov_out.disposition, "COMPLETED")
            ov = ov_out.data
            assert isinstance(ov, c.OverlaysDto)
            self.assertIsNone(ov.run_id)
            self.assertEqual(len(ov.streams), 0)
            self.assertEqual(len(ov.equipment), 0)
            self.assertFalse(ov.selection.is_stale)


if __name__ == "__main__":
    unittest.main()
