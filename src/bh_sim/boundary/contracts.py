"""DW1 command contracts, independent of HTTP, scientific and desktop libraries.

Quantities carry submitted units; these types never convert engineering values.
Presentation extension strings are JSON, not executable or runtime objects.
Commands are synchronous in DW1: completion is not worker lifecycle admission.
"""

from __future__ import annotations

import hashlib
import json
import math
import types
from dataclasses import dataclass, fields, is_dataclass
from functools import lru_cache
from typing import Literal, Union, cast, get_args, get_origin, get_type_hints

COMMAND_VERSION = "bh-command-v1alpha"
ENGINEERING_HASH_SCHEME = "bh-engineering-v1alpha"


@lru_cache(maxsize=128)
def _contract_hints(contract: type) -> dict:
    """Cache static schema reflection, never values or validation outcomes.

    DW3 measured 191 ms for a 50-unit edit before this cache. Every payload is
    still deeply validated; declared contract classes do not change at runtime.
    """
    return get_type_hints(contract)


def _check_value(value: object, hint: object) -> None:
    """Reject mutable, non-finite and structurally mistyped nested boundary values."""
    origin = get_origin(hint)
    arguments = get_args(hint)
    if origin in (types.UnionType, Union):
        for member in arguments:
            try:
                _check_value(value, member)
                return
            except (TypeError, ValueError):
                pass
        raise TypeError("value does not match declared alternatives")
    if origin is Literal:
        if value not in arguments or not any(type(value) is type(item) for item in arguments):
            raise ValueError("unsupported literal value")
    elif origin is tuple:
        if not isinstance(value, tuple):
            raise TypeError("boundary collections must be immutable tuples")
        if len(arguments) == 2 and arguments[1] is Ellipsis:
            for item in value:
                _check_value(item, arguments[0])
        else:
            if len(value) != len(arguments):
                raise TypeError("wrong tuple length")
            for item, member in zip(value, arguments, strict=True):
                _check_value(item, member)
    elif hint is float:
        if type(value) not in (float, int):
            raise ValueError("expected finite scalar")
        try:
            finite = math.isfinite(cast(float | int, value))
        except OverflowError as error:
            raise ValueError("scalar is outside the finite float range") from error
        if not finite:
            raise ValueError("expected finite scalar")
    elif hint is type(None):
        if value is not None:
            raise TypeError("expected null")
    elif hint in (str, int, bool):
        if type(value) is not hint:
            raise TypeError("wrong boundary primitive type")
    elif isinstance(hint, type) and is_dataclass(hint):
        if type(value) is not hint:
            raise TypeError("wrong nested boundary DTO type")
        hints = _contract_hints(hint)
        for field in fields(hint):
            _check_value(getattr(value, field.name), hints[field.name])
    else:
        raise TypeError("unsupported boundary value type")


class _ImmutableBoundary:
    """Validate deep immutable structure at every public DTO construction."""

    def __post_init__(self) -> None:
        _check_value(self, type(self))


@dataclass(frozen=True)
class QuantityDto(_ImmutableBoundary):
    """Finite scalar with explicit unit text; domain adapters validate dimensions."""

    value: float
    unit: str

    def __post_init__(self) -> None:
        try:
            finite = type(self.value) in (float, int) and math.isfinite(self.value)
        except OverflowError as error:
            raise ValueError("quantity value must be finite") from error
        if not finite:
            raise ValueError("quantity value must be finite")
        super().__post_init__()


@dataclass(frozen=True)
class ParameterDto(_ImmutableBoundary):
    """Named calculation input; UI captions belong to presentation metadata."""

    name: str
    quantity: QuantityDto


@dataclass(frozen=True)
class EquipmentDto(_ImmutableBoundary):
    """Equipment identifier, catalogue identifier and explicit parameters."""

    object_id: str
    model_id: str
    parameters: tuple[ParameterDto, ...]


@dataclass(frozen=True)
class ConnectionDto(_ImmutableBoundary):
    """Connection with catalogue-declared local port locators, not graph objects.

    The reference catalogue uses in-N/out-N local locators. None retains the legacy
    first-port default; invalid locators may be saved but fail authoritative validation.
    """

    object_id: str
    source_id: str
    target_id: str
    source_port: str | None
    target_port: str | None


@dataclass(frozen=True)
class ParameterPresentationDto(_ImmutableBoundary):
    """A parameter caption and description, separate from its quantity."""

    name: str
    label: str
    description: str | None = None


@dataclass(frozen=True)
class ObjectPresentationDto(_ImmutableBoundary):
    """Object layout/labels and an opaque compatibility extension JSON object.

    Extensions are retained for adapter round-trip only. They cannot affect domain
    conversion or dispatch. DW1 reserves the namespace react-flow/v1alpha.
    """

    object_id: str
    label: str | None = None
    x: float | None = None
    y: float | None = None
    parameters: tuple[ParameterPresentationDto, ...] = ()
    extension_namespace: str = "react-flow/v1alpha"
    extensions_json: str = "{}"
    object_kind: Literal["equipment", "connection"] = "equipment"
    occurrence: int = 0

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.extension_namespace != "react-flow/v1alpha":
            raise ValueError("unsupported presentation extension namespace")
        if self.occurrence < 0:
            raise ValueError("presentation occurrence must be nonnegative")

        def reject_constant(value: str) -> None:
            raise ValueError(f"non-finite JSON constant: {value}")

        extension = json.loads(self.extensions_json, parse_constant=reject_constant)
        if not isinstance(extension, dict):
            raise ValueError("presentation extensions must be a JSON object")
        allowed = {"node", "runtime"} if self.object_kind == "equipment" else {"edge"}
        if set(extension) - allowed or any(
            not isinstance(value, dict) for value in extension.values()
        ):
            raise ValueError("unsupported presentation extension framing")


@dataclass(frozen=True)
class PresentationDto(_ImmutableBoundary):
    """Versioned presentation state keyed to equipment and connection IDs."""

    objects: tuple[ObjectPresentationDto, ...]
    schema_version: Literal["bh-presentation-v1alpha"] = "bh-presentation-v1alpha"


@dataclass(frozen=True)
class DraftDto(_ImmutableBoundary):
    """A saveable, possibly incomplete draft; saving never approves a case."""

    draft_id: str
    revision: int
    base_case_id: str | None
    updated_at: str
    equipment: tuple[EquipmentDto, ...]
    connections: tuple[ConnectionDto, ...]
    presentation: PresentationDto


@dataclass(frozen=True)
class DiagnosticDto(_ImmutableBoundary):
    """Stable boundary failure or engineering diagnostic without secret traces."""

    code: str
    message: str
    severity: Literal["info", "warning", "error"] = "error"
    subject_id: str | None = None
    field: str | None = None
    boundary: str | None = None


@dataclass(frozen=True)
class ArtifactReferenceDto(_ImmutableBoundary):
    """Immutable artifact identity; filesystem paths are adapter-private."""

    artifact_kind: str
    artifact_id: str
    content_hash: str
    schema_version: str = "v1alpha"


