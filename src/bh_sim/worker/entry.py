"""Out-of-process thermofluid solver worker entry point.

Communicates over standard I/O pipes using length-prefixed boundary JSON frames.
Standard output is reserved exclusively for framed protocol messages; diagnostics
and logs are emitted to stderr.
"""

from __future__ import annotations

import os
import platform
import sys
import threading
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, BinaryIO, Literal, cast

from bh_sim.boundary import contracts as c
from bh_sim.boundary.worker_framing import read_frame, write_frame


def create_default_adapter() -> Any:
    """Instantiate the concrete calculation engine adapter inside the worker process."""
    import json
    from dataclasses import asdict
    from importlib.metadata import version

    from bh_sim.adapters.engineering import InProcessEngineeringAdapter
    from bh_sim.adapters.reference import reference_property_package
    from bh_sim.core.json_codec import canonical_json
    from bh_sim.engine import AcyclicRunEngine, PropertyRegistry, reference_model_catalog
    from bh_sim.engine.properties import PolynomialLiquidPackage

    catalog = reference_model_catalog()
    properties = PropertyRegistry((reference_property_package(),))
    engine = AcyclicRunEngine(catalog, properties)

    def context_metadata(selected_engine: AcyclicRunEngine) -> str:
        packages = []
        for identifier, package in sorted(selected_engine.properties._packages.items()):
            if not isinstance(package, PolynomialLiquidPackage):
                raise RuntimeError("execution-context inventory unavailable for this backend")
            packages.append(
                {
                    "package_id": str(identifier),
                    "implementation": type(package).__qualname__,
                    "version": package.version,
                    "liquids": [asdict(liquid) for _, liquid in sorted(package._liquids.items())],
                }
            )
        return json.dumps(
            {
                "catalogue": [
                    json.loads(canonical_json(selected_engine.catalog.descriptor(model)))
                    for model in selected_engine.catalog.model_ids
                ],
                "factories": [
                    (name, factory.__module__, factory.__qualname__)
                    for name, factory in sorted(selected_engine.catalog._factories.items())
                ],
                "properties": packages,
                "execution": "AcyclicRunEngine/v1alpha; no configured residual solver",
                "runtime": {
                    "implementation": platform.python_implementation(),
                    "version": platform.python_version(),
                },
                "packages": {
                    name: version(name) for name in ("numpy", "scipy", "pint", "networkx")
                },
            },
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )

    return InProcessEngineeringAdapter(engine, context_metadata)


