"""Test WorkerSupervisor child process management, handshake, execution, and crash containment."""

from __future__ import annotations

import io
import sys
import threading
from pathlib import Path

import pytest

from bh_sim.adapters.worker_supervisor import (
    WorkerLostError,
    WorkerSupervisor,
    WorkerTimeoutError,
)
from bh_sim.boundary import contracts as c
from bh_sim.boundary.worker_framing import read_frame, write_frame
from bh_sim.worker.entry import run_worker_loop


class DummyMockAdapter:
    """Mock calculation adapter for fast deterministic tests without external libraries."""

    def __init__(self) -> None:
        self._ctx = "mock_context_hash_123"

    def context_hash(self) -> str:
        return self._ctx

    def prepare(self, draft: c.DraftDto) -> c.PreparedRevisionDto:
        return c.PreparedRevisionDto(
            case_id=draft.draft_id,
            revision_id="1",
            case_json='{"case_id": "' + draft.draft_id + '"}',
            revision_json='{"revision_id": 1}',
            source_artifact_hash="mock_source_hash",
            engineering_hash="mock_engineering_hash",
            node_ids=(),
            edge_ids=(),
        )

    def validate(self, prepared: c.PreparedRevisionDto) -> c.ValidationDto:
        return c.ValidationDto(valid=True, degrees_of_freedom=0, diagnostics=())

    def run(
        self,
        prepared: c.PreparedRevisionDto,
        *,
        run_id: str | None = None,
        expected_context_hash: str | None = None,
        **kwargs: object,
    ) -> object:
        from collections import namedtuple

        RunResultMock = namedtuple(
            "RunResultMock", ["convergence", "closure", "physical_validity", "correlation_validity"]
        )
        StatusMock = namedtuple("StatusMock", ["value"])
        CalculatedMock = namedtuple("CalculatedMock", ["run_id", "result"])

        return CalculatedMock(
            run_id=run_id or "run-1",
            result=RunResultMock(
                convergence=StatusMock("converged"),
                closure=StatusMock("passed"),
                physical_validity=StatusMock("valid"),
                correlation_validity=StatusMock("valid"),
            ),
        )


def test_run_worker_loop_in_memory() -> None:
    """Test worker message loop protocol directly via in-memory pipes."""
    supervisor_to_worker = io.BytesIO()
    worker_to_supervisor = io.BytesIO()

    # We will run worker in a thread
    def worker_thread_target() -> None:
        run_worker_loop(
            supervisor_to_worker, worker_to_supervisor, adapter_factory=DummyMockAdapter
        )

    # Pre-populate supervisor input for worker:
    # 1. WorkerReady
    write_frame(
        supervisor_to_worker,
        c.WorkerReady(
            selected_protocol=c.WORKER_PROTOCOL_VERSION,
            worker_session_id="test-session",
            accepted=True,
        ),
    )
    # 2. WorkerShutdownRequest
    write_frame(supervisor_to_worker, c.WorkerShutdownRequest())
    supervisor_to_worker.seek(0)

    thread = threading.Thread(target=worker_thread_target)
    thread.start()
    thread.join(timeout=3.0)
    assert not thread.is_alive()

    # Read frames emitted by worker
    worker_to_supervisor.seek(0)
    hello = read_frame(worker_to_supervisor)
    assert isinstance(hello, c.WorkerHello)
    assert hello.protocol_version == c.WORKER_PROTOCOL_VERSION


def test_supervisor_worker_crash_containment() -> None:
    """Test that supervisor detects worker crash and raises WorkerLostError without freezing."""
    supervisor = WorkerSupervisor(worker_command=[sys.executable, "-c", "import sys; sys.exit(42)"])
    with pytest.raises((WorkerLostError, WorkerTimeoutError)):
        supervisor.start(timeout=1.0)
    assert not supervisor.is_alive()


def test_supervisor_child_process_e2e_lifecycle() -> None:
    """Test full child process execution: handshake, validate, run_job, and clean stop."""
    supervisor = WorkerSupervisor(
        worker_command=[sys.executable, "tests/fixtures/mock_worker_entry.py"]
    )
    supervisor.start(timeout=5.0)
    assert supervisor.is_alive()
    assert supervisor.session_id is not None
    assert supervisor.worker_pid is not None

    draft = c.DraftDto("test-case", 1, None, "2026-09-15T00:00:00Z", (), (), c.PresentationDto(()))

    # 1. Validation over IPC
    val_resp = supervisor.validate(draft, "eng_hash_1", "ctx_hash_1", timeout=5.0)
    assert val_resp.valid is True
    assert val_resp.engineering_hash == "mock_engineering_hash"

    # 2. Run execution over IPC
    progress_events: list[c.WorkerProgressEvent] = []
    job = c.RunJob(
        job_id="job-100",
        run_id="run:100",
        case_id="test-case",
        revision_id=1,
        engineering_hash="mock_engineering_hash",
        context_hash="mock_context_hash_123",
        draft=draft,
    )
    outcome = supervisor.execute_job(job, on_progress=progress_events.append, timeout=5.0)
    assert isinstance(outcome, c.WorkerCompletedEvent)
    assert outcome.run_id == "run:100"
    assert outcome.convergence == "converged"
    assert ":" not in Path(outcome.staged_path).name
    assert len(Path(outcome.staged_path).stem) == 64
    assert len(progress_events) >= 1

    # 3. Clean shutdown
    supervisor.stop()
    assert not supervisor.is_alive()


def test_supervisor_quarantines_mismatched_protocol_version() -> None:
    """Test that supervisor drops incoming frames with unsupported protocol version."""
    import queue

    supervisor = WorkerSupervisor(worker_command=[])
    supervisor._negotiated_protocol = c.WORKER_PROTOCOL_VERSION
    supervisor._session_id = "test-session"

    bad_msg = c.WorkerCompletedEvent(
        run_id="run-test",
        worker_session_id="test-session",
        sequence=1,
        timestamp="2026-09-15T00:00:00Z",
        artifact_hash="hash-1",
        staged_path="/tmp/test",
        convergence="converged",
        closure="passed",
        physical_validity="valid",
        correlation_validity="valid",
        execution_duration_ms=10.0,
        protocol_version="unsupported-v99",
    )
    good_msg = c.WorkerCompletedEvent(
        run_id="run-test",
        worker_session_id="test-session",
        sequence=2,
        timestamp="2026-09-15T00:00:01Z",
        artifact_hash="hash-2",
        staged_path="/tmp/test",
        convergence="converged",
        closure="passed",
        physical_validity="valid",
        correlation_validity="valid",
        execution_duration_ms=12.0,
        protocol_version=c.WORKER_PROTOCOL_VERSION,
    )

    stream = io.BytesIO()
    write_frame(stream, bad_msg)
    write_frame(stream, good_msg)
    stream.seek(0)

    q: queue.Queue[object] = queue.Queue()
    supervisor._active_jobs["run-test"] = q

    # Run reader loop directly on the in-memory stream (terminates on stream EOF)
    supervisor._reader_loop(stream)

    # The bad message was quarantined; only the good message reached the queue!
    assert q.qsize() == 1
    received = q.get_nowait()
    assert isinstance(received, c.WorkerCompletedEvent)
    assert received.sequence == 2
    assert received.protocol_version == c.WORKER_PROTOCOL_VERSION