@dataclass(frozen=True)
class PreparedRevisionDto(_ImmutableBoundary):
    """Canonical domain bytes and mappings produced only by the engineering port.

    The opaque JSON strings retain the existing scientific codec and bytes. These
    are internal port values; UI callers cannot submit a prepared revision to Run.
    """

    case_id: str
    revision_id: str
    case_json: str
    revision_json: str
    source_artifact_hash: str
    engineering_hash: str
    node_ids: tuple[tuple[str, str], ...]
    edge_ids: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class ValidationDto(_ImmutableBoundary):
    """Authoritative compiler result, distinct from numerical result statuses."""

    valid: bool
    degrees_of_freedom: int
    diagnostics: tuple[DiagnosticDto, ...]


@dataclass(frozen=True)
class ValidationReceiptDto(_ImmutableBoundary):
    """Service-issued validation identity; the service retains the original."""

    receipt_id: str
    draft_id: str
    revision_id: str
    source_artifact_hash: str
    engineering_hash: str
    execution_context_hash: str
    validation: ValidationDto
    engineering_hash_scheme: str = ENGINEERING_HASH_SCHEME
    worker_session_id: str | None = None


@dataclass(frozen=True)
class MetricDto(_ImmutableBoundary):
    """Named returned quantity; formatting is a presentation adapter concern."""

    name: str
    quantity: QuantityDto


@dataclass(frozen=True)
class UnitResultDto(_ImmutableBoundary):
    """Calculated unit metrics and declared validity, without a widget status."""

    unit_id: str
    validity: Literal["VALID", "EXTRAPOLATED", "INVALID", "UNKNOWN"]
    metrics: tuple[MetricDto, ...]


@dataclass(frozen=True)
class RunViewDto(_ImmutableBoundary):
    """Immutable result view retaining all four independent scientific states."""

    run_id: str
    case_id: str
    revision_id: str | None
    completed_at: str
    convergence: Literal["NOT_RUN", "CONVERGED", "FAILED"]
    closure: Literal["NOT_CHECKED", "PASSED", "FAILED"]
    physical_validity: Literal["VALID", "EXTRAPOLATED", "INVALID", "UNKNOWN"]
    correlation_validity: Literal["VALID", "EXTRAPOLATED", "INVALID", "UNKNOWN"]
    unit_results: tuple[UnitResultDto, ...]
    diagnostics: tuple[DiagnosticDto, ...]
    artifact: ArtifactReferenceDto


@dataclass(frozen=True)
class CalculatedRunDto(_ImmutableBoundary):
    """Kernel output awaiting persistence; view alone is not a save receipt."""

    canonical_json: str
    view: RunViewDto


@dataclass(frozen=True)
class RunExecutionDto(_ImmutableBoundary):
    """Saved input identities and persisted result for a synchronous DW1 Run."""

    draft: DraftDto
    prepared: PreparedRevisionDto
    result: RunViewDto


@dataclass(frozen=True)
class MetricChangeDto(_ImmutableBoundary):
    """Before/after quantities; absence and unit differences stay explicit."""

    unit_id: str
    metric_name: str
    before: QuantityDto | None
    after: QuantityDto | None


@dataclass(frozen=True)
class StatusChangeDto(_ImmutableBoundary):
    """Change in one scientific status dimension, optionally for a unit."""

    dimension: str
    before: str | None
    after: str | None
    unit_id: str | None = None


@dataclass(frozen=True)
class RunComparisonDto(_ImmutableBoundary):
    """Two immutable run references and returned metric/status differences."""

    before: ArtifactReferenceDto
    after: ArtifactReferenceDto
    metrics: tuple[MetricChangeDto, ...]
    statuses: tuple[StatusChangeDto, ...]


@dataclass(frozen=True)
class DemonstrationReportDto(_ImmutableBoundary):
    """Opaque legacy prototype report JSON; not a promoted flowsheet model."""

    report_json: str

    def to_dict(self) -> dict:
        """Retain the prototype report consumer shape; returns a detached copy."""
        return json.loads(self.report_json)


@dataclass(frozen=True)
class DraftSummaryDto(_ImmutableBoundary):
    """Latest saved draft identity for navigation; no calculated values."""

    draft_id: str
    revision: int
    updated_at: str


@dataclass(frozen=True)
class DraftListDto(_ImmutableBoundary):
    """Read-only saved draft catalogue."""

    drafts: tuple[DraftSummaryDto, ...]


@dataclass(frozen=True)
class CreateDraftParameters(_ImmutableBoundary):
    """Owner-supplied draft name/identity; creation does not save or validate."""

    draft_id: str


@dataclass(frozen=True)
class ListDraftsParameters(_ImmutableBoundary):
    """Explicit request for saved draft navigation entries."""


@dataclass(frozen=True)
class DraftParameters(_ImmutableBoundary):
    """Draft command input."""

    draft: DraftDto


@dataclass(frozen=True)
class OpenDraftParameters(_ImmutableBoundary):
    """Explicitly selected draft identity."""

    draft_id: str


@dataclass(frozen=True)
class StartRunParameters(_ImmutableBoundary):
    """Exact draft snapshot and a previously issued validation receipt ID."""

    draft: DraftDto
    receipt_id: str


@dataclass(frozen=True)
class InspectRunParameters(_ImmutableBoundary):
    """Explicitly selected immutable run identity."""

    run_id: str


@dataclass(frozen=True)
class LastValidParameters(_ImmutableBoundary):
    """Case identity whose last acceptable result is requested."""

    case_id: str


@dataclass(frozen=True)
class CompareRunsParameters(_ImmutableBoundary):
    """Two explicitly selected immutable runs; no rerun is performed."""

    before_run_id: str
    after_run_id: str


@dataclass(frozen=True)
class DemonstrationParameters(_ImmutableBoundary):
    """One of the retained prototype CLI demonstrations."""

    name: str


@dataclass(frozen=True)
class CancelRunParameters(_ImmutableBoundary):
    """Cancel in-flight solver execution."""

    run_id: str
    reason: str = "User cancelled"


@dataclass(frozen=True)
class InspectAttemptParameters(_ImmutableBoundary):
    """Retrieve operational attempt lifecycle record."""

    attempt_id: str


@dataclass(frozen=True)
class ListAttemptsParameters(_ImmutableBoundary):
    """List operational attempt records for a case or all cases."""

    case_id: str | None = None


@dataclass(frozen=True)
class CanvasPointDto(_ImmutableBoundary):
    """Finite presentation coordinates in logical scene units, never physical units."""

    x: float
    y: float


@dataclass(frozen=True)
class InputNotationDto(_ImmutableBoundary):
    """Original submitted notation and optional display override; no inferred precision."""

    name: str
    text: str
    unit: str
    display_unit: str | None = None


@dataclass(frozen=True)
class UnitPreferenceDto(_ImmutableBoundary):
    """Display-unit choice keyed by a catalogue parameter's canonical unit."""

    canonical_unit: str
    display_unit: str


