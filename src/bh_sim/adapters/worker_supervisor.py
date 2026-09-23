"""Application-side supervisor managing child worker process lifecycle and IPC.

Communicates over standard I/O pipes using length-prefixed boundary JSON frames.
Runs non-blocking reader threads to drain progress/events without stalling the GUI.
"""

from __future__ import annotations

import math
import os
import queue
import subprocess
import sys
import threading
import time
import uuid
from collections.abc import Callable
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, BinaryIO, cast

from bh_sim.boundary import contracts as c
from bh_sim.boundary.worker_framing import read_frame, write_frame


class SupervisorError(RuntimeError):
    """Base error for supervisor and IPC failures."""


class WorkerLostError(SupervisorError):
    """Raised when the worker child process terminates unexpectedly."""


class WorkerTimeoutError(SupervisorError):
    """Raised when a worker operation times out."""


class WorkerSupervisor:
    """Supervises a spawned solver child process over standard I/O pipes."""

    def __init__(
        self,
        worker_command: list[str] | None = None,
        on_progress: Callable[[c.WorkerProgressEvent], None] | None = None,
        on_diagnostic: Callable[[c.WorkerDiagnosticEvent], None] | None = None,
        on_worker_lost: Callable[[int], None] | None = None,
        cancellation_grace_seconds: float = 1.0,
    ) -> None:
        if not math.isfinite(cancellation_grace_seconds) or cancellation_grace_seconds <= 0:
            raise ValueError("Cancellation grace must be a positive finite number of seconds")
        self.cancellation_grace_seconds = cancellation_grace_seconds
        self._cancel_timers: dict[str, threading.Timer] = {}
        self._command = worker_command or [sys.executable, "-m", "bh_sim.worker.entry"]
        self._process: subprocess.Popen[bytes] | None = None
        self._session_id: str | None = None
        self._worker_pid: int | None = None
        self._lock = threading.RLock()
        self._reader_thread: threading.Thread | None = None
        self._stderr_thread: threading.Thread | None = None
        self._last_sequence: dict[str, int] = {}
        self._pending_responses: dict[str, queue.Queue[Any]] = {}
        self._active_jobs: dict[str, queue.Queue[Any]] = {}
        self._on_progress = on_progress
        self._on_diagnostic = on_diagnostic
        self._on_worker_lost = on_worker_lost
        self._stopping = False
        self._negotiated_protocol: str | None = None

    @property
    def session_id(self) -> str | None:
        return self._session_id

    @property
    def worker_pid(self) -> int | None:
        return self._worker_pid

    @property
    def _stdin(self) -> BinaryIO:
        assert self._process is not None and self._process.stdin is not None
        return cast(BinaryIO, self._process.stdin)

    @property
    def _stdout(self) -> BinaryIO:
        assert self._process is not None and self._process.stdout is not None
        return cast(BinaryIO, self._process.stdout)

    def is_alive(self) -> bool:
        with self._lock:
            return self._process is not None and self._process.poll() is None

    def start(self, timeout: float = 10.0) -> None:
        """Spawn the child worker process and complete protocol handshake."""
        with self._lock:
            if self.is_alive():
                return
            self._stopping = False
            self._last_sequence.clear()
            self._session_id = None
            self._negotiated_protocol = None
            env = dict(os.environ)
            src_path = str(Path(__file__).resolve().parents[2] / "src")
            root_path = str(Path(__file__).resolve().parents[2])
            existing_pythonpath = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = f"{src_path}:{root_path}:{existing_pythonpath}".strip(":")
            self._process = subprocess.Popen(
                self._command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                bufsize=0,
            )
            handshake_queue: queue.Queue[Any] = queue.Queue(maxsize=1)
            self._pending_responses["__handshake__"] = handshake_queue
            self._reader_thread = threading.Thread(
                target=self._reader_loop,
                daemon=True,
                name="WorkerSupervisorReader",
            )
            self._reader_thread.start()
            self._stderr_thread = threading.Thread(
                target=self._stderr_drain_loop,
                daemon=True,
                name="WorkerSupervisorStderrDrain",
            )
            self._stderr_thread.start()

        try:
            hello = handshake_queue.get(timeout=timeout)
            if not isinstance(hello, c.WorkerHello):
                raise SupervisorError(f"Unexpected initial message: {type(hello).__name__}")
            if c.WORKER_PROTOCOL_VERSION not in hello.supported_protocols:
                with self._lock:
                    ready = c.WorkerReady(
                        selected_protocol="",
                        worker_session_id=hello.worker_session_id,
                        accepted=False,
                        message="Unsupported protocol",
                    )
                    with suppress(Exception):
                        write_frame(self._stdin, ready)
                self.stop()
                raise SupervisorError(
                    f"Worker does not support protocol {c.WORKER_PROTOCOL_VERSION}"
                )
            with self._lock:
                self._session_id = hello.worker_session_id
                self._worker_pid = hello.worker_pid
                self._negotiated_protocol = c.WORKER_PROTOCOL_VERSION
                ready = c.WorkerReady(
                    selected_protocol=c.WORKER_PROTOCOL_VERSION,
                    worker_session_id=hello.worker_session_id,
                    accepted=True,
                    message="Supervisor accepted",
                )
                write_frame(self._stdin, ready)
        except queue.Empty as error:
            self.stop()
            raise WorkerTimeoutError("Timeout waiting for WorkerHello handshake") from error
        finally:
            with self._lock:
                self._pending_responses.pop("__handshake__", None)

    def stop(self) -> None:
        """Gracefully shut down the worker process."""
        with self._lock:
            self._stopping = True
            for timer in self._cancel_timers.values():
                timer.cancel()
            self._cancel_timers.clear()
            if self._process is None:
                return
            try:
                if self._process.stdin and not self._process.stdin.closed:
                    write_frame(cast(BinaryIO, self._process.stdin), c.WorkerShutdownRequest())
                    self._process.stdin.close()
            except Exception:
                pass
            try:
                self._process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()
            self._process = None
            self._session_id = None
            self._worker_pid = None

    def validate(
        self,
        draft: c.DraftDto,
        expected_engineering_hash: str,
        expected_context_hash: str,
        timeout: float = 15.0,
    ) -> c.WorkerValidateResponse:
        """Dispatch validation request to the worker."""
        request_id = str(uuid.uuid4())
        resp_queue: queue.Queue[Any] = queue.Queue(maxsize=1)
        with self._lock:
            if not self.is_alive():
                raise WorkerLostError("Worker process is not running")
            self._pending_responses[request_id] = resp_queue
            request = c.WorkerValidateRequest(
                request_id=request_id,
                draft=draft,
                expected_engineering_hash=expected_engineering_hash,
                expected_context_hash=expected_context_hash,
            )
            write_frame(self._stdin, request)

        try:
            response = resp_queue.get(timeout=timeout)
            if not isinstance(response, c.WorkerValidateResponse):
                raise SupervisorError(f"Unexpected validation response: {type(response).__name__}")
            return response
        except queue.Empty as error:
            raise WorkerTimeoutError("Validation request timed out") from error
        finally:
            with self._lock:
                self._pending_responses.pop(request_id, None)

    def execute_job(
        self,
        job: c.RunJob,
        on_progress: Callable[[c.WorkerProgressEvent], None] | None = None,
        on_diagnostic: Callable[[c.WorkerDiagnosticEvent], None] | None = None,
        timeout: float | None = None,
        cancellation_requested: Callable[[], bool] | None = None,
    ) -> c.WorkerCompletedEvent | c.WorkerFailedEvent | c.WorkerCancelledEvent:
        """Admit and execute a preallocated run job on the worker."""
        job_timeout = timeout or job.timeout_seconds
        event_queue: queue.Queue[Any] = queue.Queue()

        with self._lock:
            if not self.is_alive():
                raise WorkerLostError("Worker process is not running")
            if cancellation_requested is not None and cancellation_requested():
                return c.WorkerCancelledEvent(
                    run_id=job.run_id,
                    worker_session_id=self._session_id or "",
                    sequence=0,
                    timestamp=datetime.now(UTC).isoformat(),
                    safe_boundary_reached=True,
                )
            self._active_jobs[job.run_id] = event_queue
            write_frame(self._stdin, job)

        try:
            # Wait for RunAccepted
            try:
                first = event_queue.get(timeout=5.0)
                if not isinstance(first, c.RunAccepted):
                    raise SupervisorError(f"Expected RunAccepted, got: {type(first).__name__}")
            except queue.Empty as error:
                raise WorkerTimeoutError("Job admission timed out") from error

            # Drain loop until terminal event
            deadline = time.monotonic() + job_timeout
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    with self._lock:
                        if self._process is not None:
                            self._process.kill()
                    raise WorkerTimeoutError(f"Run {job.run_id} timed out after {job_timeout}s")
                try:
                    event = event_queue.get(timeout=min(remaining, 1.0))
                except queue.Empty as err:
                    if not self.is_alive():
                        raise WorkerLostError(
                            f"Worker died during execution of run {job.run_id}"
                        ) from err
                    continue

                if isinstance(event, c.WorkerProgressEvent):
                    if on_progress:
                        on_progress(event)
                    elif self._on_progress:
                        self._on_progress(event)
                elif isinstance(event, c.WorkerDiagnosticEvent):
                    if on_diagnostic:
                        on_diagnostic(event)
                    elif self._on_diagnostic:
                        self._on_diagnostic(event)
                elif isinstance(
                    event, (c.WorkerCompletedEvent, c.WorkerFailedEvent, c.WorkerCancelledEvent)
                ):
                    with self._lock:
                        self._active_jobs.pop(job.run_id, None)
                    return event
                elif isinstance(event, c.WorkerFault):
                    with self._lock:
                        self._active_jobs.pop(job.run_id, None)
                    raise SupervisorError(
                        f"Worker fault: {event.fault_code}: {event.fault_message}"
                    )
                else:
                    sys.stderr.write(f"Unhandled worker event: {type(event).__name__}\n")

        finally:
            with self._lock:
                self._active_jobs.pop(job.run_id, None)
                timer = self._cancel_timers.pop(job.run_id, None)
                if timer is not None:
                    timer.cancel()

    def cancel(self, run_id: str, force: bool = False) -> None:
        """Request safe-boundary cancellation, then bound uncooperative execution.

        The deadline belongs to this job and process, so a completed job's timer
        cannot kill a later run or a replacement worker. The one-second default
        retains the earlier force-cancel grace and is configurable by composition.
        """
        with self._lock:
            if not self.is_alive() or run_id not in self._active_jobs:
                return
            with suppress(Exception):
                write_frame(self._stdin, c.CancelRunRequest(run_id=run_id, force_terminate=force))
            if run_id not in self._cancel_timers:
                process = self._process
                session_id = self._session_id
                timer = threading.Timer(
                    self.cancellation_grace_seconds,
                    self._force_kill_if_still_running,
                    args=(run_id, process, session_id),
                )
                timer.daemon = True
                self._cancel_timers[run_id] = timer
                timer.start()

    def _force_kill_if_still_running(
        self, run_id: str, process: subprocess.Popen[bytes] | None, session_id: str | None
    ) -> None:
        """Terminate only the still-active job on the captured worker generation."""
        with self._lock:
            if (
                process is not None
                and self._process is process
                and self._session_id == session_id
                and run_id in self._active_jobs
                and process.poll() is None
            ):
                process.kill()

    def _stderr_drain_loop(self) -> None:
        """Background thread continuously draining stderr to prevent pipe deadlocks."""
        if self._process is None or self._process.stderr is None:
            return
        stream = self._process.stderr
        while not self._stopping:
            try:
                line = stream.readline()
                if not line:
                    break
                sys.stderr.buffer.write(line)
                sys.stderr.buffer.flush()
            except Exception:
                break

    def _reader_loop(self, stream: BinaryIO | None = None) -> None:
        """Background thread continuously reading frames from worker stdout."""
        if stream is None:
            stream = self._stdout
        while not self._stopping:
            try:
                msg = read_frame(stream)
            except Exception as exc:
                if not self._stopping:
                    sys.stderr.write(f"Supervisor framing error: {exc}\n")
                break
            if msg is None:
                # EOF: worker closed output
                break

            worker_session_id = getattr(msg, "worker_session_id", None)
            if (
                worker_session_id is not None
                and self._session_id is not None
                and worker_session_id != self._session_id
            ):
                sys.stderr.write(
                    f"Supervisor quarantined frame from untrusted session: {worker_session_id}\n"
                )
                continue

            proto_version = getattr(msg, "protocol_version", None)
            expected_proto = self._negotiated_protocol or c.WORKER_PROTOCOL_VERSION
            if proto_version is not None and proto_version != expected_proto:
                sys.stderr.write(
                    f"Supervisor quarantined frame with unsupported protocol version: "
                    f"{proto_version} (expected {expected_proto})\n"
                )
                continue

            seq = getattr(msg, "sequence", None)
            msg_run_id = getattr(msg, "run_id", None)
            if seq is not None and msg_run_id is not None and isinstance(seq, int):
                run_id_str = str(msg_run_id)
                last_seq = self._last_sequence.get(run_id_str, -1)
                if seq <= last_seq:
                    sys.stderr.write(
                        f"Supervisor rejected non-monotonic sequence {seq} <= {last_seq} "
                        f"for run {run_id_str}\n"
                    )
                    continue
                self._last_sequence[run_id_str] = seq

            if isinstance(msg, c.WorkerHello):
                q = self._pending_responses.get("__handshake__")
                if q:
                    q.put(msg)
            elif isinstance(msg, c.WorkerValidateResponse):
                q = self._pending_responses.get(msg.request_id)
                if q:
                    q.put(msg)
            elif isinstance(
                msg,
                (
                    c.RunAccepted,
                    c.WorkerProgressEvent,
                    c.WorkerDiagnosticEvent,
                    c.WorkerCompletedEvent,
                    c.WorkerFailedEvent,
                    c.WorkerCancelledEvent,
                ),
            ):
                q = self._active_jobs.get(msg.run_id)
                if q:
                    q.put(msg)
            elif isinstance(msg, c.WorkerFault):
                if msg.run_id:
                    q = self._active_jobs.get(msg.run_id)
                    if q:
                        q.put(msg)
            else:
                sys.stderr.write(f"Supervisor received unexpected frame: {type(msg).__name__}\n")

        # Worker terminated or pipe closed
        exit_code = self._process.poll() if self._process else -1
        if not self._stopping and self._on_worker_lost:
            self._on_worker_lost(exit_code or -1)
