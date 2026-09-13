"""Retained prototype demonstration implementation, outside all public UI adapters."""

from __future__ import annotations

import json

from bh_sim.audit import CalculationReport, ClosureCheck
from bh_sim.boundary.contracts import DemonstrationReportDto
from bh_sim.radiators import DropletRadiator, SolidRadiator
from bh_sim.stream import MaterialStream
from bh_sim.thermo import PolynomialLiquid
from bh_sim.transients import ThermalBuffer


def illustrative_fluid() -> PolynomialLiquid:
    """Retain illustrative placeholder property inputs; not approved material data."""
    return PolynomialLiquid(
        name="illustrative liquid metal",
        density_kg_m3=6500.0,
        cp_a_j_kg_k=240.0,
        minimum_temperature_k=600.0,
        maximum_temperature_k=1600.0,
        reference_temperature_k=600.0,
        provenance="illustrative placeholder; not approved tin property data",
    )


def demonstration_report(command: str) -> CalculationReport:
    """Execute a retained prototype report without promoting a flowsheet model."""
    fluid = illustrative_fluid()
    stream = MaterialStream("hot-loop", fluid, 100.0, 1200.0, 500_000.0)
    if command == "solid-radiator":
        return SolidRadiator(emissivity=0.85).size(stream, 900.0)
    if command == "droplet-radiator":
        return DropletRadiator(
            droplet_radius_m=50.0e-6,
            spray_length_m=500.0,
            droplet_velocity_m_s=20.0,
            emissivity=0.35,
            optical_escape_factor=0.65,
            collection_efficiency=0.9999,
        ).calculate(stream)
    if command == "surge-buffer":
        return ThermalBuffer(
            mass_kg=20_000.0,
            average_cp_j_kg_k=500.0,
            initial_temperature_k=500.0,
            maximum_temperature_k=700.0,
            latent_heat_j_kg=120_000.0,
            usable_latent_fraction=0.8,
        ).assess_surge(
            thermal_load_w=2.0e9,
            continuous_rejection_w=1.2e9,
            duration_s=3.0,
        )
    raise ValueError(f"unknown command {command}")


class PrototypeDemonstrationAdapter:
    """Wrap legacy reports without registering prototype equations as models."""

    def evaluate(self, name: str) -> DemonstrationReportDto:
        """Return the unchanged report as an immutable neutral JSON value."""
        return DemonstrationReportDto(
            json.dumps(demonstration_report(name).to_dict(), indent=2, allow_nan=False)
        )


def restore_legacy_report(report: DemonstrationReportDto) -> CalculationReport:
    """Restore historical Python report identity from already calculated output."""
    data = report.to_dict()
    return CalculationReport(
        data["model"],
        data["outputs"],
        data["equations"],
        data["assumptions"],
        data["warnings"],
        [
            ClosureCheck(item["name"], item["residual"], item["tolerance"], item["units"])
            for item in data["checks"]
        ],
    )
