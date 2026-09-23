"""Regression evidence for the six findings in the third DW4/DW5 review.

Faults use disposable stores; child probes execute the real worker loop and
reference adapter. Delays exercise lifecycle control, not scientific performance.
"""

from __future__ import annotations

import sys
import threading
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest

from bh_sim.adapters.worker_supervisor import WorkerLostError, WorkerSupervisor
from bh_sim.application.services import CommandRejected
from bh_sim.boundary import contracts as c
from bh_sim.composition import create_services
from bh_sim.persistence import PersistenceStore
from tests.test_dw4_command_integration import make_sample_draft


def running_attempt() -> c.RunAttemptRecord:
    return c.RunAttemptRecord(
        "att:fault",
        "run:fault",
        "case:fault",
        "e",
        "c",
        "RUNNING",
        "2026-09-23T00:00:00Z",
    )


def test_manifest_failure_retry_and_index_loss(tmp_path: Path) -> None:
    store = PersistenceStore(tmp_path)
    running = running_attempt()
    completed = replace(
        running,
        state="COMPLETED",
        terminal_at="2026-09-23T00:00:01Z",
        artifact_hash="a" * 64,
        persisted=True,
    )
    store.record_attempt(running)
    with (
        patch.object(store, "_write_attempt_manifest", side_effect=OSError("disk full")),
        pytest.raises(OSError),
    ):
        store.record_attempt(completed)
    assert store.index.get_attempt(running.attempt_id) == running
    assert store.get_attempt(running.attempt_id) == running
    assert store.record_attempt(completed) == completed
    manifest_path = store._attempt_path(running.attempt_id)
    before = manifest_path.read_bytes()
    with pytest.raises(ValueError):
        store.record_attempt(replace(completed, engineering_hash="changed"))
    assert store.record_attempt(replace(completed, state="CANCELLED")) == completed
    assert manifest_path.read_bytes() == before
    (tmp_path / "index.sqlite3").unlink()
    restored = PersistenceStore(tmp_path)
    restored.rebuild_index_from_artifacts()
    assert restored.index.get_attempt(running.attempt_id) == completed


def test_index_failure_after_json_is_repairable(tmp_path: Path) -> None:
    store = PersistenceStore(tmp_path)
    running = running_attempt()
    completed = replace(running, state="COMPLETED", terminal_at="2026-09-23T00:00:01Z")
    store.record_attempt(running)
    session = store.index._session

    @contextmanager
    def failed_commit() -> Iterator[object]:
        with session() as connection:
            yield connection
            raise OSError("index commit unavailable")

    with patch.object(store.index, "_session", failed_commit), pytest.raises(OSError):
        store.record_attempt(completed)
    assert store.index.get_attempt(running.attempt_id) == running
    assert store.get_attempt(running.attempt_id) == completed
    assert store.record_attempt(completed) == completed
    assert store.index.get_attempt(running.attempt_id) == completed


def test_cancelled_attempt_never_acquires_late_persistence_ack(tmp_path: Path) -> None:
    store = PersistenceStore(tmp_path)
    cancelled = replace(running_attempt(), state="CANCELLED", terminal_at="2026-09-23T00:00:01Z")
    store.record_attempt(cancelled)
    late = replace(cancelled, state="COMPLETED", artifact_hash="b" * 64, persisted=True)
    assert store.record_attempt(late) == cancelled
    assert store.get_attempt(cancelled.attempt_id) == cancelled


def test_dead_configured_worker_rejects_validate_and_run(tmp_path: Path) -> None:
    supervisor = WorkerSupervisor()
    supervisor.start()
    try:
        services = create_services(tmp_path, supervisor=supervisor)
        draft = make_sample_draft("worker-loss")
        receipt = services.validate_draft(draft)
        supervisor.stop()
        with patch.object(services.engineering, "run") as local_run:
            for action in (
                lambda: services.validate_draft(draft),
                lambda: services.start_run(draft, receipt.receipt_id),
            ):
                with pytest.raises(CommandRejected) as rejection:
                    action()
                assert rejection.value.code == "WORKER_UNAVAILABLE"
            local_run.assert_not_called()
        assert services.list_attempts() == ()
        supervisor.start()
        with pytest.raises(CommandRejected) as rejection:
            services.start_run(draft, receipt.receipt_id)
        assert rejection.value.code == "STALE_VALIDATION"
        current = services.validate_draft(draft)
        assert services.start_run(draft, current.receipt_id).convergence == "CONVERGED"
    finally:
        supervisor.stop()


