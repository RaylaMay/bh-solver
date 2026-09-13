"""DW1 use-case policy over ports, including explicit legacy HTTP compatibility.

New Run requires a service-owned receipt for the exact engineering identity and
execution context. Receipts live only for this service session; reopening the app
requires validation. No worker admission, durable retry or cancellation is claimed.
"""

from __future__ import annotations

from datetime import UTC, datetime
from threading import RLock
from uuid import uuid4

from bh_sim.boundary.contracts import (
    DemonstrationReportDto,
    DiagnosticDto,
    DraftDto,
    DraftListDto,
    MetricChangeDto,
    PresentationDto,
    RunComparisonDto,
    RunExecutionDto,
    RunViewDto,
    StatusChangeDto,
    ValidationDto,
    ValidationReceiptDto,
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
    ) -> None:
        self.drafts = drafts
        self.engineering = engineering
        self.artifacts = artifacts
        self.demonstrations = demonstrations
        self._receipts: dict[str, ValidationReceiptDto] = {}
        self._lock = RLock()

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
            context = self.engineering.context_hash()
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
                draft, expected_hash=prepared.engineering_hash, expected_context=context
            )
            return execution.result

    def _execute(
        self,
        draft: DraftDto,
        *,
        expected_hash: str | None = None,
        expected_context: str | None = None,
    ) -> RunExecutionDto:
        saved = self.drafts.save(draft)
        prepared = self.engineering.prepare(saved)
        if expected_hash is not None and prepared.engineering_hash != expected_hash:
            raise CommandRejected(
                "STALE_VALIDATION", "Saved engineering content differs from input"
            )
        if expected_context is not None and self.engineering.context_hash() != expected_context:
            raise CommandRejected("CONTEXT_CHANGED", "Execution context changed before evaluation")
        self.artifacts.save_inputs(prepared)
        if expected_context is not None and self.engineering.context_hash() != expected_context:
            raise CommandRejected("CONTEXT_CHANGED", "Execution context changed during persistence")
        calculated = self.engineering.run(prepared, expected_context_hash=expected_context)
        self.artifacts.save_run(calculated)
        return RunExecutionDto(saved, prepared, calculated.view)

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

        with self._lock:
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

    def demonstrate(self, name: str) -> DemonstrationReportDto:
        """Execute only the retained explicit prototype demonstration use case."""

        return self.demonstrations.evaluate(name)
