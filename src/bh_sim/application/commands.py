"""Shared command registry and synchronous, session-local duplicate protection."""

from __future__ import annotations

from threading import RLock

from bh_sim.boundary import contracts as c
from bh_sim.boundary.contracts import (
    COMMAND_VERSION,
    CancelRunParameters,
    CommandData,
    CommandEvent,
    CommandOutcome,
    CommandRequest,
    CompareRunsParameters,
    CreateDraftParameters,
    DemonstrationParameters,
    DiagnosticDto,
    DraftParameters,
    InspectAttemptParameters,
    InspectRunParameters,
    LastValidParameters,
    ListAttemptsParameters,
    ListDraftsParameters,
    OpenDraftParameters,
    StartRunParameters,
)
from bh_sim.boundary.json_codec import boundary_from_json, boundary_json

from .history import HistoryService
from .pfd import PfdService
from .services import ApplicationServices, CommandRejected, DemonstrationService

_PFD_PARAMETERS = {
    "pfd.catalog": ListDraftsParameters,
    "pfd.list": ListDraftsParameters,
    "pfd.import": DraftParameters,
    "pfd.open": OpenDraftParameters,
    "pfd.save": c.PfdDocumentParameters,
    "pfd.restore": c.PfdDocumentParameters,
    "pfd.edit": c.PfdEditParameters,
    "quantity.display": c.QuantityDisplayParameters,
}

_HISTORY_PARAMETERS = {
    "history.start": c.PfdDocumentParameters,
    "history.list": ListDraftsParameters,
    "history.open": c.HistoryTarget,
    "history.view": c.HistoryTarget,
    "history.edit": c.HistoryEditParameters,
    "history.undo": c.HistoryTarget,
    "history.redo": c.HistoryTarget,
    "history.save": c.HistoryTarget,
    "history.snapshot": c.HistoryTarget,
    "history.branch": c.HistoryTarget,
    "history.compare": c.CompareHistoryParameters,
}

_PARAMETERS = {
    "draft.create": CreateDraftParameters,
    "draft.list": ListDraftsParameters,
    "draft.save": DraftParameters,
    "draft.open": OpenDraftParameters,
    "draft.validate": DraftParameters,
    "run.start": StartRunParameters,
    "run.cancel": CancelRunParameters,
    "run.inspect": InspectRunParameters,
    "run.inspect_attempt": InspectAttemptParameters,
    "run.list_attempts": ListAttemptsParameters,
    "run.select_last_valid": LastValidParameters,
    "run.compare": CompareRunsParameters,
    "demo.evaluate": DemonstrationParameters,
    "workbook.inspect": c.InspectWorkbookParameters,
    "result.select_display": c.SelectDisplayRunParameters,
    "result.overlays": c.GetOverlaysParameters,
    "graph.plot": c.PlotDataParameters,
}


