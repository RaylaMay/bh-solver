from __future__ import annotations

from dataclasses import dataclass

import pytest

from bh_sim.core import (
    AiProfile,
    CaseDefinition,
    ClosureStatus,
    CompositionComponent,
    ConnectionDefinition,
    ConvergenceStatus,
    FlashRequest,
    FlashVariable,
    MaterialReference,
    PropertyPackageReference,
    Quantity,
    Residual,
    ResidualVariable,
    StableId,
    StateSpecification,
    UnitDefinition,
    ValidityStatus,
)
from bh_sim.engine import (
    AcyclicRunEngine,
    PolynomialLiquidPackage,
    PropertyRegistry,
    ReferenceLiquid,
    reference_model_catalog,
)
from bh_sim.engine.models import INLET, OUTLET
from bh_sim.solvers import ScipyLeastSquaresSolver

PACKAGE = StableId("properties:test")
MATERIAL = StableId("material:test")


def property_package(cp: float = 1000.0) -> PolynomialLiquidPackage:
    return PolynomialLiquidPackage(
        PACKAGE,
        (
            ReferenceLiquid(
                MATERIAL,
                "test liquid",
                900.0,
                cp,
                evidence_minimum_temperature_k=250.0,
                evidence_maximum_temperature_k=1000.0,
                hard_minimum_temperature_k=100.0,
                hard_maximum_temperature_k=2000.0,
                evidence_reference="TEST-DATA",
            ),
        ),
    )


def simple_case(*, heater_duty_w: float = 500_000.0) -> CaseDefinition:
    source = StableId("unit:source")
    heater = StableId("unit:heater")
    radiator = StableId("unit:radiator")
    sink = StableId("unit:sink")
    return CaseDefinition(
        StableId("case:vertical-slice"),
        "Vertical slice",
        (MaterialReference(MATERIAL, "test liquid", PACKAGE, "TEST-DATA"),),
        (PropertyPackageReference(PACKAGE, "test", "1"),),
        (
            UnitDefinition(
                source,
                "source",
                "Source",
                (
                    ("mass_flow", Quantity(1.0, "kg/s")),
                    ("pressure", Quantity(1.0, "bar")),
                    ("temperature", Quantity(300.0, "K")),
                ),
                (("material_id", str(MATERIAL)),),
            ),
            UnitDefinition(
                heater,
                "heater",
                "Heater",
                (("duty", Quantity(heater_duty_w, "W")),),
            ),
            UnitDefinition(
                radiator,
                "radiator",
                "Radiator",
                (
                    ("emissivity", Quantity(0.9, "1")),
                    ("outlet_temperature", Quantity(500.0, "K")),
                ),
            ),
            UnitDefinition(sink, "sink", "Sink"),
        ),
        (
            ConnectionDefinition(StableId("connection:1"), source, OUTLET, heater, INLET),
            ConnectionDefinition(StableId("connection:2"), heater, OUTLET, radiator, INLET),
            ConnectionDefinition(StableId("connection:3"), radiator, OUTLET, sink, INLET),
        ),
        (),
        AiProfile.REVIEW,
    )


def test_polynomial_property_backend_separates_extrapolation_from_invalidity() -> None:
    package = property_package()
    composition = (CompositionComponent(MATERIAL, 1.0),)
    state = package.flash(
        FlashRequest(
            PACKAGE,
            composition,
            (
                StateSpecification(FlashVariable.TEMPERATURE, Quantity(1200.0, "K")),
                StateSpecification(FlashVariable.PRESSURE, Quantity(1.0, "bar")),
            ),
        )
    )
    assert state.validity is ValidityStatus.EXTRAPOLATED
    with pytest.raises(ValueError, match="hard domain"):
        package.flash(
            FlashRequest(
                PACKAGE,
                composition,
                (
                    StateSpecification(FlashVariable.TEMPERATURE, Quantity(2200.0, "K")),
                    StateSpecification(FlashVariable.PRESSURE, Quantity(1.0, "bar")),
                ),
            )
        )


def test_vertical_slice_compiles_and_closes_mass_and_energy() -> None:
    engine = AcyclicRunEngine(reference_model_catalog(), PropertyRegistry((property_package(),)))
    case = simple_case()
    report = engine.validate(case)
    result = engine.run(case)
    assert report.valid
    assert report.degrees_of_freedom == 0
    assert result.convergence is ConvergenceStatus.CONVERGED
    assert result.closure is ClosureStatus.PASSED
    balances = {item.name: item for item in result.balances}
    assert balances["overall-mass"].residual.value == pytest.approx(0.0)
    assert (
        abs(balances["overall-energy"].residual.value) <= balances["overall-energy"].tolerance.value
    )
    assert len(result.unit_evaluations) == 4
    radiator = next(
        evaluation
        for evaluation in result.unit_evaluations
        if evaluation.unit_id == StableId("unit:radiator")
    )
    assert dict(radiator.metrics)["required_planform_area"].value > 0.0
    radiator_audit = next(item for item in radiator.audit_evidence if item.name == "radiator-area")
    assert {name for name, _ in radiator_audit.inputs} >= {
        "rejected_duty",
        "emissivity",
        "stefan_boltzmann",
        "mean_temperature",
        "sink_temperature",
    }


def test_backend_substitution_changes_numbers_without_changing_case_contract() -> None:
    case = simple_case()
    first = AcyclicRunEngine(
        reference_model_catalog(), PropertyRegistry((property_package(1000.0),))
    ).run(case)
    second = AcyclicRunEngine(
        reference_model_catalog(), PropertyRegistry((property_package(1250.0),))
    ).run(case)
    first_temperature = dict(first.unit_evaluations[1].metrics)["outlet_temperature"]
    second_temperature = dict(second.unit_evaluations[1].metrics)["outlet_temperature"]
    assert first_temperature != second_temperature
    assert case == simple_case()


def test_unconnected_input_reports_degrees_of_freedom_and_subject() -> None:
    case = simple_case()
    broken = CaseDefinition(
        case.case_id,
        case.title,
        case.materials,
        case.property_packages,
        case.units,
        case.connections[:-1],
        case.specifications,
    )
    report = AcyclicRunEngine(
        reference_model_catalog(), PropertyRegistry((property_package(),))
    ).validate(broken)
    assert not report.valid
    assert report.degrees_of_freedom == 1
    diagnostic = next(item for item in report.diagnostics if item.code == "unconnected-input")
    assert diagnostic.subject_id == StableId("unit:sink")


@dataclass(frozen=True)
class SquareRootProblem:
    variables = (ResidualVariable("x", 1.0, 2.0, 0.0, 10.0),)

    def evaluate(self, values: tuple[float, ...]) -> tuple[Residual, ...]:
        return (Residual("x_squared_minus_four", values[0] ** 2 - 4.0, 4.0),)


def test_scipy_solver_is_isolated_behind_the_residual_contract() -> None:
    result = ScipyLeastSquaresSolver().solve(SquareRootProblem())
    assert result.status is ConvergenceStatus.CONVERGED
    assert dict(result.values)["x"] == pytest.approx(2.0)
    assert abs(result.final_residuals[0].value) < 1.0e-6
