"""DW1 authority, identity, immutable-input and failure behavior at real/mock ports."""

from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from typing import Any, cast

import pytest

from bh_sim.adapters.browser_format import from_browser, to_browser
from bh_sim.adapters.engineering import InProcessEngineeringAdapter
from bh_sim.adapters.reference import REFERENCE_MATERIAL_ID, REFERENCE_PACKAGE_ID
from bh_sim.adapters.storage import ArtifactRepositoryAdapter
from bh_sim.api.schemas import PfdDraftDto
from bh_sim.application.commands import CommandRegistry
from bh_sim.application.services import ApplicationServices
from bh_sim.boundary.contracts import (
    ArtifactReferenceDto,
    CalculatedRunDto,
    CommandParameters,
    CommandRequest,
    CompareRunsParameters,
    DemonstrationReportDto,
    DraftDto,
    DraftParameters,
    DraftSummaryDto,
    InspectRunParameters,
    LastValidParameters,
    ObjectPresentationDto,
    OpenDraftParameters,
    OverlaysDto,
    PlotDefinitionDto,
    PreparedRevisionDto,
    QuantityDto,
    ResultSelectionDto,
    RunAttemptRecord,
    RunViewDto,
    StartRunParameters,
    ValidationDto,
    ValidationReceiptDto,
    WorkbookDto,
)
from bh_sim.boundary.json_codec import boundary_from_json, boundary_json
from bh_sim.composition import create_registry, create_services
from bh_sim.engine.properties import PolynomialLiquidPackage
from tests.test_api import draft_payload


def neutral_draft() -> DraftDto:
    return from_browser(PfdDraftDto.model_validate(draft_payload()))


def request(
    name: str, params: CommandParameters, identifier: str = "request:one"
) -> CommandRequest:
    return CommandRequest(name, identifier, "owner:test", params)


def run_request(registry: CommandRegistry, draft: DraftDto, prefix: str) -> RunViewDto:
    outcome = registry.dispatch(request("draft.validate", DraftParameters(draft), prefix + ":v"))
    assert isinstance(outcome.data, ValidationReceiptDto), outcome
    result = registry.dispatch(
        request("run.start", StartRunParameters(draft, outcome.data.receipt_id), prefix + ":r")
    )
    assert isinstance(result.data, RunViewDto), result
    return result.data


def test_new_commands_require_receipt_and_reuse_validation_for_presentation(tmp_path: Path) -> None:
    registry = create_registry(tmp_path)
    draft = neutral_draft()
    missing = registry.dispatch(request("run.start", StartRunParameters(draft, "forged")))
    assert missing.diagnostics[0].code == "VALIDATION_REQUIRED"
    assert list((tmp_path / "drafts").glob("*.json")) == []
    validation = registry.dispatch(request("draft.validate", DraftParameters(draft), "validate"))
    assert isinstance(validation.data, ValidationReceiptDto)
    receipt = validation.data
    assert receipt.validation.valid
    assert list((tmp_path / "drafts").glob("*.json")) == []
    presentation = replace(
        draft.presentation,
        objects=(
            replace(draft.presentation.objects[0], label="Renamed source", x=99.0, y=101.0),
            *draft.presentation.objects[1:],
        ),
    )
    moved = replace(draft, presentation=presentation)
    result = registry.dispatch(
        request("run.start", StartRunParameters(moved, receipt.receipt_id), "run:moved")
    )
    assert isinstance(result.data, RunViewDto)
    assert result.data.convergence == "CONVERGED"
    services = cast(ApplicationServices, registry.services)
    before = services.engineering.prepare(draft)
    after = services.engineering.prepare(moved)
    assert before.engineering_hash == after.engineering_hash
    assert before.source_artifact_hash != after.source_artifact_hash
    # The ordinary artifact identity continues to include labels.
    loaded = registry.dispatch(
        request("run.inspect", InspectRunParameters(result.data.run_id), "inspect")
    )
    assert loaded.data == result.data


