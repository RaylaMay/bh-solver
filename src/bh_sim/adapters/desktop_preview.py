"""DW2 mock service composition with no scientific implementation imports.

Drafts use the retained v1alpha repository. Engineering and result commands are
unavailable, not fabricated. Replacing these ports with the supervised worker is
DW4 work; the UI accepts only the neutral CommandGateway.
"""

from pathlib import Path

from bh_sim.application.commands import CommandRegistry
from bh_sim.application.history import HistoryService
from bh_sim.application.pfd import PfdService
from bh_sim.application.services import ApplicationServices, CommandRejected
from bh_sim.boundary.contracts import (
    CalculatedRunDto,
    DemonstrationReportDto,
    DraftDto,
    OverlaysDto,
    PlotDefinitionDto,
    PreparedRevisionDto,
    RunAttemptRecord,
    RunViewDto,
    ValidationDto,
    WorkbookDto,
)

from .drafts import DraftRepository, DraftRepositoryAdapter
from .history import JsonHistoryRepository
from .pfd import ExistingQuantityAdapter, NativePfdRepository, reference_catalogue


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
        self,
        prepared: PreparedRevisionDto,
        *,
        run_id: str | None = None,
        expected_context_hash: str | None = None,
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

    def record_attempt(self, attempt: RunAttemptRecord) -> RunAttemptRecord:
        raise self._unavailable()

    def load_attempt(self, attempt_id: str) -> RunAttemptRecord | None:
        raise self._unavailable()

    def list_attempts(self, case_id: str | None = None) -> tuple[RunAttemptRecord, ...]:
        raise self._unavailable()

    def reconcile_startup_attempts(self) -> tuple[RunAttemptRecord, ...]:
        raise self._unavailable()

    def promote_staged_run(
        self,
        staged_path: str,
        *,
        expected_run_id: str | None = None,
        expected_case_id: str | None = None,
        expected_revision_id: str | None = None,
        expected_hash: str | None = None,
    ) -> RunViewDto:
        raise self._unavailable()

    def get_workbook(self, case_id: str, run_id: str | None = None) -> WorkbookDto:
        raise self._unavailable()

    def get_overlays(self, case_id: str, run_id: str | None = None) -> OverlaysDto:
        raise self._unavailable()

    def get_plot_data(
        self,
        case_id: str,
        run_id: str | None = None,
        plot_kind: str = "T_Q",
        unit_id: str | None = None,
    ) -> PlotDefinitionDto:
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
    pfd = PfdService(
        reference_catalogue(),
        NativePfdRepository(data_root / "native-drafts"),
        services.drafts,
        ExistingQuantityAdapter(),
    )
    return CommandRegistry(
        services,
        pfd=pfd,
        history=HistoryService(pfd, JsonHistoryRepository(data_root / "history")),
        unavailable_commands=frozenset(
            {
                "draft.validate",
                "run.start",
                "run.cancel",
                "run.inspect",
                "run.inspect_attempt",
                "run.list_attempts",
                "run.select_last_valid",
                "run.compare",
                "demo.evaluate",
            }
        ),
    )


def create_supervised_gateway(
    data_root: Path,
    supervisor: object | None = None,
) -> CommandRegistry:
    """Bind real draft, persistence, and supervised solver commands for DW4."""
    from bh_sim.composition import create_services

    services = create_services(data_root=data_root, supervisor=supervisor)
    pfd = PfdService(
        reference_catalogue(),
        NativePfdRepository(data_root / "native-drafts"),
        services.drafts,
        ExistingQuantityAdapter(),
    )
    return CommandRegistry(
        services,
        pfd=pfd,
        history=HistoryService(pfd, JsonHistoryRepository(data_root / "history")),
        unavailable_commands=frozenset({"demo.evaluate"}),
    )
