from __future__ import annotations

import dataclasses
import unittest

from bh_sim.core import (
    AiProfile,
    BalanceRecord,
    CaseDefinition,
    ClosureStatus,
    CompiledFlowsheet,
    CompositionComponent,
    ConnectionDefinition,
    ConvergenceStatus,
    DraftRevision,
    EnergyPort,
    FlashRequest,
    FlashVariable,
    MaterialPort,
    MaterialReference,
    PortDirection,
    PropertyPackageReference,
    Quantity,
    Residual,
    ResidualProblem,
    ResidualVariable,
    RunResult,
    SolverResult,
    Specification,
    StableId,
    StateSpecification,
    SteadySolver,
    UnitDefinition,
    UnitDefinitionError,
    UnitEvaluation,
    UnitEvaluationRequest,
    UnitOperation,
    ValidityStatus,
    VariableDefinition,
    ports_are_compatible,
)


def sample_case() -> CaseDefinition:
    package_id = StableId("property:polynomial-liquid")
    material_id = StableId("material:tin")
    return CaseDefinition(
        case_id=StableId("case:radiator-loop"),
        title="Radiator loop",
        materials=(MaterialReference(material_id, "Tin", package_id, "model-card:tin-v1"),),
        property_packages=(PropertyPackageReference(package_id, "polynomial-liquid", "0.1"),),
        units=(
            UnitDefinition(
                StableId("unit:source"),
                "source.v1",
                "Tin source",
                (("temperature", Quantity(900.0, "K")),),
            ),
            UnitDefinition(StableId("unit:sink"), "sink.v1", "Tin sink"),
        ),
        connections=(
            ConnectionDefinition(
                StableId("connection:feed"),
                StableId("unit:source"),
                StableId("port:source-out"),
                StableId("unit:sink"),
                StableId("port:sink-in"),
            ),
        ),
        specifications=(
            Specification(
                StableId("specification:flow"),
                StableId("unit:source"),
                "mass_flow",
                Quantity(2.0, "kg/s"),
            ),
        ),
        ai_profile=AiProfile.REVIEW,
    )


class QuantityContractTests(unittest.TestCase):
    def test_explicit_unit_conversion_and_affine_temperature(self) -> None:
        self.assertAlmostEqual(Quantity(25.0, "degC").to("K").value, 298.15)
        self.assertEqual(Quantity(2.0, "MW").to("kW"), Quantity(2000.0, "kW"))
        self.assertAlmostEqual(Quantity(3600.0, "kg/h").si_value, 1.0)

    def test_dimension_mismatch_and_unknown_unit_are_rejected(self) -> None:
        with self.assertRaises(UnitDefinitionError):
            Quantity(1.0, "kg/s").to("K")
        with self.assertRaises(UnitDefinitionError):
            Quantity(1.0, "furlong")

    def test_quantity_is_immutable_and_finite(self) -> None:
        value = Quantity(1.0, "Pa")
        with self.assertRaises(dataclasses.FrozenInstanceError):
            value.value = 2.0  # type: ignore[misc]
        with self.assertRaises(ValueError):
            Quantity(float("nan"), "Pa")