def test_engineering_edit_context_and_scope_invalidate_before_save(tmp_path: Path) -> None:
    registry = create_registry(tmp_path)
    services = cast(ApplicationServices, registry.services)
    draft = neutral_draft()
    receipt = services.validate_draft(draft)
    parameter = replace(draft.equipment[1].parameters[0], quantity=QuantityDto(600000.0, "W"))
    changed = replace(
        draft,
        equipment=(
            draft.equipment[0],
            replace(draft.equipment[1], parameters=(parameter,)),
            *draft.equipment[2:],
        ),
    )
    for number, target in enumerate((changed, replace(draft, draft_id="another-draft"))):
        result = registry.dispatch(
            request(
                "run.start", StartRunParameters(target, receipt.receipt_id), f"changed:{number}"
            )
        )
        assert result.diagnostics[0].code == "STALE_VALIDATION"
    engine = cast(InProcessEngineeringAdapter, services.engineering)
    package = cast(PolynomialLiquidPackage, engine.engine.properties.get(REFERENCE_PACKAGE_ID))
    package.version = "changed-configuration"
    result = registry.dispatch(
        request("run.start", StartRunParameters(draft, receipt.receipt_id), "changed:backend")
    )
    assert result.diagnostics[0].code == "STALE_VALIDATION"
    assert list((tmp_path / "drafts").glob("*.json")) == []
    # A fresh process/service has no trusted copy of the submitted receipt ID.
    reopened = create_registry(tmp_path)
    result = reopened.dispatch(request("run.start", StartRunParameters(draft, receipt.receipt_id)))
    assert result.diagnostics[0].code == "VALIDATION_REQUIRED"


def test_failed_run_retention_four_statuses_and_comparison(tmp_path: Path) -> None:
    registry = create_registry(tmp_path)
    good = run_request(registry, neutral_draft(), "good")
    payload = draft_payload()
    payload["nodes"][0]["data"]["parameters"]["temperature"]["quantity"]["value"] = 50.0
    bad = run_request(registry, from_browser(PfdDraftDto.model_validate(payload)), "bad")
    assert (bad.convergence, bad.closure, bad.physical_validity, bad.correlation_validity) == (
        "FAILED",
        "NOT_CHECKED",
        "INVALID",
        "UNKNOWN",
    )
    latest = registry.dispatch(
        request("run.select_last_valid", LastValidParameters(good.case_id), "latest")
    )
    assert latest.data == good
    inspected = registry.dispatch(
        request("run.inspect", InspectRunParameters(bad.run_id), "bad:view")
    )
    assert inspected.data == bad
    comparison = registry.dispatch(
        request("run.compare", CompareRunsParameters(good.run_id, bad.run_id), "compare")
    )
    assert comparison.disposition == "COMPLETED"
    assert comparison.data is not None
    from bh_sim.boundary.contracts import RunComparisonDto

    assert isinstance(comparison.data, RunComparisonDto)
    assert comparison.data.before == good.artifact
    assert comparison.data.after == bad.artifact
    assert {item.dimension for item in comparison.data.statuses} >= {
        "convergence",
        "closure",
        "physical_validity",
        "correlation_validity",
    }
    assert any(item.before is not None and item.after is None for item in comparison.data.metrics)


def test_exact_duplicate_is_session_local_and_conflicting_id_rejects(tmp_path: Path) -> None:
    registry = create_registry(tmp_path)
    services = cast(ApplicationServices, registry.services)
    draft = neutral_draft()
    receipt = services.validate_draft(draft)
    command = request("run.start", StartRunParameters(draft, receipt.receipt_id))
    first = registry.dispatch(command)
    assert registry.dispatch(command) == first
    assert registry.dispatch(replace(command, actor_id="someone-else")).diagnostics[0].code == (
        "REQUEST_ID_CONFLICT"
    )
    repeated = registry.dispatch(replace(command, request_id="run:explicit-second"))
    assert isinstance(first.data, RunViewDto) and isinstance(repeated.data, RunViewDto)
    assert first.data.run_id != repeated.data.run_id