@pytest.mark.parametrize("published_before_error", [False, True])
def test_result_storage_failure_retains_terminal_identity(
    tmp_path: Path,
    published_before_error: bool,
) -> None:
    services = create_services(tmp_path)
    draft = make_sample_draft("save-failure")
    receipt = services.validate_draft(draft)
    real_save = services.artifacts.save_run

    def fail(result: c.CalculatedRunDto) -> None:
        if published_before_error:
            real_save(result)
        raise OSError("disk full")

    with (
        patch.object(services.artifacts, "save_run", fail),
        pytest.raises(CommandRejected) as rejection,
    ):
        services.start_run(draft, receipt.receipt_id)
    assert rejection.value.code == "PERSISTENCE_FAILED"
    (attempt,) = services.list_attempts()
    assert attempt.state == "FAILED" and attempt.terminal_at and attempt.failure_reason
    assert not attempt.persisted
    retained = services._unpersisted_runs[attempt.run_id]
    assert attempt.artifact_hash == retained.view.artifact.content_hash
    assert services.last_valid_run(attempt.case_id) is None
    # A normal reopen retains the failure without replaying computation.
    reopened = create_services(tmp_path)
    assert reopened.list_attempts() == (attempt,)
    assert reopened.last_valid_run(attempt.case_id) is None


def test_local_cancel_wins_publication_and_blocks_duplicate_run(tmp_path: Path) -> None:
    services = create_services(tmp_path)
    draft = make_sample_draft("cancel-race")
    receipt = services.validate_draft(draft)
    entered, release = threading.Event(), threading.Event()
    real_run = services.engineering.run

    def delayed(
        prepared: c.PreparedRevisionDto,
        *,
        run_id: str | None = None,
        expected_context_hash: str | None = None,
    ) -> c.CalculatedRunDto:
        entered.set()
        assert release.wait(5)
        return real_run(prepared, run_id=run_id, expected_context_hash=expected_context_hash)

    with patch.object(services.engineering, "run", delayed), ThreadPoolExecutor() as pool:
        future = pool.submit(services.start_run, draft, receipt.receipt_id)
        try:
            assert entered.wait(5)
            with pytest.raises(CommandRejected) as busy:
                services.start_run(draft, receipt.receipt_id)
            assert busy.value.code == "RUN_BUSY"
            cancelled = services.cancel_run("")
            assert cancelled and cancelled.state == "CANCELLED"
        finally:
            release.set()
        with pytest.raises(CommandRejected) as rejection:
            future.result(timeout=5)
    assert rejection.value.code == "RUN_CANCELLED"
    (attempt,) = services.list_attempts()
    assert attempt == cancelled and not attempt.persisted
    assert services.last_valid_run(attempt.case_id) is None
    with pytest.raises(KeyError):
        services.inspect_run(attempt.run_id)


@pytest.mark.parametrize("delay,grace,cooperative", [(0.2, 1.0, True), (5.0, 0.2, False)])
def test_real_worker_cancel_control_and_bounded_escalation(
    tmp_path: Path,
    delay: float,
    grace: float,
    cooperative: bool,
) -> None:
    worker = Path(__file__).parent / "fixtures" / "delayed_worker_entry.py"
    started = threading.Event()
    supervisor = WorkerSupervisor(
        worker_command=[sys.executable, str(worker), str(delay)],
        on_progress=lambda _: started.set(),
        cancellation_grace_seconds=grace,
    )
    supervisor.start()
    try:
        services = create_services(tmp_path, supervisor=supervisor)
        draft = make_sample_draft("child-cancel")
        receipt = services.validate_draft(draft)
        prepared = services.engineering.prepare(draft)
        job = c.RunJob(
            "job:cancel",
            "run:cancel",
            prepared.case_id,
            draft.revision,
            prepared.engineering_hash,
            receipt.execution_context_hash,
            draft,
        )
        with ThreadPoolExecutor() as pool:
            future = pool.submit(supervisor.execute_job, job)
            assert started.wait(5)
            began = time.monotonic()
            supervisor.cancel(job.run_id)
            if cooperative:
                event = future.result(timeout=3)
                assert isinstance(event, c.WorkerCancelledEvent) and event.safe_boundary_reached
                # The deadline for this completed job must not kill the healthy child.
                time.sleep(grace + 0.1)
                assert supervisor.is_alive()
            else:
                with pytest.raises(WorkerLostError):
                    future.result(timeout=3)
                assert time.monotonic() - began < grace + 2.0
                assert not supervisor.is_alive()
            assert supervisor._active_jobs == {}
            assert supervisor._cancel_timers == {}
    finally:
        supervisor.stop()


