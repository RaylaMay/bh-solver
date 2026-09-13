"""Lumped thermal-storage models for non-steady heat loads."""

from __future__ import annotations

from dataclasses import dataclass

from .audit import CalculationReport, ClosureCheck


@dataclass(frozen=True)
class ThermalBuffer:
    """Sensible plus optional latent thermal store."""

    mass_kg: float
    average_cp_j_kg_k: float
    initial_temperature_k: float
    maximum_temperature_k: float
    latent_heat_j_kg: float = 0.0
    usable_latent_fraction: float = 0.0

    def __post_init__(self) -> None:
        if self.mass_kg <= 0.0 or self.average_cp_j_kg_k <= 0.0:
            raise ValueError("buffer mass and heat capacity must be positive")
        if self.maximum_temperature_k <= self.initial_temperature_k:
            raise ValueError("maximum temperature must exceed initial temperature")
        if self.latent_heat_j_kg < 0.0:
            raise ValueError("latent heat cannot be negative")
        if not 0.0 <= self.usable_latent_fraction <= 1.0:
            raise ValueError("usable latent fraction must be in [0, 1]")

    @property
    def capacity_j(self) -> float:
        sensible_j = (
            self.mass_kg
            * self.average_cp_j_kg_k
            * (self.maximum_temperature_k - self.initial_temperature_k)
        )
        latent_j = self.mass_kg * self.latent_heat_j_kg * self.usable_latent_fraction
        return sensible_j + latent_j

    def assess_surge(
        self,
        *,
        thermal_load_w: float,
        continuous_rejection_w: float,
        duration_s: float,
    ) -> CalculationReport:
        if thermal_load_w < 0.0 or continuous_rejection_w < 0.0 or duration_s < 0.0:
            raise ValueError("loads, rejection, and duration cannot be negative")
        excess_power_w = max(thermal_load_w - continuous_rejection_w, 0.0)
        absorbed_energy_j = excess_power_w * duration_s
        margin_j = self.capacity_j - absorbed_energy_j
        maximum_duration_s = None if excess_power_w == 0.0 else self.capacity_j / excess_power_w
        final_temperature_k = self.initial_temperature_k
        if self.mass_kg * self.average_cp_j_kg_k > 0.0:
            sensible_equivalent_k = min(
                absorbed_energy_j / (self.mass_kg * self.average_cp_j_kg_k),
                self.maximum_temperature_k - self.initial_temperature_k,
            )
            final_temperature_k += sensible_equivalent_k

        warnings: list[str] = []
        if margin_j < 0.0:
            warnings.append("Surge exceeds the modeled thermal-buffer capacity")
        return CalculationReport(
            model="lumped_thermal_buffer",
            outputs={
                "capacity_j": self.capacity_j,
                "excess_power_w": excess_power_w,
                "absorbed_energy_j": absorbed_energy_j,
                "capacity_margin_j": margin_j,
                "maximum_surge_duration_s": maximum_duration_s,
                "sensible_equivalent_final_temperature_k": final_temperature_k,
            },
            equations=[
                "E_capacity = m*cp*(T_max-T_initial) + m*latent_heat*usable_fraction",
                "E_absorbed = max(Q_load-Q_rejection, 0) * duration",
                "duration_max = E_capacity / max(Q_load-Q_rejection, 0)",
            ],
            assumptions=[
                "Lumped uniform buffer temperature",
                "Constant average heat capacity",
                "Constant thermal load and heat rejection during the assessed interval",
                "No heat-transfer-rate limitation between the process loop and buffer",
            ],
            warnings=warnings,
            checks=[ClosureCheck("capacity_margin", min(margin_j, 0.0), 0.0, "J")],
        )
