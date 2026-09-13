"""DW2 mock service composition with no scientific implementation imports.

Drafts use the retained v1alpha repository. Engineering and result commands are
unavailable, not fabricated. Replacing these ports with the supervised worker is
DW4 work; the UI accepts only the neutral CommandGateway.
"""

from pathlib import Path

from bh_sim.application.commands import CommandRegistry
from bh_sim.application.services import ApplicationServices, CommandRejected
from bh_sim.boundary.contracts import (
    CalculatedRunDto,
    DemonstrationReportDto,
    DraftDto,
    PreparedRevisionDto,
    RunViewDto,
    ValidationDto,
)

from .drafts import DraftRepository, DraftRepositoryAdapter


class UnavailablePreviewPorts:
    """Mock run/result ports with explicit absence; never return engineering values."""

    @staticmethod
    def _unavailable() -> CommandRejected:
        return CommandRejected(
            "CAPABILITY_UNAVAILABLE", "Solver connection is unavailable in this preview"
        )

    def prepare(self, draft: DraftDto) -> PreparedRevisionDto:
        raise self._unavailable()

    def context_hash(self) -> str:
        raise self._unavailable()

    def validate(self, prepared: PreparedRevisionDto) -> ValidationDto:
        raise self._unavailable()

    def run(
        self, prepared: PreparedRevisionDto, *, expected_context_hash: str | None = None
    ) -> CalculatedRunDto:
        raise self._unavailable()

    def save_inputs(self, prepared: PreparedRevisionDto) -> None:
        raise self._unavailable()

    def save_run(self, result: CalculatedRunDto) -> None:
        raise self._unavailable()

    def load_run(self, run_id: str) -> RunViewDto:
        raise self._unavailable()

    def latest_valid_run(self, case_id: str) -> RunViewDto | None:
        raise self._unavailable()

    def evaluate(self, name: str) -> DemonstrationReportDto:
        raise self._unavailable()


def create_preview_gateway(data_root: Path) -> CommandRegistry:
    """Bind draft commands only; unavailable commands reject before any mock call."""
    mock = UnavailablePreviewPorts()
    services = ApplicationServices(
        DraftRepositoryAdapter(DraftRepository(data_root / "drafts")),
        mock,
        mock,
        mock,
    )
    return CommandRegistry(
        services,
        unavailable_commands=frozenset(
            {
                "draft.validate",
                "run.start",
                "run.inspect",
                "run.select_last_valid",
                "run.compare",
                "demo.evaluate",
            }
        ),
    )