class DomainContractTests(unittest.TestCase):
    def test_stable_id_validation(self) -> None:
        self.assertEqual(str(StableId("unit:HX-101")), "unit:HX-101")
        with self.assertRaises(ValueError):
            StableId("101 invalid")

    def test_ports_require_matching_kind_and_direction(self) -> None:
        material_out = MaterialPort(StableId("port:out"), "out", PortDirection.OUTPUT)
        material_in = MaterialPort(StableId("port:in"), "in", PortDirection.INPUT)
        energy_in = EnergyPort(StableId("port:energy-in"), "energy", PortDirection.INPUT)
        self.assertTrue(ports_are_compatible(material_out, material_in))
        self.assertFalse(ports_are_compatible(material_in, material_out))
        self.assertFalse(ports_are_compatible(material_out, energy_in))

    def test_flash_requires_normalized_composition_and_independent_pair(self) -> None:
        composition = (CompositionComponent(StableId("material:tin"), 1.0),)
        request = FlashRequest(
            StableId("property:tin"),
            composition,
            (
                StateSpecification(FlashVariable.TEMPERATURE, Quantity(900.0, "K")),
                StateSpecification(FlashVariable.PRESSURE, Quantity(100.0, "kPa")),
            ),
        )
        self.assertEqual(request.specifications[0].value.si_unit, "K")
        with self.assertRaises(ValueError):
            FlashRequest(
                StableId("property:tin"),
                composition,
                (
                    StateSpecification(FlashVariable.TEMPERATURE, Quantity(900.0, "K")),
                    StateSpecification(FlashVariable.TEMPERATURE, Quantity(1000.0, "K")),
                ),
            )
        with self.assertRaises(ValueError):
            FlashRequest(
                StableId("property:tin"),
                (CompositionComponent(StableId("material:tin"), 0.8),),
                request.specifications,
            )

    def test_case_and_draft_are_immutable_and_consistent(self) -> None:
        case = sample_case()
        revision = DraftRevision(
            StableId("revision:r1"), case.case_id, 1, case, (), "2026-08-27T00:00:00Z"
        )
        self.assertEqual(revision.case, case)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            case.title = "Changed"  # type: ignore[misc]
        with self.assertRaises(ValueError):
            DraftRevision(
                StableId("revision:bad"),
                StableId("case:other"),
                1,
                case,
                (),
                "2026-08-27T00:00:00Z",
            )

    def test_compiled_contract_keeps_graph_implementation_out(self) -> None:
        compiled = CompiledFlowsheet(
            StableId("compiled:one"),
            StableId("case:radiator-loop"),
            None,
            "a" * 64,
            (StableId("unit:source"), StableId("unit:sink")),
            (
                VariableDefinition(
                    "source.mass_flow", StableId("unit:source"), "mass_flow", 1.0, True
                ),
            ),
            0,
            (),
        )
        self.assertEqual(compiled.degrees_of_freedom, 0)
        self.assertNotIn("graph", {field.name for field in dataclasses.fields(compiled)})

    def test_convergence_closure_and_validity_are_independent(self) -> None:
        solver = SolverResult(
            ConvergenceStatus.CONVERGED,
            (("temperature", 900.0),),
            (),
            (Residual("energy", 0.0, unit="W"),),
            "converged",
        )
        run = RunResult(
            StableId("run:one"),
            StableId("case:radiator-loop"),
            None,
            StableId("compiled:one"),
            "2026-08-27T00:00:00Z",
            (),
            (
                BalanceRecord(
                    "energy",
                    Quantity(0.0, "W"),
                    Quantity(1.0, "W"),
                    ClosureStatus.PASSED,
                ),
            ),
            solver,
            ConvergenceStatus.CONVERGED,
            ClosureStatus.PASSED,
            ValidityStatus.VALID,
            ValidityStatus.EXTRAPOLATED,
            (),
        )
        self.assertIs(run.correlation_validity, ValidityStatus.EXTRAPOLATED)
        with self.assertRaises(ValueError):
            dataclasses.replace(run, convergence=ConvergenceStatus.FAILED)

    def test_protocols_accept_independent_implementations(self) -> None:
        class ExampleUnit:
            model_id = "example.v1"
            ports = ()

            def evaluate(self, request: UnitEvaluationRequest) -> UnitEvaluation:
                return UnitEvaluation(request.unit_id, (), (), (), (), ValidityStatus.VALID, ())

        class ExampleProblem:
            variables = (ResidualVariable("x", 0.0, 1.0),)

            def evaluate(self, values: tuple[float, ...]) -> tuple[Residual, ...]:
                return (Residual("x", values[0]),)

        class ExampleSolver:
            solver_id = "test-solver"

            def solve(self, problem: ResidualProblem) -> SolverResult:
                return SolverResult(
                    ConvergenceStatus.CONVERGED, (("x", 0.0),), (), problem.evaluate((0.0,)), "ok"
                )

        self.assertIsInstance(ExampleUnit(), UnitOperation)
        self.assertIsInstance(ExampleProblem(), ResidualProblem)
        self.assertIsInstance(ExampleSolver(), SteadySolver)


if __name__ == "__main__":
    unittest.main()
