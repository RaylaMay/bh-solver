"""Acyclic sequential-modular execution and immutable run results."""

from __future__ import annotations

from datetime import UTC, datetime

from bh_sim.core import (
    AiProfile,
    BalanceRecord,
    CaseDefinition,
    ClosureStatus,
    ConvergenceStatus,
    Diagnostic,
    EnergyPortValue,
    MaterialPortValue,
    NamedPortValue,
    Quantity,
    RunResult,
    SolverResult,
    StableId,
    UnitEvaluationRequest,
    ValidityStatus,
    new_stable_id,
)

from .catalog import EvaluationServices, ModelCatalog
from .compiler import FlowsheetCompiler, ValidationReport
from .properties import PropertyRegistry


def _worst_validity(values: tuple[ValidityStatus, ...]) -> ValidityStatus:
    order = {
        ValidityStatus.UNKNOWN: 0,
        ValidityStatus.VALID: 1,
        ValidityStatus.EXTRAPOLATED: 2,
        ValidityStatus.INVALID: 3,
    }
    return max(values, key=order.__getitem__) if values else ValidityStatus.UNKNOWN


class AcyclicRunEngine:
    def __init__(self, catalog: ModelCatalog, properties: PropertyRegistry) -> None:
        self.catalog = catalog
        self.properties = properties
        self.compiler = FlowsheetCompiler(catalog)

    def validate(
        self, case: CaseDefinition, *, revision_id: StableId | None = None
    ) -> ValidationReport:
        return self.compiler.compile(case, revision_id=revision_id)

    def run(
        self,
        case: CaseDefinition,
        *,
        revision_id: StableId | None = None,
        run_id: StableId | None = None,
    ) -> RunResult:
        resolved_run_id = run_id or new_stable_id("run")
        validation = self.validate(case, revision_id=revision_id)
        created_at = datetime.now(UTC).isoformat()
        if not validation.valid:
            return RunResult(
                run_id=resolved_run_id,
                case_id=case.case_id,
                revision_id=revision_id,
                compiled_id=validation.compiled.compiled_id,
                created_at=created_at,
                unit_evaluations=(),
                balances=(),
                solver_result=SolverResult(
                    ConvergenceStatus.FAILED,
                    (),
                    (),
                    (),
                    "flowsheet validation failed",
                ),
                convergence=ConvergenceStatus.FAILED,
                closure=ClosureStatus.NOT_CHECKED,
                physical_validity=ValidityStatus.INVALID,
                correlation_validity=ValidityStatus.UNKNOWN,
                provenance=(),
                diagnostics=validation.diagnostics,
            )

        definitions = {unit.unit_id: unit for unit in case.units}
        materials = {material.material_id: material for material in case.materials}
        services = EvaluationServices(self.properties, materials)
        connections_by_target = {
            (connection.target_unit_id, connection.target_port_id): connection
            for connection in case.connections
        }
        outputs: dict[tuple[StableId, StableId], NamedPortValue] = {}
        evaluations = []
        diagnostics: list[Diagnostic] = []
        if case.ai_profile is AiProfile.NARRATIVE:
            diagnostics.append(
                Diagnostic(
                    "narrative-profile",
                    "Narrative-profile result: assumptions may be speculative or placeholders",
                    "warning",
                )
            )

        try:
            for unit_id in validation.compiled.execution_order:
                definition = definitions[unit_id]
                descriptor = self.catalog.descriptor(definition.model_id)
                input_values = []
                for port in descriptor.ports:
                    connection = connections_by_target.get((unit_id, port.port_id))
                    if connection is not None:
                        upstream = outputs[(connection.source_unit_id, connection.source_port_id)]
                        if isinstance(upstream, MaterialPortValue):
                            input_values.append(MaterialPortValue(port.port_id, upstream.state))
                        elif isinstance(upstream, EnergyPortValue):
                            input_values.append(EnergyPortValue(port.port_id, upstream.duty))
                model = self.catalog.build(definition, services)
                evaluation = model.evaluate(
                    UnitEvaluationRequest(unit_id, tuple(input_values), definition.parameters)
                )
                evaluations.append(evaluation)
                diagnostics.extend(evaluation.diagnostics)
                for output in evaluation.output_port_values:
                    outputs[(unit_id, output.port_id)] = output
        except Exception as error:
            diagnostics.append(Diagnostic("unit-evaluation-failed", str(error), "error"))
            return RunResult(
                run_id=resolved_run_id,
                case_id=case.case_id,
                revision_id=revision_id,
                compiled_id=validation.compiled.compiled_id,
                created_at=created_at,
                unit_evaluations=tuple(evaluations),
                balances=(),
                solver_result=SolverResult(
                    ConvergenceStatus.FAILED,
                    (),
                    (),
                    (),
                    "unit evaluation failed",
                ),
                convergence=ConvergenceStatus.FAILED,
                closure=ClosureStatus.NOT_CHECKED,
                physical_validity=ValidityStatus.INVALID,
                correlation_validity=_worst_validity(tuple(item.validity for item in evaluations)),
                provenance=tuple(
                    record
                    for item in evaluations
                    for value in item.output_port_values
                    if isinstance(value, MaterialPortValue)
                    for record in value.state.thermo.provenance
                ),
                diagnostics=tuple(diagnostics),
            )

        source_flow = 0.0
        sink_flow = 0.0
        source_enthalpy_flow_w = 0.0
        sink_enthalpy_flow_w = 0.0
        equipment_duty_w = 0.0
        for definition, evaluation in zip(
            (definitions[item] for item in validation.compiled.execution_order),
            evaluations,
            strict=True,
        ):
            if definition.model_id == "source":
                source_flow += sum(
                    value.state.mass_flow.to("kg/s").value
                    for value in evaluation.output_port_values
                    if isinstance(value, MaterialPortValue)
                )
                source_enthalpy_flow_w += sum(
                    value.state.mass_flow.to("kg/s").value
                    * value.state.thermo.specific_enthalpy.to("J/kg").value
                    for value in evaluation.output_port_values
                    if isinstance(value, MaterialPortValue)
                )
            elif definition.model_id == "sink":
                descriptor = self.catalog.descriptor("sink")
                inlet_port = descriptor.ports[0]
                connection = connections_by_target[(definition.unit_id, inlet_port.port_id)]
                value = outputs[(connection.source_unit_id, connection.source_port_id)]
                if isinstance(value, MaterialPortValue):
                    sink_flow += value.state.mass_flow.to("kg/s").value
                    sink_enthalpy_flow_w += (
                        value.state.mass_flow.to("kg/s").value
                        * value.state.thermo.specific_enthalpy.to("J/kg").value
                    )
            equipment_duty_w += sum(
                value.duty.to("W").value
                for value in evaluation.output_port_values
                if isinstance(value, EnergyPortValue)
            )

        mass_residual = source_flow - sink_flow
        mass_tolerance = max(source_flow, sink_flow, 1.0) * 1.0e-8
        mass_closure = (
            ClosureStatus.PASSED if abs(mass_residual) <= mass_tolerance else ClosureStatus.FAILED
        )
        mass_balance = BalanceRecord(
            "overall-mass",
            Quantity(mass_residual, "kg/s"),
            Quantity(mass_tolerance, "kg/s"),
            mass_closure,
        )
        energy_residual_w = source_enthalpy_flow_w + equipment_duty_w - sink_enthalpy_flow_w
        energy_tolerance_w = (
            max(
                abs(source_enthalpy_flow_w),
                abs(equipment_duty_w),
                abs(sink_enthalpy_flow_w),
                1.0,
            )
            * 1.0e-8
        )
        energy_closure = (
            ClosureStatus.PASSED
            if abs(energy_residual_w) <= energy_tolerance_w
            else ClosureStatus.FAILED
        )
        energy_balance = BalanceRecord(
            "overall-energy",
            Quantity(energy_residual_w, "W"),
            Quantity(energy_tolerance_w, "W"),
            energy_closure,
        )
        closure = (
            ClosureStatus.PASSED
            if mass_closure is ClosureStatus.PASSED and energy_closure is ClosureStatus.PASSED
            else ClosureStatus.FAILED
        )
        validity = _worst_validity(tuple(item.validity for item in evaluations))
        return RunResult(
            run_id=resolved_run_id,
            case_id=case.case_id,
            revision_id=revision_id,
            compiled_id=validation.compiled.compiled_id,
            created_at=created_at,
            unit_evaluations=tuple(evaluations),
            balances=(mass_balance, energy_balance),
            solver_result=SolverResult(
                ConvergenceStatus.CONVERGED,
                (),
                (),
                (),
                "acyclic sequential evaluation completed",
            ),
            convergence=ConvergenceStatus.CONVERGED,
            closure=closure,
            physical_validity=(
                ValidityStatus.INVALID
                if validity is ValidityStatus.INVALID
                else ValidityStatus.VALID
            ),
            correlation_validity=validity,
            provenance=tuple(
                record
                for item in evaluations
                for value in item.output_port_values
                if isinstance(value, MaterialPortValue)
                for record in value.state.thermo.provenance
            ),
            diagnostics=tuple(diagnostics),
        )