def test_admission_write_failure_retains_failed_audit_without_execution(tmp_path: Path) -> None:
    services = create_services(tmp_path)
    draft = make_sample_draft("admission-failure")
    receipt = services.validate_draft(draft)
    with (
        patch.object(services.artifacts, "record_attempt", side_effect=OSError("disk full")),
        patch.object(services.engineering, "run") as run,
        pytest.raises(CommandRejected) as rejection,
    ):
        services.start_run(draft, receipt.receipt_id)
    assert rejection.value.code == "PERSISTENCE_FAILED"
    run.assert_not_called()
    (attempt,) = services.list_attempts()
    assert attempt.state == "FAILED" and attempt.terminal_at and attempt.failure_reason
    assert not attempt.persisted and services._active_run_id is None
    assert services.inspect_attempt(attempt.attempt_id) == attempt


def test_cancel_before_worker_registration_prevents_dispatch(tmp_path: Path) -> None:
    from collections.abc import Callable

    supervisor = WorkerSupervisor()
    supervisor.start()
    entered, release = threading.Event(), threading.Event()
    try:
        services = create_services(tmp_path, supervisor=supervisor)
        draft = make_sample_draft("pre-dispatch-cancel")
        receipt = services.validate_draft(draft)
        real_execute = supervisor.execute_job

        def delayed_admission(
            job: c.RunJob,
            *,
            cancellation_requested: Callable[[], bool] | None = None,
        ) -> c.WorkerCompletedEvent | c.WorkerFailedEvent | c.WorkerCancelledEvent:
            entered.set()
            assert release.wait(5)
            return real_execute(job, cancellation_requested=cancellation_requested)

        with (
            patch.object(supervisor, "execute_job", delayed_admission),
            ThreadPoolExecutor() as pool,
        ):
            future = pool.submit(services.start_run, draft, receipt.receipt_id)
            try:
                assert entered.wait(5) and supervisor._active_jobs == {}
                cancelled = services.cancel_run("")
                assert cancelled and cancelled.state == "CANCELLED"
            finally:
                release.set()
            with pytest.raises(CommandRejected) as rejection:
                future.result(timeout=2)
            assert rejection.value.code == "RUN_CANCELLED"
        assert supervisor.is_alive() and supervisor._active_jobs == {}
        assert supervisor._last_sequence == {}  # No RunJob or progress was sent.
        assert services.last_valid_run(cancelled.case_id) is None
    finally:
        supervisor.stop()


def test_worker_rejects_concurrent_validation_without_queuing(tmp_path: Path) -> None:
    worker = Path(__file__).parent / "fixtures" / "delayed_worker_entry.py"
    started = threading.Event()
    supervisor = WorkerSupervisor(
        worker_command=[sys.executable, str(worker), "1.0"],
        on_progress=lambda _: started.set(),
    )
    supervisor.start()
    try:
        services = create_services(tmp_path, supervisor=supervisor)
        draft = make_sample_draft("worker-busy")
        receipt = services.validate_draft(draft)
        prepared = services.engineering.prepare(draft)
        job = c.RunJob(
            "job:busy",
            "run:busy",
            prepared.case_id,
            draft.revision,
            prepared.engineering_hash,
            receipt.execution_context_hash,
            draft,
        )
        with ThreadPoolExecutor() as pool:
            future = pool.submit(supervisor.execute_job, job)
            assert started.wait(5)
            response = supervisor.validate(
                draft, prepared.engineering_hash, receipt.execution_context_hash, timeout=0.5
            )
            assert not response.valid and response.diagnostics[0].code == "WORKER_BUSY"
            assert isinstance(future.result(timeout=3), c.WorkerCompletedEvent)
    finally:
        supervisor.stop()