def test_nested_types_immutability_and_malformed_ingress(tmp_path: Path) -> None:
    draft = neutral_draft()
    with pytest.raises(FrozenInstanceError):
        cast(Any, draft.equipment[0].parameters[0].quantity).value = 8.0
    with pytest.raises(TypeError):
        replace(draft, equipment=cast(Any, list(draft.equipment)))
    with pytest.raises(TypeError):
        replace(draft.equipment[0], parameters=(cast(Any, "not a DTO"),))
    with pytest.raises(ValueError):
        replace(draft.presentation, schema_version=cast(Any, "future"))
    with pytest.raises(ValueError):
        ObjectPresentationDto("source", extension_namespace="unreviewed")
    for value in (float("inf"), float("nan"), 10**1000):
        with pytest.raises((ValueError, TypeError)):
            ObjectPresentationDto("source", x=value)
        encoded = json.loads(boundary_json(ObjectPresentationDto("source")))
        encoded["x"] = value
        with pytest.raises((ValueError, TypeError)):
            boundary_from_json(json.dumps(encoded))
    with pytest.raises(ValueError):
        ObjectPresentationDto("source", extensions_json='{"value":NaN}')
    registry = create_registry(tmp_path)
    malformed = request("draft.save", DraftParameters(draft))
    object.__setattr__(malformed.parameters, "draft", "wrong type")
    assert registry.dispatch(malformed).diagnostics[0].code == "INVALID_COMMAND"
    for field, value in (("request_id", 1), ("command_name", None)):
        malformed = request("draft.open", OpenDraftParameters("some-draft"))
        object.__setattr__(malformed, field, value)
        assert registry.dispatch(malformed).diagnostics[0].code == "INVALID_COMMAND"
    assert registry.dispatch(cast(Any, OpenDraftParameters("draft"))).diagnostics[0].code == (
        "INVALID_COMMAND"
    )
    assert list((tmp_path / "drafts").glob("*.json")) == []


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"schema_version": "future"}, "VERSION_MISMATCH"),
        ({"command_name": "run.cancel"}, "CAPABILITY_UNAVAILABLE"),
        ({"profile": "EXPLORATION"}, "PROFILE_UNAVAILABLE"),
        ({"profile": "NARRATIVE"}, "PROFILE_UNAVAILABLE"),
        ({"actor_id": ""}, "INVALID_COMMAND"),
        ({"parameters": InspectRunParameters("run:x")}, "INVALID_COMMAND"),
    ],
)
def test_commands_reject_unsupported_contracts_before_ports(
    tmp_path: Path,
    changes: dict[str, Any],
    code: str,
) -> None:
    registry = create_registry(tmp_path)
    command = replace(request("draft.save", DraftParameters(neutral_draft())), **changes)
    assert registry.dispatch(command).diagnostics[0].code == code
    assert list((tmp_path / "drafts").glob("*.json")) == []


@pytest.mark.parametrize(
    "variation",
    [
        "empty_label",
        "cross_kind_ids",
        "reserved_extension",
        "parameter_alias",
        "duplicate_nodes",
        "duplicate_edges",
    ],
)
def test_all_legacy_saveable_shapes_round_trip(variation: str) -> None:
    payload = draft_payload()
    if variation == "empty_label":
        payload["nodes"][0]["data"]["label"] = ""
    elif variation == "cross_kind_ids":
        payload["edges"][0]["id"] = payload["nodes"][0]["id"]
    elif variation == "reserved_extension":
        payload["nodes"][0]["transientData"] = {"owner": "original extension"}
    elif variation == "parameter_alias":
        payload["nodes"][0]["data"]["parameters"]["mass_flow"] = deepcopy(
            payload["nodes"][0]["data"]["parameters"]["massFlow"]
        )
    elif variation == "duplicate_nodes":
        payload["nodes"][1]["id"] = payload["nodes"][0]["id"]
    else:
        payload["edges"][1]["id"] = payload["edges"][0]["id"]
        payload["edges"][1]["ownerExtra"] = "preserve this occurrence"
    original = PfdDraftDto.model_validate(payload)
    assert to_browser(from_browser(original)).model_dump() == original.model_dump()


