"""Immutable v1alpha domain and numerical contracts."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable

from .ids import StableId
from .quantity import Quantity
from .status import ClosureStatus, ConvergenceStatus, ValidityStatus

SCHEMA_VERSION = "v1alpha"


def _require_fraction(value: float, name: str) -> None:
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be a finite fraction from 0 to 1")


def _validate_composition(components: tuple[CompositionComponent, ...]) -> None:
    if not components:
        raise ValueError("composition must contain at least one component")
    identifiers = [component.material_id for component in components]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("composition contains duplicate material IDs")
    total = sum(component.fraction for component in components)
    if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1.0e-9):
        raise ValueError(f"composition fractions must sum to one, received {total}")


class AiProfile(StrEnum):
    REVIEW = "review"
    EXPLORATION = "exploration"
    NARRATIVE = "narrative"


class ChangeSetStatus(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    APPLIED = "applied"
    REJECTED = "rejected"


class PortDirection(StrEnum):
    INPUT = "input"
    OUTPUT = "output"


class FlashVariable(StrEnum):
    TEMPERATURE = "temperature"
    PRESSURE = "pressure"
    SPECIFIC_ENTHALPY = "specific_enthalpy"
    VAPOUR_FRACTION = "vapour_fraction"


@dataclass(frozen=True)
class CompositionComponent:
    material_id: StableId
    fraction: float

    def __post_init__(self) -> None:
        _require_fraction(self.fraction, "composition fraction")


@dataclass(frozen=True)
class PropertyPackageReference:
    package_id: StableId
    implementation: str
    version: str
    configuration_id: str | None = None

    def __post_init__(self) -> None:
        if not self.implementation or not self.version:
            raise ValueError("property-package implementation and version are required")


@dataclass(frozen=True)
class MaterialReference:
    material_id: StableId
    name: str
    property_package_id: StableId
    evidence_reference: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("material name cannot be blank")


@dataclass(frozen=True)
class MaterialPort:
    port_id: StableId
    name: str
    direction: PortDirection
    required: bool = True


@dataclass(frozen=True)
class EnergyPort:
    port_id: StableId
    name: str
    direction: PortDirection
    required: bool = True


Port = MaterialPort | EnergyPort


def ports_are_compatible(source: Port, target: Port) -> bool:
    """Return whether two ports can form a directed connection."""

    return (
        source.direction is PortDirection.OUTPUT
        and target.direction is PortDirection.INPUT
        and type(source) is type(target)
    )


@dataclass(frozen=True)
class StateSpecification:
    variable: FlashVariable
    value: Quantity

    def __post_init__(self) -> None:
        dimensions = {
            FlashVariable.TEMPERATURE: "temperature",
            FlashVariable.PRESSURE: "pressure",
            FlashVariable.SPECIFIC_ENTHALPY: "specific_energy",
            FlashVariable.VAPOUR_FRACTION: "dimensionless",
        }
        self.value.require_dimension(dimensions[self.variable])
        if self.variable is FlashVariable.VAPOUR_FRACTION:
            _require_fraction(self.value.to("1").value, "vapour fraction")


@dataclass(frozen=True)
class FlashRequest:
    property_package_id: StableId
    composition: tuple[CompositionComponent, ...]
    specifications: tuple[StateSpecification, StateSpecification]

    def __post_init__(self) -> None:
        _validate_composition(self.composition)
        if self.specifications[0].variable is self.specifications[1].variable:
            raise ValueError("flash request requires two independent state variables")


@dataclass(frozen=True)
class PhaseState:
    phase: str
    fraction: float
    temperature: Quantity
    pressure: Quantity
    density: Quantity
    specific_enthalpy: Quantity
    heat_capacity: Quantity | None = None

    def __post_init__(self) -> None:
        if not self.phase.strip():
            raise ValueError("phase name cannot be blank")
        _require_fraction(self.fraction, "phase fraction")
        self.temperature.require_dimension("temperature")
        self.pressure.require_dimension("pressure")
        self.density.require_dimension("density")
        self.specific_enthalpy.require_dimension("specific_energy")
        if self.heat_capacity is not None:
            self.heat_capacity.require_dimension("specific_heat")


@dataclass(frozen=True)
class ProvenanceRecord:
    source: str
    model: str
    version: str
    evidence_reference: str | None = None


@dataclass(frozen=True)
class ThermoState:
    property_package_id: StableId
    composition: tuple[CompositionComponent, ...]
    temperature: Quantity
    pressure: Quantity
    specific_enthalpy: Quantity
    phases: tuple[PhaseState, ...]
    validity: ValidityStatus
    provenance: tuple[ProvenanceRecord, ...]
    messages: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_composition(self.composition)
        self.temperature.require_dimension("temperature")
        self.pressure.require_dimension("pressure")
        self.specific_enthalpy.require_dimension("specific_energy")
        if not self.phases:
            raise ValueError("thermodynamic state must contain at least one phase")
        phase_total = sum(phase.fraction for phase in self.phases)
        if not math.isclose(phase_total, 1.0, rel_tol=0.0, abs_tol=1.0e-9):
            raise ValueError("phase fractions must sum to one")


@runtime_checkable
class PropertyPackage(Protocol):
    """Replaceable thermophysical backend boundary."""

    @property
    def package_id(self) -> StableId: ...

    def flash(self, request: FlashRequest) -> ThermoState: ...


@dataclass(frozen=True)
class MaterialState:
    material_reference_id: StableId
    composition: tuple[CompositionComponent, ...]
    mass_flow: Quantity
    thermo: ThermoState

    def __post_init__(self) -> None:
        _validate_composition(self.composition)
        self.mass_flow.require_dimension("mass_flow")


@dataclass(frozen=True)
class MaterialPortValue:
    port_id: StableId
    state: MaterialState


@dataclass(frozen=True)
class EnergyPortValue:
    port_id: StableId
    duty: Quantity

    def __post_init__(self) -> None:
        self.duty.require_dimension("power")


NamedPortValue = MaterialPortValue | EnergyPortValue


@dataclass(frozen=True)
class Residual:
    name: str
    value: float
    scale: float = 1.0
    unit: str = "1"

    def __post_init__(self) -> None:
        if not math.isfinite(self.value):
            raise ValueError("residual must be finite")
        if not math.isfinite(self.scale) or self.scale <= 0.0:
            raise ValueError("residual scale must be finite and positive")


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    severity: str = "information"
    subject_id: StableId | None = None


@dataclass(frozen=True)
class ModelEvent:
    code: str
    message: str
    timestamp_s: float | None = None


@dataclass(frozen=True)
class AuditEvidence:
    name: str
    equation: str
    inputs: tuple[tuple[str, Quantity], ...] = ()
    outputs: tuple[tuple[str, Quantity], ...] = ()
    assumptions: tuple[str, ...] = ()
    evidence_reference: str | None = None


@dataclass(frozen=True)
class UnitEvaluationRequest:
    unit_id: StableId
    input_port_values: tuple[NamedPortValue, ...]
    parameters: tuple[tuple[str, Quantity], ...]


@dataclass(frozen=True)
class UnitEvaluation:
    unit_id: StableId
    output_port_values: tuple[NamedPortValue, ...]
    residuals: tuple[Residual, ...]
    diagnostics: tuple[Diagnostic, ...]
    events: tuple[ModelEvent, ...]
    validity: ValidityStatus
    audit_evidence: tuple[AuditEvidence, ...]
    metrics: tuple[tuple[str, Quantity], ...] = ()


@runtime_checkable
class UnitOperation(Protocol):
    """Boundary implemented independently by every equipment model."""

    @property
    def model_id(self) -> str: ...

    @property
    def ports(self) -> tuple[Port, ...]: ...

    def evaluate(self, request: UnitEvaluationRequest) -> UnitEvaluation: ...


@dataclass(frozen=True)
class ResidualVariable:
    name: str
    initial_value: float
    scale: float
    lower_bound: float | None = None
    upper_bound: float | None = None

    def __post_init__(self) -> None:
        if self.scale <= 0.0 or not math.isfinite(self.scale):
            raise ValueError("variable scale must be finite and positive")
        if (
            self.lower_bound is not None
            and self.upper_bound is not None
            and self.lower_bound > self.upper_bound
        ):
            raise ValueError("lower bound cannot exceed upper bound")


@runtime_checkable
class ResidualProblem(Protocol):
    @property
    def variables(self) -> tuple[ResidualVariable, ...]: ...

    def evaluate(self, values: tuple[float, ...]) -> tuple[Residual, ...]: ...


@dataclass(frozen=True)
class SolverIteration:
    iteration: int
    residual_norm: float


@dataclass(frozen=True)
class SolverResult:
    status: ConvergenceStatus
    values: tuple[tuple[str, float], ...]
    iterations: tuple[SolverIteration, ...]
    final_residuals: tuple[Residual, ...]
    message: str


@runtime_checkable
class SteadySolver(Protocol):
    @property
    def solver_id(self) -> str: ...

    def solve(self, problem: ResidualProblem) -> SolverResult: ...


@dataclass(frozen=True)
class UnitDefinition:
    unit_id: StableId
    model_id: str
    name: str
    parameters: tuple[tuple[str, Quantity], ...] = ()
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.model_id.strip() or not self.name.strip():
            raise ValueError("unit model ID and name cannot be blank")
        parameter_names = [name for name, _ in self.parameters]
        metadata_names = [name for name, _ in self.metadata]
        if len(parameter_names) != len(set(parameter_names)):
            raise ValueError("unit parameters must have unique names")
        if len(metadata_names) != len(set(metadata_names)):
            raise ValueError("unit metadata must have unique names")


@dataclass(frozen=True)
class ConnectionDefinition:
    connection_id: StableId
    source_unit_id: StableId
    source_port_id: StableId
    target_unit_id: StableId
    target_port_id: StableId


@dataclass(frozen=True)
class Specification:
    specification_id: StableId
    target_unit_id: StableId
    parameter: str
    value: Quantity


@dataclass(frozen=True)
class CaseDefinition:
    case_id: StableId
    title: str
    materials: tuple[MaterialReference, ...]
    property_packages: tuple[PropertyPackageReference, ...]
    units: tuple[UnitDefinition, ...]
    connections: tuple[ConnectionDefinition, ...]
    specifications: tuple[Specification, ...]
    ai_profile: AiProfile = AiProfile.REVIEW
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(f"unsupported schema version: {self.schema_version}")
        if not self.title.strip():
            raise ValueError("case title cannot be blank")
        for values, name in (
            (self.materials, "material"),
            (self.property_packages, "property package"),
            (self.units, "unit"),
            (self.connections, "connection"),
            (self.specifications, "specification"),
        ):
            identifiers = [next(iter(value.__dict__.values())) for value in values]
            if len(identifiers) != len(set(identifiers)):
                raise ValueError(f"duplicate {name} ID")


@dataclass(frozen=True)
class ChangeRecord:
    operation: str
    target_id: StableId
    field_name: str | None = None
    prior_value: str | None = None
    new_value: str | None = None
    rationale: str | None = None


@dataclass(frozen=True)
class ExplorationLimits:
    maximum_iterations: int
    maximum_runs: int
    maximum_elapsed_seconds: float

    def __post_init__(self) -> None:
        if self.maximum_iterations < 1 or self.maximum_runs < 1:
            raise ValueError("exploration iteration and run limits must be positive")
        if not math.isfinite(self.maximum_elapsed_seconds) or self.maximum_elapsed_seconds <= 0:
            raise ValueError("exploration elapsed-time limit must be finite and positive")


@dataclass(frozen=True)
class ChangeSet:
    change_set_id: StableId
    profile: AiProfile
    base_revision_id: StableId
    proposed_revision: DraftRevision
    changes: tuple[ChangeRecord, ...]
    engineering_rationale: str
    status: ChangeSetStatus = ChangeSetStatus.PROPOSED
    exploration_limits: ExplorationLimits | None = None

    def __post_init__(self) -> None:
        if self.proposed_revision.revision_id == self.base_revision_id:
            raise ValueError("a change set must propose a new draft revision")
        if not self.engineering_rationale.strip():
            raise ValueError("a concise engineering rationale is required")
        if self.profile is AiProfile.EXPLORATION and self.exploration_limits is None:
            raise ValueError("exploration change sets require explicit limits")


@dataclass(frozen=True)
class DraftRevision:
    revision_id: StableId
    base_case_id: StableId
    revision_number: int
    case: CaseDefinition
    changes: tuple[ChangeRecord, ...]
    created_at: str

    def __post_init__(self) -> None:
        if self.revision_number < 1:
            raise ValueError("draft revision number must be positive")
        if self.case.case_id != self.base_case_id:
            raise ValueError("draft case ID must match its base case ID")


@dataclass(frozen=True)
class VariableDefinition:
    name: str
    owner_id: StableId
    dimension: str
    scale: float
    specified: bool


@dataclass(frozen=True)
class CompiledFlowsheet:
    compiled_id: StableId
    source_case_id: StableId
    source_revision_id: StableId | None
    source_hash: str
    execution_order: tuple[StableId, ...]
    variables: tuple[VariableDefinition, ...]
    degrees_of_freedom: int
    recycle_groups: tuple[tuple[StableId, ...], ...]
    diagnostics: tuple[Diagnostic, ...] = ()
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(f"unsupported schema version: {self.schema_version}")
        if self.degrees_of_freedom < 0:
            raise ValueError("degrees of freedom cannot be negative")


@dataclass(frozen=True)
class BalanceRecord:
    name: str
    residual: Quantity
    tolerance: Quantity
    status: ClosureStatus

    def __post_init__(self) -> None:
        if self.residual.dimension != self.tolerance.dimension:
            raise ValueError("balance residual and tolerance must share a dimension")


@dataclass(frozen=True)
class RunResult:
    run_id: StableId
    case_id: StableId
    revision_id: StableId | None
    compiled_id: StableId
    created_at: str
    unit_evaluations: tuple[UnitEvaluation, ...]
    balances: tuple[BalanceRecord, ...]
    solver_result: SolverResult
    convergence: ConvergenceStatus
    closure: ClosureStatus
    physical_validity: ValidityStatus
    correlation_validity: ValidityStatus
    provenance: tuple[ProvenanceRecord, ...]
    diagnostics: tuple[Diagnostic, ...] = ()
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(f"unsupported schema version: {self.schema_version}")
        if self.convergence is not self.solver_result.status:
            raise ValueError("run and solver convergence statuses must agree")
