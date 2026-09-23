"""DW1 use-case policy over ports, including explicit legacy HTTP compatibility.

New Run requires a service-owned receipt for the exact engineering identity and
execution context. Receipts live only for this service session; reopening the app
requires validation. Configured workers never fall back to local execution.
Cancellation and publication share one terminal-disposition policy.
"""

from __future__ import annotations

from contextlib import suppress
from dataclasses import replace
from datetime import UTC, datetime
from threading import Event, RLock
from typing import Any
from uuid import uuid4

from bh_sim.boundary.contracts import (
    CalculatedRunDto,
    DemonstrationReportDto,
    DiagnosticDto,
    DraftDto,
    DraftListDto,
    MetricChangeDto,
    OverlaysDto,
    PlotDefinitionDto,
    PresentationDto,
    ResultSelectionDto,
    RunAttemptRecord,
    RunComparisonDto,
    RunExecutionDto,
    RunJob,
    RunViewDto,
    StatusChangeDto,
    ValidationDto,
    ValidationReceiptDto,
    WorkbookDto,
    WorkerCancelledEvent,
    WorkerCompletedEvent,
    WorkerFailedEvent,
)

from .ports import (
    ArtifactRepositoryPort,
    DemonstrationPort,
    DraftRepositoryPort,
    EngineeringPort,
)