@dataclass(frozen=True)
class VisualStreamGroup(_ImmutableBoundary):
    """Presentation-only named stream membership; overlap is explicitly permitted."""

    group_id: str
    name: str
    member_stream_ids: tuple[str, ...] = ()
    highlight_colour: str = "#FFD166"
    order: int = 0
    visible: bool = True
    schema_version: Literal["bh-visual-stream-group-v1"] = "bh-visual-stream-group-v1"

    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.group_id.strip() or not self.name.strip():
            raise ValueError("visual group identity and name are required")
        if len(set(self.member_stream_ids)) != len(self.member_stream_ids):
            raise ValueError("visual group contains duplicate stream identities")
        if len(self.highlight_colour) != 7 or not self.highlight_colour.startswith("#"):
            raise ValueError("highlight colour must be #RRGGBB")
        int(self.highlight_colour[1:], 16)


@dataclass(frozen=True)
class EngineeringSubsystem(_ImmutableBoundary):
    """Versioned engineering grouping whose membership participates in project hashing."""

    subsystem_id: str
    name: str
    member_object_ids: tuple[str, ...] = ()
    purpose: str = ""
    metadata: tuple[tuple[str, str], ...] = ()
    revision_provenance: str = "draft"
    schema_version: Literal["bh-engineering-subsystem-v1"] = "bh-engineering-subsystem-v1"

    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.subsystem_id.strip() or not self.name.strip():
            raise ValueError("engineering subsystem identity and name are required")
        if len(set(self.member_object_ids)) != len(self.member_object_ids):
            raise ValueError("engineering subsystem contains duplicate object identities")
        if len(dict(self.metadata)) != len(self.metadata):
            raise ValueError("engineering subsystem metadata keys must be unique")


@dataclass(frozen=True)
class PfdEngineeringIdentity(_ImmutableBoundary):
    """Project-level engineering content used to stale subsystem-dependent validation."""

    equipment: tuple[EquipmentDto, ...]
    connections: tuple[ConnectionDto, ...]
    subsystems: tuple[EngineeringSubsystem, ...]
    schema_version: Literal["bh-pfd-engineering-identity-v1"] = "bh-pfd-engineering-identity-v1"


@dataclass(frozen=True)
class PfdLayerPreferences(_ImmutableBoundary):
    """Presentation styling, overlays and motion preferences; never result authority."""

    active_visual_group_id: str | None = None
    active_result_layer: (
        Literal["temperature", "pressure", "mass-flow", "duty", "validity"] | None
    ) = None
    base_stream_colour: str = "#A4C7CE"
    show_labels: bool = True
    line_style: Literal["solid", "dash", "dot"] = "solid"
    line_width: float = 2.0
    animation_fps: Literal[0, 15, 30, 60] = 30
    animation_speed_scale: float = 1.0
    reduced_motion: bool = False
    follow_system_reduced_motion: bool = True
    show_direction_arrows: bool = True
    show_legend: bool = True
    schema_version: Literal["bh-pfd-layer-preferences-v1"] = "bh-pfd-layer-preferences-v1"

    def __post_init__(self) -> None:
        super().__post_init__()
        if not 0.5 <= self.line_width <= 12 or not 0.1 <= self.animation_speed_scale <= 10:
            raise ValueError("layer line width or animation speed is outside the supported range")
        if len(self.base_stream_colour) != 7 or not self.base_stream_colour.startswith("#"):
            raise ValueError("base stream colour must be #RRGGBB")
        int(self.base_stream_colour[1:], 16)


@dataclass(frozen=True)
class FlowStreamVisualization(_ImmutableBoundary):
    """One stream value from an attributable run artifact or telemetry frame."""

    stream_id: str
    signed_flow: float | None
    direction: Literal["forward", "reverse", "stationary", "unavailable"]
    unit: str
    status: Literal[
        "VALID", "INVALID", "EXTRAPOLATED", "UNCONVERGED", "STALE", "FAILED", "UNAVAILABLE"
    ]

    def __post_init__(self) -> None:
        super().__post_init__()
        expected = (
            "unavailable"
            if self.signed_flow is None
            else "forward"
            if self.signed_flow > 0
            else "reverse"
            if self.signed_flow < 0
            else "stationary"
        )
        if self.direction != expected:
            raise ValueError("flow direction must agree with the signed flow value")
        if self.signed_flow is None and self.status != "UNAVAILABLE":
            raise ValueError("missing flow data requires UNAVAILABLE status")
        if self.signed_flow is not None and not self.unit.strip():
            raise ValueError("finite flow visualization data requires units")


@dataclass(frozen=True)
class FlowVisualizationFrame(_ImmutableBoundary):
    """Typed visualization input; this contract does not calculate or infer flow."""

    source_artifact_id: str
    timestamp: float
    streams: tuple[FlowStreamVisualization, ...]
    source_kind: Literal["completed-run", "dynamic-telemetry"]
    schema_version: Literal["bh-flow-visualization-frame-v1"] = "bh-flow-visualization-frame-v1"

    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.source_artifact_id.strip():
            raise ValueError("flow visualization requires a source artifact")
        if len({stream.stream_id for stream in self.streams}) != len(self.streams):
            raise ValueError("flow visualization stream identities must be unique")


@dataclass(frozen=True)
class PfdSettingsDto(_ImmutableBoundary):
    """Versioned, non-executable case preferences; templates cannot carry engineering inputs."""

    grid_spacing: float = 20.0
    snap_radius: float = 8.0
    snap_grid: bool = True
    snap_alignment: bool = True
    snap_ports: bool = True
    crossing: Literal["vertical-gap", "bridge"] = "vertical-gap"
    stream_prefix: str = "S-"
    stream_start: int = 1
    stream_padding: int = 3
    branch_names: Literal["suffix", "independent"] = "suffix"
    prompt_stream_name: bool = False
    collision: Literal["resolve", "next-available"] = "resolve"
    original_on_edit: bool = True
    display_precision: int = 6
    significant_figures: int = 4
    significant_mode: bool = False
    units: tuple[UnitPreferenceDto, ...] = ()
    shortcuts: tuple[tuple[str, str], ...] = ()
    detail_fields: tuple[str, ...] = ("inputs", "status")
    background_colour: str = "#121B22"
    stream_colour: str = "#A4C7CE"
    missing_colour: str = "#F0B673"
    handle_size: float = 6.0
    schema_version: Literal["bh-pfd-settings-v1"] = "bh-pfd-settings-v1"

    def __post_init__(self) -> None:
        super().__post_init__()
        if not 2 <= self.grid_spacing <= 200 or not 0 <= self.snap_radius <= 40:
            raise ValueError("grid/snap setting outside supported range")
        if not 2 <= self.handle_size <= 20:
            raise ValueError("handle size outside supported range")
        if not 1 <= self.display_precision <= 15 or not 1 <= self.significant_figures <= 15:
            raise ValueError("display precision must be between 1 and 15")
        if not 0 <= self.stream_start <= 999999 or not 1 <= self.stream_padding <= 8:
            raise ValueError("stream numbering setting outside supported range")
        if len(self.stream_prefix) > 20 or any(ord(c) < 32 for c in self.stream_prefix):
            raise ValueError("invalid stream prefix")
        for colour in (self.background_colour, self.stream_colour, self.missing_colour):
            if len(colour) != 7 or not colour.startswith("#"):
                raise ValueError("colours must be #RRGGBB")
            int(colour[1:], 16)
        if len(dict(self.shortcuts)) != len(self.shortcuts):
            raise ValueError("duplicate shortcut command")
        if any(len(key) > 80 or len(value) > 80 for key, value in self.shortcuts):
            raise ValueError("shortcut entry exceeds supported length")
        if len({u.canonical_unit for u in self.units}) != len(self.units):
            raise ValueError("duplicate unit preference")
        if not set(self.detail_fields) <= {
            "inputs",
            "status",
            "temperature",
            "pressure",
            "massFlow",
            "duty",
            "effectiveness",
            "targetTemperature",
            "emissivity",
            "splitFraction",
        }:
            raise ValueError("unknown detail field")