def test_index_failure_is_sanitized_at_storage_port(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry = create_registry(tmp_path)
    services = cast(ApplicationServices, registry.services)
    adapter = cast(ArtifactRepositoryAdapter, services.artifacts)

    def failure(*args: object) -> None:
        raise sqlite3.OperationalError("private/path database is locked")

    monkeypatch.setattr(adapter.store, "load_run", failure)
    outcome = registry.dispatch(request("run.inspect", InspectRunParameters("run:x")))
    assert outcome.diagnostics[0].code == "BOUNDARY_FAILURE"
    assert "private/path" not in boundary_json(outcome)


def test_source_and_context_changes_are_explicit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    services = create_services(tmp_path)
    engineering = cast(InProcessEngineeringAdapter, services.engineering)
    receipt = services.validate_draft(neutral_draft())
    monkeypatch.setattr(engineering, "_read_source_digest", lambda: "changed")
    outcome = CommandRegistry(services).dispatch(
        request("run.start", StartRunParameters(neutral_draft(), receipt.receipt_id))
    )
    assert outcome.diagnostics[0].code == "BOUNDARY_FAILURE"
    assert list((tmp_path / "drafts").glob("*.json")) == []


def test_run_uses_snapshot_when_live_backend_changes_after_capture(tmp_path: Path) -> None:
    services = create_services(tmp_path)
    engineering = cast(InProcessEngineeringAdapter, services.engineering)
    draft = neutral_draft()
    prepared = engineering.prepare(draft)
    expected = engineering.context_hash()
    original_metadata = engineering._context_metadata
    live_package = cast(
        PolynomialLiquidPackage, engineering.engine.properties.get(REFERENCE_PACKAGE_ID)
    )
    original_liquid = live_package._liquids[REFERENCE_MATERIAL_ID]

    def mutate_after_snapshot(selected_engine: Any) -> str:
        if selected_engine is not engineering.engine:
            live_package._liquids[REFERENCE_MATERIAL_ID] = replace(
                original_liquid, cp_a_j_kg_k=2000.0
            )
        return original_metadata(selected_engine)

    engineering._context_metadata = mutate_after_snapshot
    result = engineering.run(prepared, expected_context_hash=expected)
    assert result.view.convergence == "CONVERGED"
    # Baseline heater delivers 800 K; changed live cp would instead deliver 550 K.
    heater = next(unit for unit in result.view.unit_results if unit.unit_id == "unit:heater-1")
    assert next(
        metric.quantity.value for metric in heater.metrics if metric.name == "outlet_temperature"
    ) == pytest.approx(800.0)
    assert engineering.context_hash() != expected


class RecordingPorts:
    """Independent protocol implementation with deterministic identities and no kernel."""

    def __init__(self) -> None:
        self.context = "context:A"
        self.calls: list[str] = []
        self.change_during_save = False

    def prepare(self, draft: DraftDto) -> PreparedRevisionDto:
        return PreparedRevisionDto("case:x", "revision:x", "{}", "{}", "a" * 64, "b" * 64, (), ())

    def context_hash(self) -> str:
        return self.context

    def validate(self, prepared: PreparedRevisionDto) -> ValidationDto:
        return ValidationDto(True, 0, ())

    def save(self, draft: DraftDto) -> DraftDto:
        self.calls.append("save_draft")
        return draft

    def latest(self, draft_id: str) -> DraftDto:
        return neutral_draft()

    def summaries(self) -> tuple[DraftSummaryDto, ...]:
        return ()

    def save_inputs(self, prepared: PreparedRevisionDto) -> None:
        self.calls.append("save_inputs")
        if self.change_during_save:
            self.context = "context:B"

    def run(
        self,
        prepared: PreparedRevisionDto,
        *,
        run_id: str | None = None,
        expected_context_hash: str | None = None,
    ) -> CalculatedRunDto:
        self.calls.append("run")
        assert expected_context_hash == self.context
        return CalculatedRunDto("{}", self.load_run(run_id or "run:fake"))

    def save_run(self, result: CalculatedRunDto) -> None:
        self.calls.append("save_run")

    def load_run(self, run_id: str) -> RunViewDto:
        return RunViewDto(
            run_id,
            "case:x",
            "revision:x",
            "2026-09-11T00:00:00Z",
            "CONVERGED",
            "PASSED",
            "VALID",
            "EXTRAPOLATED",
            (),
            (),
            ArtifactReferenceDto("RunResult", run_id, "a" * 64),
        )

    def latest_valid_run(self, case_id: str) -> RunViewDto | None:
        return None

    def record_attempt(self, attempt: RunAttemptRecord) -> RunAttemptRecord:
        return attempt

    def load_attempt(self, attempt_id: str) -> RunAttemptRecord | None:
        return None

    def list_attempts(self, case_id: str | None = None) -> tuple[RunAttemptRecord, ...]:
        return ()

    def reconcile_startup_attempts(self) -> tuple[RunAttemptRecord, ...]:
        return ()

    def promote_staged_run(
        self,
        staged_path: str,
        *,
        expected_run_id: str | None = None,
        expected_case_id: str | None = None,
        expected_revision_id: str | None = None,
        expected_hash: str | None = None,
    ) -> RunViewDto:
        return self.load_run(expected_run_id or "run:promoted")

    def get_workbook(self, case_id: str, run_id: str | None = None) -> WorkbookDto:
        return WorkbookDto(
            case_id,
            run_id or "run:fake",
            "flow:main",
            "CONVERGED",
            "PASSED",
            "VALID",
            "EXTRAPOLATED",
            (),
            (),
            (),
        )

    def get_overlays(self, case_id: str, run_id: str | None = None) -> OverlaysDto:
        return OverlaysDto(
            case_id,
            run_id or "run:fake",
            (),
            (),
            ResultSelectionDto(case_id, run_id, run_id, run_id, False),
        )

    def get_plot_data(
        self,
        case_id: str,
        run_id: str | None = None,
        plot_kind: str = "T_Q",
        unit_id: str | None = None,
    ) -> PlotDefinitionDto:
        return PlotDefinitionDto(
            plot_id=f"plot:{plot_kind}",
            title=plot_kind,
            x_label="x",
            y_label="y",
            plot_kind="T_Q",
            series=(),
        )

    def evaluate(self, name: str) -> DemonstrationReportDto:
        return DemonstrationReportDto("{}")


def test_mock_ports_enforce_admission_and_detect_context_change_during_persistence() -> None:
    ports = RecordingPorts()
    services = ApplicationServices(ports, ports, ports, ports)
    registry = CommandRegistry(services)
    draft = neutral_draft()
    missing = registry.dispatch(request("run.start", StartRunParameters(draft, "unknown")))
    assert missing.diagnostics[0].code == "VALIDATION_REQUIRED"
    assert ports.calls == []
    receipt = services.validate_draft(draft)
    ports.change_during_save = True
    changed = registry.dispatch(
        request("run.start", StartRunParameters(draft, receipt.receipt_id), "changed")
    )
    assert changed.diagnostics[0].code == "CONTEXT_CHANGED"
    assert ports.calls == ["save_draft", "save_inputs"]
    ports.change_during_save = False
    receipt = services.validate_draft(draft)
    completed = registry.dispatch(
        request("run.start", StartRunParameters(draft, receipt.receipt_id), "success")
    )
    assert isinstance(completed.data, RunViewDto)
    assert ports.calls[-4:] == ["save_draft", "save_inputs", "run", "save_run"]


def test_neutral_codec_fixed_request_and_outcome_fixtures() -> None:
    fixture_root = Path(__file__).parent / "fixtures" / "dw1_commands"
    for name in ("draft-open.command.json", "version-mismatch.outcome.json"):
        encoded = (fixture_root / name).read_text().strip()
        decoded = boundary_from_json(encoded)
        assert boundary_json(decoded) == encoded
    command = boundary_from_json((fixture_root / "draft-open.command.json").read_text())
    assert command == request("draft.open", OpenDraftParameters("draft:example"), "request:fixture")
    ports = RecordingPorts()
    registry = CommandRegistry(ApplicationServices(ports, ports, ports, ports))
    rejected = registry.dispatch(replace(command, schema_version="future"))
    assert (
        boundary_json(rejected)
        == (fixture_root / "version-mismatch.outcome.json").read_text().strip()
    )
    unknown = json.loads(boundary_json(command))
    unknown["notAField"] = 1
    with pytest.raises(ValueError):
        boundary_from_json(json.dumps(unknown))


def test_invalid_validation_receipt_and_units_are_explicit(tmp_path: Path) -> None:
    registry = create_registry(tmp_path)
    draft = neutral_draft()
    incomplete = replace(draft, connections=draft.connections[:-1])
    outcome = registry.dispatch(
        request("draft.validate", DraftParameters(incomplete), "incomplete:v")
    )
    assert isinstance(outcome.data, ValidationReceiptDto)
    assert not outcome.data.validation.valid
    rejected = registry.dispatch(
        request(
            "run.start", StartRunParameters(incomplete, outcome.data.receipt_id), "incomplete:r"
        )
    )
    assert rejected.diagnostics[0].code == "VALIDATION_FAILED"
    payload = draft_payload()
    payload["nodes"][0]["data"]["parameters"]["temperature"]["quantity"]["unit"] = "furlong"
    wrong_units = from_browser(PfdDraftDto.model_validate(payload))
    outcome = registry.dispatch(request("draft.validate", DraftParameters(wrong_units), "bad-unit"))
    assert outcome.diagnostics[0].code == "INVALID_DRAFT"
    assert "unknown unit" in outcome.diagnostics[0].message
    assert list((tmp_path / "drafts").glob("*.json")) == []


def test_unknown_presentation_content_cannot_be_silently_dropped(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        ObjectPresentationDto("source", extensions_json='{"unreviewed":{}}')
    draft = neutral_draft()
    presentation = replace(
        draft.presentation,
        objects=(
            *draft.presentation.objects,
            ObjectPresentationDto("absent-object"),
        ),
    )
    command = request("draft.save", DraftParameters(replace(draft, presentation=presentation)))
    result = create_registry(tmp_path).dispatch(command)
    assert result.diagnostics[0].code == "INVALID_COMMAND"
    assert list((tmp_path / "drafts").glob("*.json")) == []


def test_legacy_validation_still_reports_nonfinite_quantity(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from bh_sim.api import create_app

    payload = draft_payload()
    payload["nodes"][0]["data"]["parameters"]["temperature"]["quantity"]["value"] = "NaN"
    result = TestClient(create_app(tmp_path)).post(
        "/api/v1alpha/drafts/thermal-loop-concept/validate",
        json=payload,
    )
    assert result.status_code == 200
    assert result.json()["data"] == {
        "valid": False,
        "degreesOfFreedom": 0,
        "diagnostics": [
            {
                "severity": "error",
                "code": "INVALID_DRAFT",
                "message": "quantity value must be finite",
                "subjectId": None,
            }
        ],
    }