class CommandRejected(ValueError):
    """Expected application rejection carrying a stable diagnostic code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class DemonstrationService:
    """Prototype-only CLI use case with no draft store or scientific promotion."""

    def __init__(self, demonstrations: DemonstrationPort) -> None:
        self.demonstrations = demonstrations

    def demonstrate(self, name: str) -> DemonstrationReportDto:
        """Request the selected prototype and return its immutable report."""
        return self.demonstrations.evaluate(name)


class ApplicationServices:
    """Case/revision, validation, run and result policy with injectable ports."""

    def __init__(
        self,
        drafts: DraftRepositoryPort,
        engineering: EngineeringPort,
        artifacts: ArtifactRepositoryPort,
        demonstrations: DemonstrationPort,
        supervisor: Any | None = None,
    ) -> None:
        self.drafts = drafts
        self.engineering = engineering
        self.artifacts = artifacts
        self.demonstrations = demonstrations
        self.supervisor = supervisor
        self._receipts: dict[str, ValidationReceiptDto] = {}
        self._active_run_id: str | None = None
        self._active_cancel_event: Event | None = None
        self._lock = RLock()
        # Retain computed identities when storage is unavailable; never rerun to save.
        self._unpersisted_runs: dict[str, CalculatedRunDto] = {}
        self._pending_attempts: dict[str, RunAttemptRecord] = {}
        if hasattr(self.artifacts, "reconcile_startup_attempts"):
            with suppress(Exception):
                self.artifacts.reconcile_startup_attempts()

    def save_draft(self, draft: DraftDto) -> DraftDto:
        """Save even incomplete drafts; repository decides immutable revision ID."""

        return self.drafts.save(draft)

    def create_draft(self, draft_id: str) -> DraftDto:
        """Create an unsaved empty revision; never overwrite an existing identity.

        Names retain the legacy PFD identity rules. Looking up the repository also
        catches names colliding with its existing filename normalization.
        """
        if not draft_id.strip() or draft_id != draft_id.strip() or len(draft_id) > 120:
            raise CommandRejected("INVALID_DRAFT_NAME", "Use 1–120 characters without outer spaces")
        try:
            self.drafts.latest(draft_id)
        except KeyError:
            pass
        else:
            raise CommandRejected("DRAFT_EXISTS", "A saved draft already uses this name")
        return DraftDto(
            draft_id, 1, None, datetime.now(UTC).isoformat(), (), (), PresentationDto(())
        )

    def list_drafts(self) -> DraftListDto:
        """Read saved draft identities without opening, validating or running one."""
        return DraftListDto(self.drafts.summaries())

    def open_draft(self, draft_id: str) -> DraftDto:
        """Read the selected latest draft without validation or execution."""

        return self.drafts.latest(draft_id)

    def validate_draft(self, draft: DraftDto) -> ValidationReceiptDto:
        """Compile current inputs without saving, and retain the issued receipt."""

        with self._lock:
            try:
                prepared = self.engineering.prepare(draft)
            except (KeyError, TypeError, ValueError) as error:
                raise CommandRejected("INVALID_DRAFT", str(error)) from error
            context = self.engineering.context_hash()
            worker_session_id = None
            if self._uses_worker():
                assert self.supervisor is not None
                resp = self.supervisor.validate(draft, prepared.engineering_hash, context)
                validation = ValidationDto(
                    valid=resp.valid,
                    degrees_of_freedom=resp.dof,
                    diagnostics=resp.diagnostics,
                )
                context = resp.context_hash
                worker_session_id = getattr(self.supervisor, "session_id", None)
            else:
                validation = self.engineering.validate(prepared)
                if context != self.engineering.context_hash():
                    raise CommandRejected(
                        "CONTEXT_CHANGED", "Execution context changed; validate again"
                    )
            receipt = ValidationReceiptDto(
                f"validation:{uuid4()}",
                draft.draft_id,
                prepared.revision_id,
                prepared.source_artifact_hash,
                prepared.engineering_hash,
                context,
                validation,
                worker_session_id=worker_session_id,
            )
            self._receipts[receipt.receipt_id] = receipt
            return receipt

    def start_run(self, draft: DraftDto, receipt_id: str) -> RunViewDto:
        """Run only matching validated content; reject before saving or evaluating."""

        with self._lock:
            receipt = self._receipts.get(receipt_id)
            if receipt is None:
                raise CommandRejected("VALIDATION_REQUIRED", "Validate this draft in this session")
            prepared = self.engineering.prepare(draft)
            is_supervised = self._uses_worker()
            if is_supervised:
                current_session_id = getattr(self.supervisor, "session_id", None)
                if receipt.worker_session_id != current_session_id:
                    raise CommandRejected(
                        "STALE_VALIDATION",
                        "Worker session expired; revalidation required",
                    )
            context = (
                receipt.execution_context_hash if is_supervised else self.engineering.context_hash()
            )
            if (
                receipt.draft_id != draft.draft_id
                or receipt.engineering_hash != prepared.engineering_hash
                or receipt.execution_context_hash != context
            ):
                raise CommandRejected("STALE_VALIDATION", "Engineering inputs or context changed")
            if not receipt.validation.valid:
                raise CommandRejected(
                    "VALIDATION_FAILED", "Resolve blocking validation diagnostics"
                )

        execution = self._execute(
            draft,
            expected_hash=prepared.engineering_hash,
            expected_context=context,
            expected_session=receipt.worker_session_id,
        )
        return execution.result

    def _uses_worker(self) -> bool:
        """Distinguish explicit local composition from a lost configured worker."""
        if self.supervisor is None:
            return False
        if not self.supervisor.is_alive() or self.supervisor.session_id is None:
            raise CommandRejected(
                "WORKER_UNAVAILABLE", "Worker unavailable; restart it and validate again"
            )
        return True

    def _record_attempt(self, attempt: RunAttemptRecord) -> RunAttemptRecord:
        """Retain a terminal audit record even if its durable write cannot complete."""
        self._pending_attempts[attempt.attempt_id] = attempt
        if hasattr(self.artifacts, "record_attempt"):
            winner = self.artifacts.record_attempt(attempt)
            self._pending_attempts.pop(attempt.attempt_id, None)
            return winner
        return attempt

    def _cancelled_attempt(self, attempt: RunAttemptRecord) -> bool:
        current = self._pending_attempts.get(attempt.attempt_id)
        if current is None and hasattr(self.artifacts, "load_attempt"):
            current = self.artifacts.load_attempt(attempt.attempt_id)
        return current is not None and current.state == "CANCELLED"

    def _execute(
        self,
        draft: DraftDto,
        *,
        expected_hash: str | None = None,
        expected_context: str | None = None,
        expected_session: str | None = None,
    ) -> RunExecutionDto:
        with self._lock:
            if self._active_run_id is not None:
                raise CommandRejected("RUN_BUSY", "Another run is still executing")
            is_supervised = self._uses_worker()
            if is_supervised and expected_session is not None:
                assert self.supervisor is not None
                if self.supervisor.session_id != expected_session:
                    raise CommandRejected("STALE_VALIDATION", "Worker changed; validate again")
            saved = self.drafts.save(draft)
            prepared = self.engineering.prepare(saved)
            if expected_hash is not None and prepared.engineering_hash != expected_hash:
                raise CommandRejected(
                    "STALE_VALIDATION", "Saved engineering content differs from input"
                )
            if (
                not is_supervised
                and expected_context is not None
                and self.engineering.context_hash() != expected_context
            ):
                raise CommandRejected("CONTEXT_CHANGED", "Execution context changed")
            self.artifacts.save_inputs(prepared)
            if (
                not is_supervised
                and expected_context is not None
                and self.engineering.context_hash() != expected_context
            ):
                raise CommandRejected("CONTEXT_CHANGED", "Context changed during persistence")
            attempt = RunAttemptRecord(
                attempt_id=f"att:{uuid4()}",
                run_id=f"run:{uuid4()}",
                case_id=prepared.case_id,
                engineering_hash=prepared.engineering_hash,
                context_hash=expected_context or self.engineering.context_hash(),
                state="ADMITTED",
                admitted_at=datetime.now(UTC).isoformat(),
            )
            try:
                self._record_attempt(attempt)
            except Exception as error:
                failed = replace(
                    attempt,
                    state="FAILED",
                    terminal_at=datetime.now(UTC).isoformat(),
                    failure_reason=f"Admission persistence failed: {type(error).__name__}",
                )
                # _record_attempt retains the failed record for inspection.
                with suppress(Exception):
                    self._record_attempt(failed)
                raise CommandRejected(
                    "PERSISTENCE_FAILED", f"Admission failed; no execution for {attempt.run_id}"
                ) from error
            self._active_run_id = attempt.run_id
            cancellation = Event()
            self._active_cancel_event = cancellation

        artifact_hash: str | None = None
        publishing = False
        try:
            with self._lock:
                if self._cancelled_attempt(attempt):
                    raise CommandRejected("RUN_CANCELLED", "Run was cancelled")
                attempt = self._record_attempt(replace(attempt, state="RUNNING"))
            # Evaluation must release the application lock so Cancel can win.
            if is_supervised:
                assert self.supervisor is not None
                job = RunJob(
                    job_id=f"job:{uuid4()}",
                    run_id=attempt.run_id,
                    case_id=prepared.case_id,
                    revision_id=saved.revision,
                    engineering_hash=prepared.engineering_hash,
                    context_hash=attempt.context_hash,
                    draft=saved,
                )
                terminal = self.supervisor.execute_job(
                    job,
                    cancellation_requested=cancellation.is_set,
                )
            else:
                terminal = self.engineering.run(
                    prepared,
                    run_id=attempt.run_id,
                    expected_context_hash=expected_context,
                )

            with self._lock:
                # Publication and cancellation are serialized on both execution paths.
                if self._cancelled_attempt(attempt):
                    raise CommandRejected("RUN_CANCELLED", "Run was cancelled")
                if isinstance(terminal, WorkerCancelledEvent):
                    attempt = self._record_attempt(
                        replace(
                            attempt,
                            state="CANCELLED",
                            terminal_at=datetime.now(UTC).isoformat(),
                            failure_reason="Run cancelled",
                        )
                    )
                    raise CommandRejected("RUN_CANCELLED", "Run was cancelled")
                if isinstance(terminal, WorkerFailedEvent):
                    raise CommandRejected("RUN_FAILED", f"Run failed: {terminal.reason}")
                publishing = True
                if isinstance(terminal, WorkerCompletedEvent):
                    artifact_hash = terminal.artifact_hash
                    if not terminal.staged_path:
                        raise ValueError("Worker completed without staged artifact path")
                    view = self.artifacts.promote_staged_run(
                        terminal.staged_path,
                        expected_run_id=attempt.run_id,
                        expected_case_id=attempt.case_id,
                        expected_revision_id=prepared.revision_id,
                        expected_hash=artifact_hash,
                    )
                elif isinstance(terminal, CalculatedRunDto):
                    artifact_hash = terminal.view.artifact.content_hash
                    self._unpersisted_runs[attempt.run_id] = terminal
                    if (
                        terminal.view.run_id != attempt.run_id
                        or terminal.view.case_id != attempt.case_id
                        or terminal.view.revision_id != prepared.revision_id
                    ):
                        raise ValueError("Calculated result does not match admitted identity")
                    self.artifacts.save_run(terminal)
                    view = terminal.view
                else:
                    raise ValueError("Unexpected execution disposition")
                self._record_attempt(
                    replace(
                        attempt,
                        state="COMPLETED",
                        terminal_at=datetime.now(UTC).isoformat(),
                        artifact_hash=artifact_hash,
                        persisted=True,
                    )
                )
                self._unpersisted_runs.pop(attempt.run_id, None)
                return RunExecutionDto(saved, prepared, view)
        except Exception as error:
            with self._lock:
                if self._cancelled_attempt(attempt):
                    raise CommandRejected("RUN_CANCELLED", "Run was cancelled") from error
                reason = "Result persistence failed" if publishing else "Run execution failed"
                failed = replace(
                    attempt,
                    state="FAILED",
                    terminal_at=datetime.now(UTC).isoformat(),
                    failure_reason=f"{reason}: {type(error).__name__}",
                    artifact_hash=artifact_hash,
                    persisted=False,
                )
                try:
                    self._record_attempt(failed)
                except Exception as audit_error:
                    raise CommandRejected(
                        "PERSISTENCE_FAILED",
                        f"{reason}; terminal audit retained in memory for {attempt.run_id}",
                    ) from audit_error
                if publishing:
                    raise CommandRejected(
                        "PERSISTENCE_FAILED", f"{reason}; reconcile {attempt.run_id} without rerun"
                    ) from error
                raise
        finally:
            with self._lock:
                self._active_run_id = None
                self._active_cancel_event = None

    def cancel_run(self, run_id: str, reason: str = "User cancelled") -> RunAttemptRecord | None:
        """Cancel an in-flight run."""
        with self._lock:
            target_run_id = run_id
            if not target_run_id or target_run_id == "run:in-flight":
                target_run_id = self._active_run_id or target_run_id
            if hasattr(self.artifacts, "list_attempts"):
                attempts = self.artifacts.list_attempts()
                if not target_run_id or target_run_id == "run:in-flight":
                    for att in reversed(attempts):
                        if att.state in ("ADMITTED", "RUNNING"):
                            target_run_id = att.run_id
                            break
                if target_run_id == self._active_run_id and self._active_cancel_event:
                    self._active_cancel_event.set()
                if (
                    self.supervisor is not None
                    and getattr(self.supervisor, "is_alive", lambda: False)()
                    and target_run_id
                    and target_run_id != "run:in-flight"
                ):
                    self.supervisor.cancel(target_run_id)
                for att in attempts:
                    if att.run_id == target_run_id and att.state in ("ADMITTED", "RUNNING"):
                        updated = replace(
                            att,
                            state="CANCELLED",
                            terminal_at=datetime.now(UTC).isoformat(),
                            failure_reason=reason,
                        )
                        return self._record_attempt(updated)
            elif (
                self.supervisor is not None
                and getattr(self.supervisor, "is_alive", lambda: False)()
            ):
                if target_run_id and target_run_id != "run:in-flight":
                    self.supervisor.cancel(target_run_id)
            return None

    def inspect_attempt(self, attempt_id: str) -> RunAttemptRecord:
        """Retrieve an operational attempt record by its ID."""
        if not hasattr(self.artifacts, "load_attempt"):
            raise CommandRejected("CAPABILITY_UNAVAILABLE", "Attempt persistence is unavailable")
        record = self._pending_attempts.get(attempt_id) or self.artifacts.load_attempt(attempt_id)
        if record is None:
            raise KeyError(f"unknown attempt ID: {attempt_id}")
        return record

    def list_attempts(self, case_id: str | None = None) -> tuple[RunAttemptRecord, ...]:
        """List operational attempt records for a case or all cases."""
        if not hasattr(self.artifacts, "list_attempts"):
            return ()
        records = {item.attempt_id: item for item in self.artifacts.list_attempts(case_id)}
        records.update(
            {
                key: item
                for key, item in self._pending_attempts.items()
                if case_id is None or item.case_id == case_id
            }
        )
        return tuple(sorted(records.values(), key=lambda item: (item.admitted_at, item.attempt_id)))

    def _legacy_validate(self, draft: DraftDto) -> ValidationDto:
        """Retain HTTP v1alpha diagnostics/DOF behavior without issuing a receipt."""

        try:
            return self.engineering.validate(self.engineering.prepare(draft))
        except (KeyError, TypeError, ValueError) as error:
            return ValidationDto(False, 0, (DiagnosticDto("INVALID_DRAFT", str(error)),))

    def _legacy_run(self, draft: DraftDto) -> RunExecutionDto:
        """Compatibility-only save/run behavior; never exposed as a registry flag.

        Old HTTP had no prior-Validate receipt. Keep that contract until a separately
        versioned HTTP migration; each explicit legacy POST is still a new attempt.
        """

        return self._execute(draft)

    def inspect_run(self, run_id: str) -> RunViewDto:
        """Load an immutable result, including failed attempts, without rerunning."""

        return self.artifacts.load_run(run_id)

    def last_valid_run(self, case_id: str) -> RunViewDto | None:
        """Use repository four-status acceptance, never a UI combined success flag."""

        return self.artifacts.latest_valid_run(case_id)

    def compare_runs(self, before_id: str, after_id: str) -> RunComparisonDto:
        """Compare stored quantities/statuses; retain units and absent metrics.

        No numerical deltas or unit conversions are invented here. Cross-case comparison
        requires a future explicit object correspondence contract and is rejected in DW1.
        """

        before = self.inspect_run(before_id)
        after = self.inspect_run(after_id)
        if before.case_id != after.case_id:
            raise CommandRejected("CASE_MISMATCH", "Select two runs from the same case")
        old = {
            (unit.unit_id, metric.name): metric.quantity
            for unit in before.unit_results
            for metric in unit.metrics
        }
        new = {
            (unit.unit_id, metric.name): metric.quantity
            for unit in after.unit_results
            for metric in unit.metrics
        }
        metrics = tuple(
            MetricChangeDto(unit, name, old.get((unit, name)), new.get((unit, name)))
            for unit, name in sorted(old.keys() | new.keys())
            if old.get((unit, name)) != new.get((unit, name))
        )
        statuses = [
            StatusChangeDto(dimension, getattr(before, dimension), getattr(after, dimension))
            for dimension in ("convergence", "closure", "physical_validity", "correlation_validity")
            if getattr(before, dimension) != getattr(after, dimension)
        ]
        old_units = {unit.unit_id: unit.validity for unit in before.unit_results}
        new_units = {unit.unit_id: unit.validity for unit in after.unit_results}
        statuses.extend(
            StatusChangeDto("unit_validity", old_units.get(unit), new_units.get(unit), unit)
            for unit in sorted(old_units.keys() | new_units.keys())
            if old_units.get(unit) != new_units.get(unit)
        )
        return RunComparisonDto(before.artifact, after.artifact, metrics, tuple(statuses))

    def inspect_workbook(self, case_id: str, run_id: str | None = None) -> WorkbookDto:
        """Expose authoritative flowsheet stream, unit and balance workbooks."""
        return self.artifacts.get_workbook(case_id, run_id)

    def select_display_run(self, case_id: str, run_id: str | None = None) -> ResultSelectionDto:
        """Select active display run and return selection and staleness status."""
        return self.artifacts.get_overlays(case_id, run_id).selection

    def get_overlays(self, case_id: str, run_id: str | None = None) -> OverlaysDto:
        """Expose canvas result overlays for streams and equipment."""
        return self.artifacts.get_overlays(case_id, run_id)

    def get_plot_data(
        self,
        case_id: str,
        run_id: str | None = None,
        plot_kind: str = "T_Q",
        unit_id: str | None = None,
    ) -> PlotDefinitionDto:
        """Extract plottable 2D series for process-wide or single-unit curves."""
        return self.artifacts.get_plot_data(case_id, run_id, plot_kind, unit_id)

    def demonstrate(self, name: str) -> DemonstrationReportDto:
        """Execute only the retained explicit prototype demonstration use case."""

        return self.demonstrations.evaluate(name)