@dataclass(frozen=True)
class PfdObjectDto(_ImmutableBoundary):
    """Native object presentation, input notation and explicit branch naming lineage."""

    object_id: str
    tag: str
    position: CanvasPointDto = CanvasPointDto(0.0, 0.0)
    route: tuple[CanvasPointDto, ...] = ()
    notation: tuple[InputNotationDto, ...] = ()
    expanded: bool = False
    pinned: bool = False
    parent_stream_id: str | None = None
    branch_suffix: str | None = None


@dataclass(frozen=True)
class PfdDocumentDto(_ImmutableBoundary):
    """Native immutable draft envelope; canonical scientific artifacts are unchanged."""

    draft: DraftDto
    objects: tuple[PfdObjectDto, ...]
    settings: PfdSettingsDto = PfdSettingsDto()
    viewport_centre: CanvasPointDto = CanvasPointDto(0.0, 0.0)
    viewport_scale: float = 1.0
    next_stream_number: int = 1
    visual_groups: tuple[VisualStreamGroup, ...] = ()
    engineering_subsystems: tuple[EngineeringSubsystem, ...] = ()
    layer_preferences: PfdLayerPreferences = PfdLayerPreferences()
    schema_version: Literal["bh-pfd-document-v1"] = "bh-pfd-document-v1"

    def __post_init__(self) -> None:
        super().__post_init__()
        if not 0.1 <= self.viewport_scale <= 4.0 or self.next_stream_number < 0:
            raise ValueError("invalid presentation viewport/numbering state")