def run_worker_loop(
    input_stream: BinaryIO,
    output_stream: BinaryIO,
    adapter_factory: Callable[[], Any] | None = None,
) -> None:
    """Execute the solver worker request/event loop."""
    factory = adapter_factory or create_default_adapter
    adapter: Any = None

    session_id = f"worker-session-{uuid.uuid4()}"
    pid = os.getpid()

    # 1. Send WorkerHello greeting
    hello = c.WorkerHello(
        supported_protocols=(c.WORKER_PROTOCOL_VERSION,),
        worker_session_id=session_id,
        worker_pid=pid,
        capabilities=("acyclic_flowsheet", "steady_state", "polynomial_liquid"),
        solver_version="0.1.0",
        protocol_version=c.WORKER_PROTOCOL_VERSION,
    )
    write_frame(output_stream, hello)

    # 2. Wait for WorkerReady confirmation
    first_msg = read_frame(input_stream)
    if not isinstance(first_msg, c.WorkerReady):
        sys.stderr.write(f"Worker expected WorkerReady, received: {type(first_msg).__name__}\n")
        sys.stderr.flush()
        return

    if not first_msg.accepted:
        sys.stderr.write(f"Supervisor rejected handshake: {first_msg.message}\n")
        sys.stderr.flush()
        return

    # Lazily initialize calculation adapter
    try:
        adapter = factory()
    except Exception as exc:
        sys.stderr.write(f"Failed to initialize engine adapter: {exc}\n")
        sys.stderr.flush()
        write_frame(
            output_stream,
            c.WorkerFault(
                worker_session_id=session_id,
                run_id=None,
                fault_code="ENGINE_INIT_FAILED",
                fault_message=str(exc),
                timestamp=datetime.now(UTC).isoformat(),
            ),
        )
        return

    # One execution thread keeps control reads responsive without queuing work.
    # Reject concurrent requests; retain only this job's cancellation event.
    output_lock = threading.Lock()
    active_thread: threading.Thread | None = None
    active_run_id: str | None = None
    cancellation = threading.Event()
    finished = threading.Event()
    finished.set()

    def send(message: object) -> None:
        with output_lock:
            write_frame(output_stream, message)

    def emit_cancelled(run_id: str, sequence: int) -> None:
        send(
            c.WorkerCancelledEvent(
                run_id=run_id,
                worker_session_id=session_id,
                sequence=sequence,
                timestamp=datetime.now(UTC).isoformat(),
                safe_boundary_reached=True,
            )
        )

    def execute(msg: c.RunJob, cancellation: threading.Event, finished: threading.Event) -> None:
        """Evaluate one job; only this thread publishes its terminal event."""
        sequence = 1
        # Acknowledge admission immediately
        admitted_at = datetime.now(UTC).isoformat()
        send(
            c.RunAccepted(
                job_id=msg.job_id,
                run_id=msg.run_id,
                worker_session_id=session_id,
                admitted_at=admitted_at,
            ),
        )

        if cancellation.is_set():
            finished.set()
            emit_cancelled(msg.run_id, sequence)
            return

        # Emit initial progress
        send(
            c.WorkerProgressEvent(
                run_id=msg.run_id,
                worker_session_id=session_id,
                sequence=sequence,
                timestamp=datetime.now(UTC).isoformat(),
                iteration=0,
                message="Compiling flowsheet input",
            ),
        )
        sequence += 1

        start_time = time.perf_counter()
        try:
            prepared = adapter.prepare(msg.draft)
            if prepared.engineering_hash != msg.engineering_hash:
                raise ValueError("Engineering input hash mismatch during worker execution")

            calculated = adapter.run(
                prepared,
                run_id=msg.run_id,
                expected_context_hash=msg.context_hash,
            )
            if cancellation.is_set():
                finished.set()
                emit_cancelled(msg.run_id, sequence)
                return
            duration_ms = (time.perf_counter() - start_time) * 1000.0

            from bh_sim.core.json_codec import canonical_json, contract_digest

            if hasattr(calculated, "view"):
                raw_json = calculated.canonical_json
                artifact_hash = calculated.view.artifact.content_hash
                conv = calculated.view.convergence.lower()
                clos = calculated.view.closure.lower()
                phys = calculated.view.physical_validity.lower()
                corr = calculated.view.correlation_validity.lower()
                staged_dir = Path(".bh/runtime/staged")
                staged_dir.mkdir(parents=True, exist_ok=True)
                staged_file = staged_dir / f"{msg.run_id}.json"
                staged_file.write_text(raw_json, encoding="utf-8")
                staged_path: str | None = str(staged_file.resolve())
            else:
                raw_json = canonical_json(calculated.result)
                artifact_hash = contract_digest(calculated.result)
                conv = getattr(
                    calculated.result.convergence,
                    "value",
                    str(calculated.result.convergence),
                ).lower()
                clos = getattr(
                    calculated.result.closure,
                    "value",
                    str(calculated.result.closure),
                ).lower()
                phys = getattr(
                    calculated.result.physical_validity,
                    "value",
                    str(calculated.result.physical_validity),
                ).lower()
                corr = getattr(
                    calculated.result.correlation_validity,
                    "value",
                    str(calculated.result.correlation_validity),
                ).lower()
                staged_dir = Path(".bh/runtime/staged")
                staged_dir.mkdir(parents=True, exist_ok=True)
                staged_file = staged_dir / f"{msg.run_id}.json"
                staged_file.write_text(raw_json, encoding="utf-8")
                staged_path = str(staged_file.resolve())

            finished.set()
            send(
                c.WorkerCompletedEvent(
                    run_id=msg.run_id,
                    worker_session_id=session_id,
                    sequence=sequence,
                    timestamp=datetime.now(UTC).isoformat(),
                    artifact_hash=artifact_hash,
                    staged_path=staged_path,
                    convergence=cast(
                        Literal["converged", "unconverged", "failed", "unknown"], conv
                    ),
                    closure=cast(Literal["passed", "failed", "unknown"], clos),
                    physical_validity=cast(Literal["valid", "invalid", "unknown"], phys),
                    correlation_validity=cast(
                        Literal["valid", "extrapolated", "invalid", "unknown"], corr
                    ),
                    execution_duration_ms=duration_ms,
                    manifest=(
                        ("solver", "scipy"),
                        ("python", platform.python_version()),
                        ("platform", platform.system()),
                    ),
                ),
            )
            sequence += 1
        except Exception as exc:
            import traceback

            traceback.print_exc(file=sys.stderr)
            finished.set()
            send(
                c.WorkerFailedEvent(
                    run_id=msg.run_id,
                    worker_session_id=session_id,
                    sequence=sequence,
                    timestamp=datetime.now(UTC).isoformat(),
                    reason=f"{type(exc).__name__}: {exc}",
                ),
            )
            sequence += 1

    while True:
        try:
            msg = read_frame(input_stream)
        except Exception:
            break
        if msg is None:
            break
        busy = not finished.is_set()
        if isinstance(msg, c.CancelRunRequest):
            if busy and msg.run_id == active_run_id:
                cancellation.set()
            continue
        if isinstance(msg, c.WorkerShutdownRequest):
            break
        if busy:
            if isinstance(msg, c.WorkerValidateRequest):
                send(
                    c.WorkerValidateResponse(
                        request_id=msg.request_id,
                        valid=False,
                        dof=0,
                        engineering_hash="",
                        context_hash="",
                        diagnostics=(c.DiagnosticDto("WORKER_BUSY", "A run is still executing"),),
                    )
                )
            elif isinstance(msg, c.RunJob):
                send(
                    c.WorkerFault(
                        worker_session_id=session_id,
                        run_id=msg.run_id,
                        fault_code="WORKER_BUSY",
                        fault_message="A run is still executing",
                        timestamp=datetime.now(UTC).isoformat(),
                    )
                )
            continue
        if isinstance(msg, c.WorkerValidateRequest):
            try:
                prepared = adapter.prepare(msg.draft)
                validation = adapter.validate(prepared)
                ctx_hash = adapter.context_hash()
                response = c.WorkerValidateResponse(
                    request_id=msg.request_id,
                    valid=validation.valid,
                    dof=validation.degrees_of_freedom,
                    engineering_hash=prepared.engineering_hash,
                    context_hash=ctx_hash,
                    diagnostics=validation.diagnostics,
                )
                send(response)
            except Exception as exc:
                sys.stderr.write(f"Validation error: {exc}\n")
                sys.stderr.flush()
                send(
                    c.WorkerValidateResponse(
                        request_id=msg.request_id,
                        valid=False,
                        dof=0,
                        engineering_hash="",
                        context_hash="",
                        diagnostics=(c.DiagnosticDto("VALIDATION_EXCEPTION", str(exc)),),
                    ),
                )

        elif isinstance(msg, c.RunJob):
            active_run_id = msg.run_id
            cancellation = threading.Event()
            finished = threading.Event()
            active_thread = threading.Thread(
                target=execute,
                args=(msg, cancellation, finished),
                name="WorkerExecution",
            )
            active_thread.start()
        else:
            sys.stderr.write(f"Unknown message type received: {type(msg).__name__}\n")
    # Intentional Quit is bounded by the supervisor; EOF alone never starts work.
    if active_thread is not None:
        active_thread.join()


def main() -> None:
    """Worker binary entry point."""
    run_worker_loop(sys.stdin.buffer, sys.stdout.buffer)


if __name__ == "__main__":
    main()