class CommandRegistry:
    """One typed dispatcher for peer adapters; future commands fail explicitly.

    Exact request repeats return the recorded outcome in this process only. A restart
    loses this cache and receipts: this is not durable worker admission or replay.
    """

    def __init__(
        self,
        services: ApplicationServices | DemonstrationService,
        *,
        unavailable_commands: frozenset[str] = frozenset(),
        pfd: PfdService | None = None,
        history: HistoryService | None = None,
    ) -> None:
        self.services = services
        self.pfd = pfd
        self.history = history
        self._unavailable = unavailable_commands
        self._completed: dict[str, tuple[str, CommandOutcome]] = {}
        self._in_flight: set[str] = set()
        self._lock = RLock()

    @property
    def command_names(self) -> tuple[str, ...]:
        """Only implemented commands are advertised."""

        names = (
            ("demo.evaluate",)
            if isinstance(self.services, DemonstrationService)
            else tuple(_PARAMETERS)
        )
        return tuple(
            name
            for name in (
                *names,
                *(_PFD_PARAMETERS if self.pfd else ()),
                *(_HISTORY_PARAMETERS if self.history else ()),
            )
            if name not in self._unavailable
        )

    def dispatch(self, request: CommandRequest) -> CommandOutcome:
        """Reject unsupported authority, identity or shape before any use case."""

        if type(request) is not CommandRequest:
            return CommandOutcome(
                "",
                "REJECTED",
                diagnostics=(
                    DiagnosticDto(
                        "INVALID_COMMAND", "Expected CommandRequest", boundary="application"
                    ),
                ),
            )
        encoded: str | None = None
        with self._lock:
            try:
                encoded = boundary_json(request)
                # Capture a detached immutable snapshot once. Malformed requests
                # never enter the duplicate cache or reach an application port.
                request = boundary_from_json(encoded)
                if not request.request_id or not request.actor_id:
                    raise CommandRejected("INVALID_COMMAND", "Request and actor IDs are required")
                if request.schema_version != COMMAND_VERSION:
                    raise CommandRejected("VERSION_MISMATCH", "Unsupported command schema version")
                expected = (
                    {**_PARAMETERS, **_PFD_PARAMETERS, **_HISTORY_PARAMETERS}.get(
                        request.command_name
                    )
                    if request.command_name in self.command_names
                    else None
                )
                if expected is None:
                    raise CommandRejected("CAPABILITY_UNAVAILABLE", "Command is not implemented")
                if not isinstance(request.parameters, expected):
                    raise CommandRejected("INVALID_COMMAND", "Parameters do not match command")
                # The retained reference draft adapter fixes REVIEW. Do not silently
                # reinterpret a different profile as review or change model authority.
                if request.profile != "REVIEW":
                    raise CommandRejected(
                        "PROFILE_UNAVAILABLE", "This draft adapter supports REVIEW"
                    )
                prior = self._completed.get(request.request_id)
                if prior is not None:
                    if prior[0] != encoded:
                        raise CommandRejected("REQUEST_ID_CONFLICT", "Request ID was already used")
                    return prior[1]
                if request.request_id in self._in_flight:
                    raise CommandRejected("REQUEST_IN_FLIGHT", "Request ID is currently executing")
                self._in_flight.add(request.request_id)
            except CommandRejected as error:
                return self._rejected(request, error.code, str(error))
            except (KeyError, StopIteration):
                return self._rejected(request, "NOT_FOUND", "Requested identity was not found")
            except (TypeError, ValueError):
                return self._rejected(request, "INVALID_COMMAND", "Invalid command or draft input")
            except (OSError, RuntimeError):
                return self._rejected(request, "BOUNDARY_FAILURE", "An application port failed")

        outcome: CommandOutcome | None = None
        try:
            data = self._invoke(request)
            outcome = CommandOutcome(
                request.request_id,
                "COMPLETED",
                data,
                (),
                (CommandEvent(request.request_id, request.command_name, "COMPLETED"),),
            )
        except CommandRejected as error:
            outcome = self._rejected(request, error.code, str(error))
        except (KeyError, StopIteration):
            outcome = self._rejected(request, "NOT_FOUND", "Requested identity was not found")
        except (TypeError, ValueError):
            outcome = self._rejected(request, "INVALID_COMMAND", "Invalid command or draft input")
        except (OSError, RuntimeError):
            # Raw exception text can include unrestricted filesystem paths.
            outcome = self._rejected(request, "BOUNDARY_FAILURE", "An application port failed")
        except Exception:
            outcome = self._rejected(request, "BOUNDARY_FAILURE", "An application port failed")
        finally:
            with self._lock:
                self._in_flight.discard(request.request_id)
                if encoded is not None and request.request_id and outcome is not None:
                    self._completed[request.request_id] = (encoded, outcome)
        if outcome is None:
            outcome = self._rejected(request, "BOUNDARY_FAILURE", "An application port failed")
        return outcome

    @staticmethod
    def _rejected(request: CommandRequest, code: str, message: str) -> CommandOutcome:
        request_id = request.request_id if isinstance(request.request_id, str) else ""
        command_name = request.command_name if isinstance(request.command_name, str) else ""
        return CommandOutcome(
            request_id,
            "REJECTED",
            diagnostics=(DiagnosticDto(code, message, boundary="application"),),
            events=(CommandEvent(request_id, command_name, "REJECTED"),),
        )

    def _invoke(self, request: CommandRequest) -> CommandData:
        params = request.parameters
        if request.command_name in _HISTORY_PARAMETERS and self.history is not None:
            return self.history.dispatch(request)
        if request.command_name in _PFD_PARAMETERS and self.pfd is not None:
            if request.command_name == "pfd.catalog":
                return self.pfd.catalogue
            if request.command_name == "pfd.list":
                return self.pfd.listing()
            if isinstance(params, DraftParameters):
                return self.pfd.import_draft(params.draft)
            if isinstance(params, OpenDraftParameters):
                return self.pfd.open(params.draft_id)
            if isinstance(params, c.PfdDocumentParameters):
                self.pfd.check(params.document)
                return (
                    self.pfd.save(params.document)
                    if request.command_name == "pfd.save"
                    else params.document
                )
            if isinstance(params, c.PfdEditParameters):
                return self.pfd.edit(params.document, params.edit)
            if isinstance(params, c.QuantityDisplayParameters):
                return self.pfd.quantities.convert(params.quantity, params.target_unit)
        if isinstance(params, DemonstrationParameters):
            return self.services.demonstrate(params.name)
        if isinstance(self.services, DemonstrationService):
            raise CommandRejected(
                "CAPABILITY_UNAVAILABLE", "Only prototype demonstration is available"
            )
        if isinstance(params, CreateDraftParameters):
            return self.services.create_draft(params.draft_id)
        if isinstance(params, ListDraftsParameters):
            return self.services.list_drafts()
        if request.command_name == "draft.save" and isinstance(params, DraftParameters):
            return self.services.save_draft(params.draft)
        if request.command_name == "draft.validate" and isinstance(params, DraftParameters):
            return self.services.validate_draft(params.draft)
        if isinstance(params, OpenDraftParameters):
            return self.services.open_draft(params.draft_id)
        if isinstance(params, StartRunParameters):
            return self.services.start_run(params.draft, params.receipt_id)
        if isinstance(params, CancelRunParameters):
            return self.services.cancel_run(params.run_id, params.reason)
        if isinstance(params, InspectRunParameters):
            return self.services.inspect_run(params.run_id)
        if isinstance(params, InspectAttemptParameters):
            return self.services.inspect_attempt(params.attempt_id)
        if isinstance(params, ListAttemptsParameters):
            return self.services.list_attempts(params.case_id)
        if isinstance(params, LastValidParameters):
            return self.services.last_valid_run(params.case_id)
        if isinstance(params, CompareRunsParameters):
            return self.services.compare_runs(params.before_run_id, params.after_run_id)
        if isinstance(params, c.InspectWorkbookParameters):
            return self.services.inspect_workbook(params.case_id, params.run_id)
        if isinstance(params, c.SelectDisplayRunParameters):
            return self.services.select_display_run(params.case_id, params.run_id)
        if isinstance(params, c.GetOverlaysParameters):
            return self.services.get_overlays(params.case_id, params.run_id)
        if isinstance(params, c.PlotDataParameters):
            return self.services.get_plot_data(
                params.case_id, params.run_id, params.plot_kind, params.unit_id
            )
        raise CommandRejected("INVALID_COMMAND", "Parameters do not match command")