def pfd_engineering_content_hash(document: PfdDocumentDto) -> str:
    """Hash engineering objects and subsystem membership, excluding presentation state."""
    from .json_codec import boundary_json

    identity = PfdEngineeringIdentity(
        document.draft.equipment,
        document.draft.connections,
        tuple(sorted(document.engineering_subsystems, key=lambda item: item.subsystem_id)),
    )
    return hashlib.sha256(boundary_json(identity).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PfdPortDto(_ImmutableBoundary):
    """Catalogue-declared connection compatibility, not compiled graph state."""

    name: str
    direction: Literal["input", "output"]
    kind: Literal["material", "energy"] = "material"
    maximum_connections: int = 1


@dataclass(frozen=True)
class PfdParameterDto(_ImmutableBoundary):
    """Required reference-fixture input descriptor; no numerical default is implied."""

    name: str
    title: str
    canonical_unit: str


@dataclass(frozen=True)
class PfdModelDto(_ImmutableBoundary):
    """Reviewed descriptor mapping to an existing model, not scientific promotion."""

    model_id: str
    title: str
    ports: tuple[PfdPortDto, ...]
    parameters: tuple[PfdParameterDto, ...]
    authority: str = "TEST FIXTURE ONLY — evidence not approved"


@dataclass(frozen=True)
class PfdCatalogueDto(_ImmutableBoundary):
    """Neutral reference-model descriptor inventory; no implementations."""

    models: tuple[PfdModelDto, ...]


@dataclass(frozen=True)
class WorkspaceDocumentRevision(_ImmutableBoundary):
    """Stable link to one independently versioned workspace document."""

    document_id: str
    revision: int
    contract_version: str


@dataclass(frozen=True)
class WorkspaceProjectManifest(_ImmutableBoundary):
    """Project links; absence means a capability has not produced that document."""

    project_id: str
    flowsheet: WorkspaceDocumentRevision
    dynamics: WorkspaceDocumentRevision | None = None
    controls: WorkspaceDocumentRevision | None = None
    schema_version: Literal["bh-workspace-project-manifest-v1"] = "bh-workspace-project-manifest-v1"


@dataclass(frozen=True)
class SignalPort(_ImmutableBoundary):
    """Future unit-aware signal endpoint; no solver or scheduling implementation."""

    port_id: str
    name: str
    direction: Literal["input", "output"]
    signal_type: Literal["real", "integer", "boolean", "event"]
    unit: str | None = None


@dataclass(frozen=True)
class ControlBlock(_ImmutableBoundary):
    """Declarative control block configuration for a future replaceable engine."""

    block_id: str
    block_type: Literal[
        "pid", "transfer-function", "state-space", "logic", "limit", "delay", "user"
    ]
    ports: tuple[SignalPort, ...]
    parameters: tuple[tuple[str, str], ...] = ()
    sample_time: float | None = None
    execution_order: int = 0

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.sample_time is not None and self.sample_time <= 0:
            raise ValueError("control sample time must be positive")
        if len({port.port_id for port in self.ports}) != len(self.ports):
            raise ValueError("control block port identities must be unique")
        if len(dict(self.parameters)) != len(self.parameters):
            raise ValueError("control block parameter keys must be unique")


@dataclass(frozen=True)
class ControlSignalConnection(_ImmutableBoundary):
    """Directed typed signal connection; algebraic loops remain engine diagnostics."""

    connection_id: str
    source_block_id: str
    source_port_id: str
    target_block_id: str
    target_port_id: str


@dataclass(frozen=True)
class ControlSchedule(_ImmutableBoundary):
    """Future deterministic scheduler configuration; no integrator is selected here."""

    base_tick: float
    start_time: float
    end_time: float
    event_ordering: Literal["time-then-execution-order-then-id"] = (
        "time-then-execution-order-then-id"
    )

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.base_tick <= 0 or self.end_time < self.start_time:
            raise ValueError("invalid control schedule interval")


@dataclass(frozen=True)
class ControlEvent(_ImmutableBoundary):
    """Ordered future control event retained separately from continuous state."""

    event_id: str
    timestamp: float
    source_block_id: str
    port_id: str
    value: str
    execution_order: int


@dataclass(frozen=True)
class SignalValue(_ImmutableBoundary):
    """One typed signal sample exchanged at a deterministic co-simulation boundary."""

    signal_id: str
    signal_type: Literal["real", "integer", "boolean", "event"]
    value: float | int | bool | str
    unit: str | None

    def __post_init__(self) -> None:
        super().__post_init__()
        valid = {
            "real": type(self.value) in (float, int) and not isinstance(self.value, bool),
            "integer": type(self.value) is int,
            "boolean": type(self.value) is bool,
            "event": type(self.value) is str,
        }[self.signal_type]
        if not valid:
            raise ValueError("signal value does not match its declared signal type")
        if self.signal_type in {"real", "integer"} and not self.unit:
            raise ValueError("numeric signal values require explicit units")


@dataclass(frozen=True)
class CoSimulationExchange(_ImmutableBoundary):
    """Future bounded plant/control exchange; complete trajectories stay in artifacts."""

    exchange_id: str
    timestamp: float
    signals: tuple[SignalValue, ...]
    events: tuple[ControlEvent, ...] = ()
    sequence: int = 0
    schema_version: Literal["bh-co-simulation-exchange-v1"] = "bh-co-simulation-exchange-v1"


@dataclass(frozen=True)
class ControlTrajectoryReference(_ImmutableBoundary):
    """Separate complete artifact and optional decimated UI telemetry references."""

    complete_artifact_id: str
    complete_artifact_sha256: str
    telemetry_artifact_id: str | None = None
    telemetry_artifact_sha256: str | None = None
    schema_version: Literal["bh-control-trajectory-reference-v1"] = (
        "bh-control-trajectory-reference-v1"
    )

    def __post_init__(self) -> None:
        super().__post_init__()
        hashes = (self.complete_artifact_sha256, self.telemetry_artifact_sha256)
        for value in hashes:
            if value is not None:
                if len(value) != 64:
                    raise ValueError("trajectory artifact hash must be SHA-256")
                int(value, 16)
        if (self.telemetry_artifact_id is None) != (self.telemetry_artifact_sha256 is None):
            raise ValueError("telemetry identity and hash must be present together")


@dataclass(frozen=True)
class ControlDiagram(_ImmutableBoundary):
    """Versioned control graph document reserved for M7/M9 numerical implementation."""

    diagram_id: str
    revision: int
    blocks: tuple[ControlBlock, ...] = ()
    connections: tuple[ControlSignalConnection, ...] = ()
    event_ordering: Literal["time-then-execution-order-then-id"] = (
        "time-then-execution-order-then-id"
    )
    schema_version: Literal["bh-control-diagram-v1"] = "bh-control-diagram-v1"

    def __post_init__(self) -> None:
        super().__post_init__()
        block_ids = {block.block_id for block in self.blocks}
        if len(block_ids) != len(self.blocks):
            raise ValueError("control block identities must be unique")
        if len({edge.connection_id for edge in self.connections}) != len(self.connections):
            raise ValueError("control connection identities must be unique")
        ports = {
            (block.block_id, port.port_id): port for block in self.blocks for port in block.ports
        }
        for edge in self.connections:
            source = ports.get((edge.source_block_id, edge.source_port_id))
            target = ports.get((edge.target_block_id, edge.target_port_id))
            if source is None or target is None:
                raise ValueError("control connection references a missing port")
            if source.direction != "output" or target.direction != "input":
                raise ValueError("control connections require output-to-input direction")
            if source.signal_type != target.signal_type or source.unit != target.unit:
                raise ValueError("control connection signal type or unit mismatch")


PluginCapability = Literal[
    "unit-model",
    "numerical-adapter",
    "study",
    "import-export",
    "command",
    "data-panel",
    "visual-layer",
    "domain-package",
]
PluginPermission = Literal["case-read", "artifact-read", "artifact-write", "filesystem", "network"]
PluginExecutionMode = Literal["isolated-stable", "trusted-in-process", "developer-unsupported"]


@dataclass(frozen=True)
class PluginManifest(_ImmutableBoundary):
    """Static, versioned extension declaration; loading remains an explicit policy action."""

    plugin_id: str
    name: str
    version: str
    api_version: str
    language: Literal["python", "cpp"]
    execution_mode: PluginExecutionMode
    capabilities: tuple[PluginCapability, ...]
    permissions: tuple[PluginPermission, ...] = ()
    platforms: tuple[str, ...] = ()
    architectures: tuple[str, ...] = ()
    licence: str = ""
    provenance: str = ""
    artifact_sha256: str = ""
    entry_point: str = ""
    schema_version: Literal["bh-plugin-manifest-v1"] = "bh-plugin-manifest-v1"

    def __post_init__(self) -> None:
        super().__post_init__()
        if not all(
            (self.plugin_id.strip(), self.name.strip(), self.version.strip(), self.api_version)
        ):
            raise ValueError("plugin identity, name, version and API version are required")
        if len(set(self.capabilities)) != len(self.capabilities):
            raise ValueError("plugin capabilities must be unique")
        if len(set(self.permissions)) != len(self.permissions):
            raise ValueError("plugin permissions must be unique")
        if len(self.artifact_sha256) != 64:
            raise ValueError("plugin artifact hash must be SHA-256")
        int(self.artifact_sha256, 16)


@dataclass(frozen=True)
class PluginExecutionRecord(_ImmutableBoundary):
    """Attributable extension outcome; custom numerical results remain unverified."""

    plugin_id: str
    plugin_version: str
    execution_mode: PluginExecutionMode
    input_hashes: tuple[str, ...]
    permissions: tuple[PluginPermission, ...]
    disposition: Literal["COMPLETED", "REJECTED", "FAILED"]
    output_hashes: tuple[str, ...] = ()
    scientific_status: Literal["UNVERIFIED_EXTENSION"] = "UNVERIFIED_EXTENSION"
    diagnostic: str = ""
    schema_version: Literal["bh-plugin-execution-record-v1"] = "bh-plugin-execution-record-v1"

    def __post_init__(self) -> None:
        super().__post_init__()
        for value in (*self.input_hashes, *self.output_hashes):
            if len(value) != 64:
                raise ValueError("plugin input and output references must be SHA-256")
            int(value, 16)


@dataclass(frozen=True)
class AddEquipmentEdit(_ImmutableBoundary):
    """Create one catalogue unit with required inputs unset."""

    model_id: str
    position: CanvasPointDto


@dataclass(frozen=True)
class ConnectPortsEdit(_ImmutableBoundary):
    """Propose an explicit output-to-input connection."""

    source_id: str
    source_port: str
    target_id: str
    target_port: str


@dataclass(frozen=True)
class RemoveObjectsEdit(_ImmutableBoundary):
    """Remove selected objects; connected equipment requires confirmation."""

    object_ids: tuple[str, ...]
    confirmed_connected: bool = False


@dataclass(frozen=True)
class MoveObjectsEdit(_ImmutableBoundary):
    """Change selected presentation coordinates only."""

    positions: tuple[tuple[str, CanvasPointDto], ...]


@dataclass(frozen=True)
class ConfigureInputEdit(_ImmutableBoundary):
    """Submit original scalar notation and unit; blank removes the input."""

    object_id: str
    name: str
    text: str
    unit: str


@dataclass(frozen=True)
class DisplayUnitEdit(_ImmutableBoundary):
    """Set or clear a presentation unit override without editing the input."""

    object_id: str
    name: str
    unit: str | None


@dataclass(frozen=True)
class RenameObjectEdit(_ImmutableBoundary):
    """Rename a visible tag, optionally swapping and updating linked branch tags."""

    object_id: str
    tag: str
    swap: bool = False
    rename_family: bool = True


@dataclass(frozen=True)
class RouteStreamEdit(_ImmutableBoundary):
    """Set orthogonal presentation points; empty resets automatic routing."""

    object_id: str
    points: tuple[CanvasPointDto, ...]


@dataclass(frozen=True)
class SplitStreamEdit(_ImmutableBoundary):
    """Insert a visible explicit splitter and an additional branch connection."""

    stream_id: str
    position: CanvasPointDto
    target_id: str
    target_port: str


@dataclass(frozen=True)
class PasteEquipmentEdit(_ImmutableBoundary):
    """Copy selected units with new identities and optional internal connections."""

    source: PfdDocumentDto
    object_ids: tuple[str, ...]
    offset: CanvasPointDto = CanvasPointDto(40.0, 40.0)
    connections: bool = False
    reset_inputs: bool = False


@dataclass(frozen=True)
class DetailsEdit(_ImmutableBoundary):
    """Set expanded and pinned presentation detail state."""

    object_id: str
    expanded: bool
    pinned: bool


@dataclass(frozen=True)
class SettingsEdit(_ImmutableBoundary):
    """Replace case preferences without reconfiguring existing stream identities."""

    settings: PfdSettingsDto


@dataclass(frozen=True)
class ViewportEdit(_ImmutableBoundary):
    """Change only the visible centre and scale."""

    centre: CanvasPointDto
    scale: float


@dataclass(frozen=True)
class UpsertVisualStreamGroupEdit(_ImmutableBoundary):
    """Create or replace one presentation-only visual stream group."""

    group: VisualStreamGroup


@dataclass(frozen=True)
class RemoveVisualStreamGroupEdit(_ImmutableBoundary):
    """Remove one visual group without changing streams or engineering selection."""

    group_id: str


@dataclass(frozen=True)
class SetPfdLayerPreferencesEdit(_ImmutableBoundary):
    """Replace presentation-only layer and animation preferences."""

    preferences: PfdLayerPreferences


@dataclass(frozen=True)
class UpsertEngineeringSubsystemEdit(_ImmutableBoundary):
    """Create or replace a versioned engineering subsystem."""

    subsystem: EngineeringSubsystem


@dataclass(frozen=True)
class RemoveEngineeringSubsystemEdit(_ImmutableBoundary):
    """Remove an engineering subsystem while retaining its member objects."""

    subsystem_id: str


PfdEdit = (
    AddEquipmentEdit
    | ConnectPortsEdit
    | RemoveObjectsEdit
    | MoveObjectsEdit
    | ConfigureInputEdit
    | DisplayUnitEdit
    | RenameObjectEdit
    | RouteStreamEdit
    | SplitStreamEdit
    | PasteEquipmentEdit
    | DetailsEdit
    | SettingsEdit
    | ViewportEdit
    | UpsertVisualStreamGroupEdit
    | RemoveVisualStreamGroupEdit
    | SetPfdLayerPreferencesEdit
    | UpsertEngineeringSubsystemEdit
    | RemoveEngineeringSubsystemEdit
)


@dataclass(frozen=True)
class PfdEditParameters(_ImmutableBoundary):
    """One immutable document and one atomic editing intention."""

    document: PfdDocumentDto
    edit: PfdEdit


@dataclass(frozen=True)
class PfdDocumentParameters(_ImmutableBoundary):
    """Explicit native save or history restoration snapshot."""

    document: PfdDocumentDto


@dataclass(frozen=True)
class QuantityDisplayParameters(_ImmutableBoundary):
    """Request a compatible conversion for formatting, never a solver result."""

    quantity: QuantityDto
    target_unit: str


@dataclass(frozen=True)
class HistoryBranchReference(_ImmutableBoundary):
    """Named editing path; its origin is retained when alternatives are created."""

    branch_id: str
    name: str
    origin_entry_id: str | None


@dataclass(frozen=True)
class SavedVersionReference(_ImmutableBoundary):
    """Explicit native save, independently addressed from continuous recovery."""

    entry_id: str
    revision: int
    document_hash: str
    created_at: str


@dataclass(frozen=True)
class ResultArtifactReference(_ImmutableBoundary):
    """Immutable result link only; no calculated values are copied into history."""

    artifact_id: str
    content_hash: str


@dataclass(frozen=True)
class NamedSnapshot(_ImmutableBoundary):
    """Restorable checkpoint of the shared PFD and optional selected result links."""

    snapshot_id: str
    name: str
    entry_id: str
    document_hash: str
    results: tuple[ResultArtifactReference, ...] = ()


@dataclass(frozen=True)
class HistoryEntry(_ImmutableBoundary):
    """Durable logical edit and stack state, with checkpoints instead of executable replay.

    parent_entry_id orders committed events; branch.origin_entry_id records the
    alternative's source. operation_json is audit data and is never dispatched.
    """

    entry_id: str
    sequence: int
    parent_entry_id: str | None
    actor_id: str
    request_id: str
    created_at: str
    branch: HistoryBranchReference
    kind: Literal["start", "edit", "undo", "redo", "save", "snapshot", "branch"]
    label: str
    classification: Literal["engineering", "presentation", "metadata"]
    affected_ids: tuple[str, ...]
    before_hash: str
    after_hash: str
    before_engineering_hash: str
    after_engineering_hash: str
    operation_json: str
    reverses_entry_id: str | None
    undo_ids: tuple[str, ...]
    redo_ids: tuple[str, ...]
    saved_version: SavedVersionReference | None
    snapshot: NamedSnapshot | None
    schema_version: Literal["bh-history-entry-v1"] = "bh-history-entry-v1"


@dataclass(frozen=True)
class HistoryState(_ImmutableBoundary):
    """Current committed working state and immutable, attributable history."""

    document: PfdDocumentDto
    entries: tuple[HistoryEntry, ...]
    dirty: bool
    schema_version: Literal["bh-history-state-v1"] = "bh-history-state-v1"


@dataclass(frozen=True)
class HistoryTarget(_ImmutableBoundary):
    """Optimistic head precondition; an entry may also identify a historical view."""

    draft_id: str
    expected_head: str = ""
    entry_id: str = ""
    name: str = ""


@dataclass(frozen=True)
class HistoryEditParameters(_ImmutableBoundary):
    """One existing typed PFD edit against an exact durable history head."""

    target: HistoryTarget
    edit: PfdEdit


@dataclass(frozen=True)
class HistoryDifference(_ImmutableBoundary):
    """Structural before/after values; strings are display data, never code."""

    category: Literal["engineering", "presentation"]
    object_id: str
    field: str
    before: str
    after: str


@dataclass(frozen=True)
class HistoryComparison(_ImmutableBoundary):
    """Two exact history checkpoints and their structural differences."""

    before_entry_id: str
    after_entry_id: str
    differences: tuple[HistoryDifference, ...]


@dataclass(frozen=True)
class CompareHistoryParameters(_ImmutableBoundary):
    """Compare any two checkpoints, including separate cases."""

    before: HistoryTarget
    after: HistoryTarget


# ---------------------------------------------------------------------------
# DW4 Worker Protocol and IPC Framing Contracts
# ---------------------------------------------------------------------------

WORKER_PROTOCOL_VERSION = "2026-09-15.dw4alpha"


@dataclass(frozen=True)
class WorkerHello(_ImmutableBoundary):
    """Initial greeting and capability advertisement sent by the solver worker."""

    supported_protocols: tuple[str, ...]
    worker_session_id: str
    worker_pid: int
    capabilities: tuple[str, ...]
    solver_version: str
    protocol_version: str = WORKER_PROTOCOL_VERSION


@dataclass(frozen=True)
class WorkerReady(_ImmutableBoundary):
    """Supervisor handshake acknowledgment confirming accepted protocol version."""

    selected_protocol: str
    worker_session_id: str
    accepted: bool
    message: str = ""
    protocol_version: str = WORKER_PROTOCOL_VERSION


@dataclass(frozen=True)
class WorkerValidateRequest(_ImmutableBoundary):
    """Validation request dispatched from supervisor to the worker."""

    request_id: str
    draft: DraftDto
    expected_engineering_hash: str
    expected_context_hash: str
    protocol_version: str = WORKER_PROTOCOL_VERSION


@dataclass(frozen=True)
class WorkerValidateResponse(_ImmutableBoundary):
    """Validation response from worker reporting DOF and diagnostics."""

    request_id: str
    valid: bool
    dof: int
    engineering_hash: str
    context_hash: str
    diagnostics: tuple[DiagnosticDto, ...] = ()
    protocol_version: str = WORKER_PROTOCOL_VERSION


@dataclass(frozen=True)
class RunJob(_ImmutableBoundary):
    """Pre-run admission job carrying preallocated run ID and sealed inputs."""

    job_id: str
    run_id: str
    case_id: str
    revision_id: int
    engineering_hash: str
    context_hash: str
    draft: DraftDto
    max_iterations: int = 100
    tolerance: float = 1e-6
    timeout_seconds: float = 120.0
    protocol_version: str = WORKER_PROTOCOL_VERSION


@dataclass(frozen=True)
class RunAccepted(_ImmutableBoundary):
    """Acknowledgment that the worker has admitted the exact preallocated job."""

    job_id: str
    run_id: str
    worker_session_id: str
    admitted_at: str
    protocol_version: str = WORKER_PROTOCOL_VERSION


@dataclass(frozen=True)
class WorkerProgressEvent(_ImmutableBoundary):
    """Periodic numerical solver telemetry during execution."""

    run_id: str
    worker_session_id: str
    sequence: int
    timestamp: str
    iteration: int
    residual_norm: float | None = None
    message: str = ""
    protocol_version: str = WORKER_PROTOCOL_VERSION


@dataclass(frozen=True)
class WorkerDiagnosticEvent(_ImmutableBoundary):
    """Sanitized diagnostic notice emitted during worker execution."""

    run_id: str
    worker_session_id: str
    sequence: int
    timestamp: str
    level: Literal["INFO", "WARNING", "ERROR"]
    code: str
    message: str
    unit_id: str | None = None
    port_name: str | None = None
    protocol_version: str = WORKER_PROTOCOL_VERSION


@dataclass(frozen=True)
class WorkerCompletedEvent(_ImmutableBoundary):
    """Terminal successful completion event carrying staged artifact reference."""

    run_id: str
    worker_session_id: str
    sequence: int
    timestamp: str
    artifact_hash: str
    staged_path: str
    convergence: Literal["converged", "unconverged", "failed", "unknown"]
    closure: Literal["passed", "failed", "unknown"]
    physical_validity: Literal["valid", "invalid", "unknown"]
    correlation_validity: Literal["valid", "extrapolated", "invalid", "unknown"]
    execution_duration_ms: float
    manifest: tuple[tuple[str, str], ...] = ()
    protocol_version: str = WORKER_PROTOCOL_VERSION


@dataclass(frozen=True)
class WorkerFailedEvent(_ImmutableBoundary):
    """Terminal failure event reporting numerical or execution failure."""

    run_id: str
    worker_session_id: str
    sequence: int
    timestamp: str
    reason: str
    diagnostics: tuple[DiagnosticDto, ...] = ()
    protocol_version: str = WORKER_PROTOCOL_VERSION


@dataclass(frozen=True)
class WorkerCancelledEvent(_ImmutableBoundary):
    """Terminal cancellation acknowledgment verifying safe boundary reached."""

    run_id: str
    worker_session_id: str
    sequence: int
    timestamp: str
    safe_boundary_reached: bool
    partial_artifact_hash: str | None = None
    protocol_version: str = WORKER_PROTOCOL_VERSION


@dataclass(frozen=True)
class WorkerFault(_ImmutableBoundary):
    """Sanitized error notification for internal worker faults."""

    worker_session_id: str
    run_id: str | None
    fault_code: str
    fault_message: str
    timestamp: str
    protocol_version: str = WORKER_PROTOCOL_VERSION


@dataclass(frozen=True)
class CancelRunRequest(_ImmutableBoundary):
    """Cooperative cancellation request sent to the worker."""

    run_id: str
    reason: str = "User cancelled"
    force_terminate: bool = False
    protocol_version: str = WORKER_PROTOCOL_VERSION


@dataclass(frozen=True)
class WorkerShutdownRequest(_ImmutableBoundary):
    """Clean termination request for supervisor shutdown."""

    reason: str = "Normal shutdown"
    protocol_version: str = WORKER_PROTOCOL_VERSION


AttemptLifecycleState = Literal[
    "ADMITTED", "RUNNING", "COMPLETED", "FAILED", "CANCELLED", "INTERRUPTED", "TIMED_OUT"
]


@dataclass(frozen=True)
class RunAttemptRecord(_ImmutableBoundary):
    """Operational lifecycle record independent of scientific convergence statuses."""

    attempt_id: str
    run_id: str
    case_id: str
    engineering_hash: str
    context_hash: str
    state: AttemptLifecycleState
    admitted_at: str
    terminal_at: str | None = None
    failure_reason: str | None = None
    artifact_hash: str | None = None
    persisted: bool = False
    protocol_version: str = WORKER_PROTOCOL_VERSION


# ---------------------------------------------------------------------------
# DW5 Result Inspection, Workbooks, Overlays and Graph Contracts
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StreamPropertyDto(_ImmutableBoundary):
    """Auxiliary thermodynamic or transport property on a material stream."""

    name: str
    value: float
    unit: str


@dataclass(frozen=True)
class StreamResultRowDto(_ImmutableBoundary):
    """Complete workbook row for a flowsheet stream connection."""

    stream_id: str
    tag: str
    from_unit_id: str | None
    from_port: str | None
    to_unit_id: str | None
    to_port: str | None
    fluid: str | None
    mass_flow_kg_s: float | None
    temperature_k: float | None
    pressure_pa: float | None
    enthalpy_j_kg: float | None
    vapor_fraction: float | None
    properties: tuple[StreamPropertyDto, ...] = ()


@dataclass(frozen=True)
class EquipmentResultRowDto(_ImmutableBoundary):
    """Complete workbook row for an equipment unit operation."""

    unit_id: str
    label: str
    model_id: str
    duty_w: float | None
    delta_p_pa: float | None
    convergence: str
    closure: str
    physical_validity: str
    correlation_validity: str
    diagnostics: tuple[DiagnosticDto, ...] = ()
    properties: tuple[StreamPropertyDto, ...] = ()


@dataclass(frozen=True)
class ProcessBalanceDto(_ImmutableBoundary):
    """Material or energy balance record with explicit closure criteria."""

    balance_type: str
    inlet_total: float
    outlet_total: float
    generation_or_duty: float
    residual: float
    tolerance: float
    status: str
    units: str


@dataclass(frozen=True)
class ResultSelectionDto(_ImmutableBoundary):
    """Identities and status for active displayed run vs latest valid run."""

    case_id: str
    active_run_id: str | None
    latest_run_id: str | None
    latest_valid_run_id: str | None
    is_stale: bool
    convergence: str | None = None
    closure: str | None = None
    physical_validity: str | None = None
    correlation_validity: str | None = None


@dataclass(frozen=True)
class WorkbookDto(_ImmutableBoundary):
    """Authoritative workbook view of streams, equipment, and balances."""

    case_id: str
    run_id: str
    flowsheet_id: str
    convergence: str
    closure: str
    physical_validity: str
    correlation_validity: str
    streams: tuple[StreamResultRowDto, ...]
    equipment: tuple[EquipmentResultRowDto, ...]
    balances: tuple[ProcessBalanceDto, ...]
    diagnostics: tuple[DiagnosticDto, ...] = ()
    selection: ResultSelectionDto | None = None


@dataclass(frozen=True)
class StreamResultOverlayDto(_ImmutableBoundary):
    """Calculated stream state badge displayed on PFD stream lines."""

    stream_id: str
    tag: str
    temperature_k: float | None
    pressure_pa: float | None
    mass_flow_kg_s: float | None
    vapor_fraction: float | None
    is_valid: bool = True


@dataclass(frozen=True)
class EquipmentResultOverlayDto(_ImmutableBoundary):
    """Calculated equipment status badge displayed on PFD symbols."""

    unit_id: str
    convergence: str
    closure: str
    physical_validity: str
    correlation_validity: str
    duty_w: float | None
    delta_p_pa: float | None


@dataclass(frozen=True)
class OverlaysDto(_ImmutableBoundary):
    """Attributable canvas overlays for streams and equipment."""

    case_id: str
    run_id: str | None
    streams: tuple[StreamResultOverlayDto, ...]
    equipment: tuple[EquipmentResultOverlayDto, ...]
    selection: ResultSelectionDto


@dataclass(frozen=True)
class SeriesDataPointDto(_ImmutableBoundary):
    """Single point in a 2D plot series."""

    x: float
    y: float
    point_label: str | None = None


@dataclass(frozen=True)
class SeriesDescriptorDto(_ImmutableBoundary):
    """Plottable 2D series with explicit physical units and visual styling."""

    series_id: str
    label: str
    unit_x: str
    unit_y: str
    line_style: Literal["solid", "dashed", "dotted", "scatter"] = "solid"
    color_hex: str = "#2b6cb0"
    points: tuple[SeriesDataPointDto, ...] = ()


@dataclass(frozen=True)
class PlotDefinitionDto(_ImmutableBoundary):
    """2D plot definition carrying engineering provenance, axes, and series."""

    plot_id: str
    title: str
    x_label: str
    y_label: str
    plot_kind: Literal["T_Q", "RESIDUAL_CONVERGENCE", "PARAMETRIC", "PROFILE"]
    series: tuple[SeriesDescriptorDto, ...]
    run_id: str | None = None
    unit_id: str | None = None
    provenance_hash: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class ExportProvenanceDto(_ImmutableBoundary):
    """Provenance record embedded in CSV and SVG graph exports."""

    run_id: str
    engineering_hash: str
    context_hash: str
    timestamp: str
    software_version: str = COMMAND_VERSION


@dataclass(frozen=True)
class InspectWorkbookParameters(_ImmutableBoundary):
    """Request for flowsheet workbook tables for a case and run."""

    case_id: str
    run_id: str | None = None


@dataclass(frozen=True)
class SelectDisplayRunParameters(_ImmutableBoundary):
    """Select which run to display on canvas and workbook."""

    case_id: str
    run_id: str | None = None


@dataclass(frozen=True)
class GetOverlaysParameters(_ImmutableBoundary):
    """Request attributable canvas overlays for streams and equipment."""

    case_id: str
    run_id: str | None = None


@dataclass(frozen=True)
class PlotDataParameters(_ImmutableBoundary):
    """Request plottable 2D series for whole-process or individual unit views."""

    case_id: str
    run_id: str | None = None
    plot_kind: Literal["T_Q", "RESIDUAL_CONVERGENCE", "PARAMETRIC", "PROFILE"] = "T_Q"
    unit_id: str | None = None


# ---------------------------------------------------------------------------
# Command Registry and Dispatch Contracts
# ---------------------------------------------------------------------------

CommandParameters = (
    CreateDraftParameters
    | ListDraftsParameters
    | DraftParameters
    | OpenDraftParameters
    | StartRunParameters
    | InspectRunParameters
    | LastValidParameters
    | CompareRunsParameters
    | DemonstrationParameters
    | PfdEditParameters
    | PfdDocumentParameters
    | QuantityDisplayParameters
    | HistoryTarget
    | HistoryEditParameters
    | CompareHistoryParameters
    | CancelRunParameters
    | InspectAttemptParameters
    | ListAttemptsParameters
    | InspectWorkbookParameters
    | SelectDisplayRunParameters
    | GetOverlaysParameters
    | PlotDataParameters
)


@dataclass(frozen=True)
class CommandRequest(_ImmutableBoundary):
    """Attributable synchronous command; request IDs do not promise durable dedup."""

    command_name: str
    request_id: str
    actor_id: str
    parameters: CommandParameters
    profile: Literal["REVIEW", "EXPLORATION", "NARRATIVE"] = "REVIEW"
    schema_version: str = COMMAND_VERSION


CommandData = (
    DraftDto
    | DraftListDto
    | ValidationReceiptDto
    | RunViewDto
    | RunComparisonDto
    | DemonstrationReportDto
    | PfdDocumentDto
    | PfdCatalogueDto
    | QuantityDto
    | HistoryState
    | HistoryComparison
    | RunAttemptRecord
    | tuple[RunAttemptRecord, ...]
    | WorkbookDto
    | OverlaysDto
    | ResultSelectionDto
    | PlotDefinitionDto
    | None
)


@dataclass(frozen=True)
class CommandEvent(_ImmutableBoundary):
    """Synchronous command terminal event; not a solver-worker progress event."""

    request_id: str
    command_name: str
    disposition: Literal["COMPLETED", "REJECTED"]
    schema_version: str = COMMAND_VERSION


@dataclass(frozen=True)
class CommandOutcome(_ImmutableBoundary):
    """Typed result whose disposition is independent of scientific validity."""

    request_id: str
    disposition: Literal["COMPLETED", "REJECTED"]
    data: CommandData = None
    diagnostics: tuple[DiagnosticDto, ...] = ()
    events: tuple[CommandEvent, ...] = ()
    schema_version: str = COMMAND_VERSION
