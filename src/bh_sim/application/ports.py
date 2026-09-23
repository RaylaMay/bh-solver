"""Replaceable DW1 repository, engineering and legacy demonstration ports.

Implementations translate canonical JSON at their own boundary. Policy and mocks
need no scientific library, HTTP framework, database implementation or UI toolkit.
"""

from typing import Protocol

from bh_sim.boundary.contracts import (
    CalculatedRunDto,
    DemonstrationReportDto,
    DraftDto,
    DraftSummaryDto,
    OverlaysDto,
    PlotDefinitionDto,
    PreparedRevisionDto,
    RunAttemptRecord,
    RunViewDto,
    ValidationDto,
    WorkbookDto,
)


class DraftRepositoryPort(Protocol):
    """Immutable draft snapshots; save returns actual idempotent revision identity."""

    def save(self, draft: DraftDto) -> DraftDto: ...

    def latest(self, draft_id: str) -> DraftDto: ...

    def summaries(self) -> tuple[DraftSummaryDto, ...]: ...


class EngineeringPort(Protocol):
    """Authoritative conversion, identity, compile and synchronous evaluation."""

    def prepare(self, draft: DraftDto) -> PreparedRevisionDto: ...

    def context_hash(self) -> str: ...

    def validate(self, prepared: PreparedRevisionDto) -> ValidationDto: ...

    def run(
        self,
        prepared: PreparedRevisionDto,
        *,
        run_id: str | None = None,
        expected_context_hash: str | None = None,
    ) -> CalculatedRunDto: ...


class ArtifactRepositoryPort(Protocol):
    """Immutable canonical persistence and four-status last-valid lookup."""

    def save_inputs(self, prepared: PreparedRevisionDto) -> None: ...

    def save_run(self, result: CalculatedRunDto) -> None: ...

    def load_run(self, run_id: str) -> RunViewDto: ...

    def latest_valid_run(self, case_id: str) -> RunViewDto | None: ...

    def record_attempt(self, attempt: RunAttemptRecord) -> RunAttemptRecord: ...

    def load_attempt(self, attempt_id: str) -> RunAttemptRecord | None: ...
    def list_attempts(self, case_id: str | None = None) -> tuple[RunAttemptRecord, ...]: ...
    def reconcile_startup_attempts(self) -> tuple[RunAttemptRecord, ...]: ...

    def promote_staged_run(
        self,
        staged_path: str,
        *,
        expected_run_id: str | None = None,
        expected_case_id: str | None = None,
        expected_revision_id: str | None = None,
        expected_hash: str | None = None,
    ) -> RunViewDto: ...

    def get_workbook(self, case_id: str, run_id: str | None = None) -> WorkbookDto: ...

    def get_overlays(self, case_id: str, run_id: str | None = None) -> OverlaysDto: ...

    def get_plot_data(
        self,
        case_id: str,
        run_id: str | None = None,
        plot_kind: str = "T_Q",
        unit_id: str | None = None,
    ) -> PlotDefinitionDto: ...


class DemonstrationPort(Protocol):
    """Retained prototype computations, never registered as production models."""

    def evaluate(self, name: str) -> DemonstrationReportDto: ...
