"""DW1 command contracts, independent of HTTP, scientific and desktop libraries.

Quantities carry submitted units; these types never convert engineering values.
Presentation extension strings are JSON, not executable or runtime objects.
Commands are synchronous in DW1: completion is not worker lifecycle admission.
"""

from __future__ import annotations

import json
import math
import types
from dataclasses import dataclass, fields, is_dataclass
from typing import Literal, cast, get_args, get_origin, get_type_hints

COMMAND_VERSION = "bh-command-v1alpha"
ENGINEERING_HASH_SCHEME = "bh-engineering-v1alpha"


def _check_value(value: object, hint: object) -> None:
    """Reject mutable, non-finite and structurally mistyped nested boundary values."""
    origin = get_origin(hint)
    arguments = get_args(hint)
    if origin is types.UnionType:
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
        hints = get_type_hints(hint)
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
