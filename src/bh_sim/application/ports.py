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
    PreparedRevisionDto,
    RunViewDto,
    ValidationDto,
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
        expected_context_hash: str | None = None,
    ) -> CalculatedRunDto: ...


class ArtifactRepositoryPort(Protocol):
    """Immutable canonical persistence and four-status last-valid lookup."""

    def save_inputs(self, prepared: PreparedRevisionDto) -> None: ...

    def save_run(self, result: CalculatedRunDto) -> None: ...

    def load_run(self, run_id: str) -> RunViewDto: ...

    def latest_valid_run(self, case_id: str) -> RunViewDto | None: ...


class DemonstrationPort(Protocol):
    """Retained prototype computations, never registered as production models."""

    def evaluate(self, name: str) -> DemonstrationReportDto: ...
