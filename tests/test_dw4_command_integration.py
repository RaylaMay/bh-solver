from __future__ import annotations

import sys
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path
from typing import cast

from bh_sim.adapters.desktop_preview import create_supervised_gateway
from bh_sim.adapters.worker_supervisor import WorkerSupervisor
from bh_sim.application.services import ApplicationServices
from bh_sim.boundary import contracts as c
from bh_sim.boundary.contracts import (
    CancelRunParameters,
    CommandRequest,
    DraftParameters,
    InspectAttemptParameters,
    InspectRunParameters,
    ListAttemptsParameters,
    StartRunParameters,
)


def make_sample_draft(draft_id: str) -> c.DraftDto:
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


class DW4CommandIntegrationTests(unittest.TestCase):
    def test_supervised_gateway_advertises_dw4_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            gateway = create_supervised_gateway(Path(temp_dir))
            names = gateway.command_names
            for expected in (
                "draft.validate",
                "run.start",
                "run.cancel",
                "run.inspect",
                "run.inspect_attempt",
                "run.list_attempts",
                "run.select_last_valid",
                "run.compare",
            ):
                self.assertIn(expected, names)

    def test_validate_and_run_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            gateway = create_supervised_gateway(Path(temp_dir))
            draft = make_sample_draft("RadiatorLoop")

            # 1. Validate
            val_req = CommandRequest(
                "draft.validate", "req:val:1", "engineer", DraftParameters(draft)
            )
            val_outcome = gateway.dispatch(val_req)
            self.assertEqual(val_outcome.disposition, "COMPLETED")
            receipt = val_outcome.data
            assert isinstance(receipt, c.ValidationReceiptDto)
            self.assertTrue(receipt.validation.valid)

            # 2. Run
            run_req = CommandRequest(
                "run.start",
                "req:run:1",
                "engineer",
                StartRunParameters(draft, receipt.receipt_id),
            )
            run_outcome = gateway.dispatch(run_req)
            self.assertEqual(run_outcome.disposition, "COMPLETED")
            run_view = run_outcome.data
            assert isinstance(run_view, c.RunViewDto)
            self.assertEqual(run_view.convergence, "CONVERGED")
            self.assertEqual(run_view.closure, "PASSED")

            # 3. List Attempts
            list_att_req = CommandRequest(
                "run.list_attempts",
                "req:att:list",
                "engineer",
                ListAttemptsParameters(case_id=draft.draft_id),
            )
            list_att_outcome = gateway.dispatch(list_att_req)
            self.assertEqual(list_att_outcome.disposition, "COMPLETED")
            attempts = list_att_outcome.data
            assert isinstance(attempts, tuple)
            self.assertEqual(len(attempts), 1)
            attempt = attempts[0]
            assert isinstance(attempt, c.RunAttemptRecord)
            self.assertEqual(attempt.state, "COMPLETED")
            self.assertTrue(attempt.persisted)

            # 4. Inspect Attempt
            insp_att_req = CommandRequest(
                "run.inspect_attempt",
                "req:att:1",
                "engineer",
                InspectAttemptParameters(attempt.attempt_id),
            )
            insp_att_outcome = gateway.dispatch(insp_att_req)
            self.assertEqual(insp_att_outcome.disposition, "COMPLETED")
            assert isinstance(insp_att_outcome.data, c.RunAttemptRecord)
            self.assertEqual(insp_att_outcome.data.attempt_id, attempt.attempt_id)

            # 5. Inspect Run
            insp_run_req = CommandRequest(
                "run.inspect",
                "req:run:insp",
                "engineer",
                InspectRunParameters(run_view.run_id),
            )
            insp_run_outcome = gateway.dispatch(insp_run_req)
            self.assertEqual(insp_run_outcome.disposition, "COMPLETED")
            assert isinstance(insp_run_outcome.data, c.RunViewDto)
            self.assertEqual(insp_run_outcome.data.run_id, run_view.run_id)

    def test_stale_validation_rejection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            gateway = create_supervised_gateway(Path(temp_dir))
            draft = make_sample_draft("RadiatorLoop")

            val_req = CommandRequest(
                "draft.validate", "req:val:1", "engineer", DraftParameters(draft)
            )
            val_outcome = gateway.dispatch(val_req)
            receipt = val_outcome.data
            assert isinstance(receipt, c.ValidationReceiptDto)

            # Modify draft inputs
            modified_heater = c.EquipmentDto(
                "u:heat",
                "heater",
                (c.ParameterDto("duty", c.QuantityDto(99999.0, "W")),),
            )
            modified_draft = c.DraftDto(
                draft_id=draft.draft_id,
                revision=draft.revision,
                base_case_id=None,
                updated_at=draft.updated_at,
                equipment=(draft.equipment[0], modified_heater, draft.equipment[2]),
                connections=draft.connections,
                presentation=draft.presentation,
            )

            # Attempt to run with stale receipt
            stale_run_req = CommandRequest(
                "run.start",
                "req:run:stale",
                "engineer",
                StartRunParameters(modified_draft, receipt.receipt_id),
            )
            outcome = gateway.dispatch(stale_run_req)
            self.assertEqual(outcome.disposition, "REJECTED")
            self.assertEqual(outcome.diagnostics[0].code, "STALE_VALIDATION")

    def test_cancel_in_flight_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            gateway = create_supervised_gateway(Path(temp_dir))
            services = cast(ApplicationServices, gateway.services)
            attempt = c.RunAttemptRecord(
                attempt_id="att:cancel:1",
                run_id="run:cancel:1",
                case_id="case:c",
                engineering_hash="eng_hash",
                context_hash="ctx_hash",
                state="RUNNING",
                admitted_at="2026-09-15T00:00:00Z",
            )
            services.artifacts.record_attempt(attempt)

            cancel_req = CommandRequest(
                "run.cancel",
                "req:can:1",
                "engineer",
                CancelRunParameters(run_id="run:cancel:1", reason="User stopped"),
            )
            outcome = gateway.dispatch(cancel_req)
            self.assertEqual(outcome.disposition, "COMPLETED")
            cancelled_att = outcome.data
            assert isinstance(cancelled_att, c.RunAttemptRecord)
            self.assertEqual(cancelled_att.state, "CANCELLED")
            self.assertEqual(cancelled_att.failure_reason, "User stopped")

    def test_supervised_child_process_end_to_end(self) -> None:
        mock_worker_py = Path(__file__).resolve().parent / "fixtures" / "mock_worker_entry.py"
        with tempfile.TemporaryDirectory() as temp_dir:
            supervisor = WorkerSupervisor(worker_command=[sys.executable, str(mock_worker_py)])
            supervisor.start(timeout=5.0)
            self.assertTrue(supervisor.is_alive())

            try:
                gateway = create_supervised_gateway(Path(temp_dir), supervisor=supervisor)
                draft = make_sample_draft("ProcessLoop")

                # Validate over child process
                val_req = CommandRequest(
                    "draft.validate", "req:spv:val", "engineer", DraftParameters(draft)
                )
                val_outcome = gateway.dispatch(val_req)
                self.assertEqual(val_outcome.disposition, "COMPLETED")
                receipt = val_outcome.data
                assert isinstance(receipt, c.ValidationReceiptDto)
                self.assertTrue(receipt.validation.valid)

                # Run over child process
                run_req = CommandRequest(
                    "run.start",
                    "req:spv:run",
                    "engineer",
                    StartRunParameters(draft, receipt.receipt_id),
                )
                run_outcome = gateway.dispatch(run_req)
                self.assertEqual(run_outcome.disposition, "COMPLETED")
                run_view = run_outcome.data
                assert isinstance(run_view, c.RunViewDto)
                self.assertEqual(run_view.convergence, "CONVERGED")

                # Verify attempt was recorded in SQLite
                services = cast(ApplicationServices, gateway.services)
                attempts = services.list_attempts("ProcessLoop")
                self.assertEqual(len(attempts), 1)
                self.assertEqual(attempts[0].state, "COMPLETED")
                self.assertTrue(attempts[0].persisted)
            finally:
                supervisor.stop()

    def test_undo_does_not_mutate_or_delete_attempts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            gateway = create_supervised_gateway(Path(temp_dir))
            draft = make_sample_draft("UndoIsolationLoop")

            val_outcome = gateway.dispatch(
                CommandRequest("draft.validate", "r:v", "eng", DraftParameters(draft))
            )
            receipt = val_outcome.data
            assert isinstance(receipt, c.ValidationReceiptDto)
            run_outcome = gateway.dispatch(
                CommandRequest(
                    "run.start", "r:r", "eng", StartRunParameters(draft, receipt.receipt_id)
                )
            )
            self.assertEqual(run_outcome.disposition, "COMPLETED")

            services = cast(ApplicationServices, gateway.services)
            attempts_before = services.list_attempts("UndoIsolationLoop")
            self.assertEqual(len(attempts_before), 1)

            # Perform history undo
            target = c.HistoryTarget("UndoIsolationLoop", "entry:0")
            undo_req = CommandRequest("history.undo", "req:undo", "eng", target)
            gateway.dispatch(undo_req)

            # Confirm attempt history remains completely unchanged
            attempts_after = services.list_attempts("UndoIsolationLoop")
            self.assertEqual(len(attempts_after), 1)
            self.assertEqual(attempts_after[0].attempt_id, attempts_before[0].attempt_id)
            self.assertEqual(attempts_after[0].state, "COMPLETED")

    def test_stale_validation_on_worker_session_restart(self) -> None:
        mock_worker_py = Path(__file__).resolve().parent / "fixtures" / "mock_worker_entry.py"
        with tempfile.TemporaryDirectory() as temp_dir:
            supervisor = WorkerSupervisor(worker_command=[sys.executable, str(mock_worker_py)])
            supervisor.start(timeout=5.0)
            try:
                gateway = create_supervised_gateway(Path(temp_dir), supervisor=supervisor)
                draft = make_sample_draft("RestartLoop")

                # Validate under initial worker session
                val_req = CommandRequest(
                    "draft.validate", "req:v1", "engineer", DraftParameters(draft)
                )
                val_outcome = gateway.dispatch(val_req)
                self.assertEqual(val_outcome.disposition, "COMPLETED")
                receipt = val_outcome.data
                assert isinstance(receipt, c.ValidationReceiptDto)
                self.assertEqual(receipt.worker_session_id, supervisor.session_id)

                # Worker process restarts -> new session_id
                supervisor.stop()
                supervisor.start(timeout=5.0)
                self.assertNotEqual(receipt.worker_session_id, supervisor.session_id)

                # Attempting to start run with stale receipt must be rejected
                run_req = CommandRequest(
                    "run.start",
                    "req:r1",
                    "engineer",
                    StartRunParameters(draft, receipt.receipt_id),
                )
                run_outcome = gateway.dispatch(run_req)
                self.assertEqual(run_outcome.disposition, "REJECTED")
                codes = [d.code for d in run_outcome.diagnostics]
                self.assertIn("STALE_VALIDATION", codes)
            finally:
                supervisor.stop()

    def test_empty_staged_path_rejects_with_persistence_failed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            draft = make_sample_draft("EmptyStagedLoop")

            class MockEmptyStagedSupervisor:
                session_id = "mock-empty-sess"

                def is_alive(self) -> bool:
                    return True

                def validate(self, draft: object, eng_hash: str, ctx: str) -> object:
                    from bh_sim.boundary.contracts import WorkerValidateResponse

                    return WorkerValidateResponse(
                        request_id="req",
                        valid=True,
                        dof=0,
                        engineering_hash=eng_hash,
                        context_hash=ctx,
                        diagnostics=(),
                    )

                def execute_job(
                    self,
                    job: object,
                    on_progress: object = None,
                    timeout: float = 0.0,
                    cancellation_requested: Callable[[], bool] | None = None,
                ) -> object:
                    return c.WorkerCompletedEvent(
                        run_id=getattr(job, "run_id", "run-1"),
                        worker_session_id=self.session_id,
                        sequence=1,
                        timestamp="2026-09-16T00:00:00Z",
                        artifact_hash="hash-empty",
                        staged_path="",  # Empty staged artifact path!
                        convergence="converged",
                        closure="passed",
                        physical_validity="valid",
                        correlation_validity="valid",
                        execution_duration_ms=5.0,
                    )

            mock_spv = MockEmptyStagedSupervisor()
            gateway = create_supervised_gateway(Path(temp_dir), supervisor=mock_spv)

            val_outcome = gateway.dispatch(
                CommandRequest("draft.validate", "v:1", "eng", DraftParameters(draft))
            )
            receipt = val_outcome.data
            assert isinstance(receipt, c.ValidationReceiptDto)

            run_outcome = gateway.dispatch(
                CommandRequest(
                    "run.start", "r:1", "eng", StartRunParameters(draft, receipt.receipt_id)
                )
            )
            self.assertEqual(run_outcome.disposition, "REJECTED")
            codes = [d.code for d in run_outcome.diagnostics]
            self.assertIn("PERSISTENCE_FAILED", codes)

            # Check that attempt was marked FAILED and persisted=False
            services = cast(ApplicationServices, gateway.services)
            attempts = services.list_attempts("EmptyStagedLoop")
            self.assertEqual(len(attempts), 1)
            self.assertEqual(attempts[0].state, "FAILED")
            self.assertFalse(attempts[0].persisted)
