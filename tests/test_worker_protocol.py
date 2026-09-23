"""Test DW4 worker IPC protocol contracts, serialization, and stream framing."""

from __future__ import annotations

import io
import struct

import pytest

from bh_sim.boundary import contracts as c
from bh_sim.boundary.json_codec import boundary_from_json, boundary_json
from bh_sim.boundary.worker_framing import (
    MAX_FRAME_SIZE,
    FrameSizeError,
    FramingError,
    read_frame,
    write_frame,
)


def sample_draft() -> c.DraftDto:
    return c.DraftDto(
        "case-1",
        1,
        None,
        "2026-09-15T00:00:00Z",
        (),
        (),
        c.PresentationDto(()),
    )


def test_worker_hello_and_ready_roundtrip() -> None:
    hello = c.WorkerHello(
        ("2026-09-15.dw4alpha",),
        "session-123",
        12345,
        ("acyclic_flowshet", "steady_state"),
        "0.1.0",
    )
    serialized = boundary_json(hello)
    restored = boundary_from_json(serialized)
    assert restored == hello

    ready = c.WorkerReady(
        "2026-09-15.dw4alpha",
        "session-123",
        True,
        "Worker accepted",
    )
    assert boundary_from_json(boundary_json(ready)) == ready


def test_run_job_and_events_roundtrip() -> None:
    draft = sample_draft()
    job = c.RunJob(
        job_id="job-1",
        run_id="run-1",
        case_id="case-1",
        revision_id=1,
        engineering_hash="e" * 64,
        context_hash="c" * 64,
        draft=draft,
    )
    assert boundary_from_json(boundary_json(job)) == job

    accepted = c.RunAccepted(
        job_id="job-1",
        run_id="run-1",
        worker_session_id="session-123",
        admitted_at="2026-09-15T00:00:01Z",
    )
    assert boundary_from_json(boundary_json(accepted)) == accepted

    progress = c.WorkerProgressEvent(
        run_id="run-1",
        worker_session_id="session-123",
        sequence=1,
        timestamp="2026-09-15T00:00:02Z",
        iteration=5,
        residual_norm=1.23e-5,
        message="Iteration 5",
    )
    assert boundary_from_json(boundary_json(progress)) == progress

    completed = c.WorkerCompletedEvent(
        run_id="run-1",
        worker_session_id="session-123",
        sequence=2,
        timestamp="2026-09-15T00:00:03Z",
        artifact_hash="a" * 64,
        staged_path="/tmp/staged_artifact.json",
        convergence="converged",
        closure="passed",
        physical_validity="valid",
        correlation_validity="valid",
        execution_duration_ms=45.2,
        manifest=(("solver", "scipy"), ("platform", "darwin")),
    )
    assert boundary_from_json(boundary_json(completed)) == completed

    attempt = c.RunAttemptRecord(
        attempt_id="att-1",
        run_id="run-1",
        case_id="case-1",
        engineering_hash="e" * 64,
        context_hash="c" * 64,
        state="ADMITTED",
        admitted_at="2026-09-15T00:00:01Z",
    )
    assert boundary_from_json(boundary_json(attempt)) == attempt


def test_framing_write_and_read_sequential_frames() -> None:
    stream = io.BytesIO()
    msg1 = c.WorkerHello(("2026-09-15.dw4alpha",), "sess-1", 999, ("solve",), "0.1.0")
    msg2 = c.CancelRunRequest(run_id="run-1", reason="User cancel")
    msg3 = c.WorkerShutdownRequest(reason="Clean exit")

    write_frame(stream, msg1)
    write_frame(stream, msg2)
    write_frame(stream, msg3)

    stream.seek(0)
    assert read_frame(stream) == msg1
    assert read_frame(stream) == msg2
    assert read_frame(stream) == msg3
    assert read_frame(stream) is None  # Clean EOF


def test_framing_rejects_oversized_frame() -> None:
    stream = io.BytesIO()
    oversized_length = MAX_FRAME_SIZE + 1
    stream.write(struct.pack("!I", oversized_length))
    stream.seek(0)
    with pytest.raises(FrameSizeError):
        read_frame(stream)


def test_framing_detects_incomplete_frame() -> None:
    stream = io.BytesIO(b"\x00\x00")  # Only 2 bytes instead of 4
    with pytest.raises(FramingError):
        read_frame(stream)

    stream2 = io.BytesIO(struct.pack("!I", 100) + b"too short")
    with pytest.raises(FramingError):
        read_frame(stream2)
