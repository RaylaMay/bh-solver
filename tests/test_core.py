from __future__ import annotations

import math
import unittest

from bh_sim import (
    CounterflowHeatExchanger,
    DropletRadiator,
    MaterialStream,
    PolynomialLiquid,
    SolidRadiator,
    ThermalBuffer,
)


class CoreModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fluid = PolynomialLiquid(
            name="test fluid",
            density_kg_m3=1000.0,
            cp_a_j_kg_k=1000.0,
            cp_b_j_kg_k2=0.2,
            minimum_temperature_k=250.0,
            maximum_temperature_k=1500.0,
            provenance="test coefficients",
        )

    def test_enthalpy_inversion(self) -> None:
        for temperature_k in (250.0, 300.0, 800.0, 1499.0):
            enthalpy = self.fluid.specific_enthalpy(temperature_k)
            recovered = self.fluid.temperature_from_enthalpy(enthalpy)
            self.assertAlmostEqual(recovered, temperature_k, places=7)

    def test_stream_accepts_property_contract_not_concrete_class(self) -> None:
        class ContractFluid:
            name = "contract test fluid"
            density_kg_m3 = 900.0
            minimum_temperature_k = 250.0
            maximum_temperature_k = 500.0
            provenance = "test double"

            def validate_temperature(self, temperature_k: float) -> None:
                if not self.minimum_temperature_k <= temperature_k <= self.maximum_temperature_k:
                    raise ValueError("out of range")

            def cp(self, temperature_k: float) -> float:
                self.validate_temperature(temperature_k)
                return 2000.0

            def specific_enthalpy(self, temperature_k: float) -> float:
                self.validate_temperature(temperature_k)
                return 2000.0 * (temperature_k - 250.0)

            def temperature_from_enthalpy(self, enthalpy_j_kg: float) -> float:
                return 250.0 + enthalpy_j_kg / 2000.0

        stream = MaterialStream("contract", ContractFluid(), 1.0, 300.0, 100_000.0)
        self.assertEqual(stream.specific_enthalpy_j_kg, 100_000.0)

    def test_heat_exchanger_energy_closure(self) -> None:
        hot = MaterialStream("hot", self.fluid, 2.0, 900.0, 200_000.0)
        cold = MaterialStream("cold", self.fluid, 3.0, 300.0, 200_000.0)
        report = CounterflowHeatExchanger("HX-1", effectiveness=0.75).calculate(hot, cold)
        self.assertTrue(report.valid)
        self.assertGreater(report.outputs["hot_outlet_temperature_k"], 300.0)
        self.assertLess(report.outputs["cold_outlet_temperature_k"], 900.0)

    def test_solid_radiator_area_and_closure(self) -> None:
        stream = MaterialStream("loop", self.fluid, 5.0, 700.0, 300_000.0)
        report = SolidRadiator(emissivity=0.9).size(stream, 500.0)
        self.assertTrue(report.valid)
        self.assertGreater(report.outputs["required_planform_area_m2"], 0.0)
        self.assertGreater(report.outputs["duty_w"], 0.0)

    def test_droplet_radiator_cools_and_closes(self) -> None:
        stream = MaterialStream("spray", self.fluid, 2.0, 1000.0, 100_000.0)
        report = DropletRadiator(
            droplet_radius_m=100.0e-6,
            spray_length_m=100.0,
            droplet_velocity_m_s=10.0,
            emissivity=0.5,
        ).calculate(stream)
        self.assertTrue(report.valid)
        self.assertLess(report.outputs["outlet_temperature_k"], 1000.0)
        self.assertGreater(report.outputs["duty_w"], 0.0)

    def test_buffer_capacity_and_overload(self) -> None:
        buffer = ThermalBuffer(
            mass_kg=1000.0,
            average_cp_j_kg_k=1000.0,
            initial_temperature_k=300.0,
            maximum_temperature_k=400.0,
        )
        okay = buffer.assess_surge(
            thermal_load_w=2.0e6,
            continuous_rejection_w=1.0e6,
            duration_s=50.0,
        )
        overload = buffer.assess_surge(
            thermal_load_w=2.0e6,
            continuous_rejection_w=1.0e6,
            duration_s=150.0,
        )
        self.assertTrue(okay.valid)
        self.assertFalse(overload.valid)
        self.assertTrue(math.isclose(okay.outputs["maximum_surge_duration_s"], 100.0))


if __name__ == "__main__":
    unittest.main()
