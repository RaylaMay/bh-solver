"""Steady and flight-path radiator models."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp

from .audit import CalculationReport, ClosureCheck
from .stream import MaterialStream

STEFAN_BOLTZMANN_W_M2_K4 = 5.670374419e-8


@dataclass(frozen=True)
class SolidRadiator:
    """Segmented solid-surface radiator sized from coolant enthalpy loss."""

    emissivity: float
    sink_temperature_k: float = 3.0
    radiating_sides: int = 2
    segments: int = 40

    def __post_init__(self) -> None:
        if not 0.0 < self.emissivity <= 1.0:
            raise ValueError("emissivity must be in (0, 1]")
        if self.sink_temperature_k < 0.0:
            raise ValueError("sink temperature cannot be negative")
        if self.radiating_sides not in (1, 2):
            raise ValueError("radiating_sides must be one or two")
        if self.segments < 1:
            raise ValueError("segments must be positive")

    def size(self, inlet: MaterialStream, outlet_temperature_k: float) -> CalculationReport:
        if outlet_temperature_k >= inlet.temperature_k:
            raise ValueError("radiator outlet must be colder than its inlet")
        inlet.fluid.validate_temperature(outlet_temperature_k)
        if outlet_temperature_k <= self.sink_temperature_k:
            raise ValueError("radiator outlet must exceed sink temperature")

        total_area_m2 = 0.0
        total_duty_w = 0.0
        delta_t = (inlet.temperature_k - outlet_temperature_k) / self.segments
        for index in range(self.segments):
            hot_k = inlet.temperature_k - index * delta_t
            cold_k = hot_k - delta_t
            mean_k = 0.5 * (hot_k + cold_k)
            segment_duty_w = inlet.mass_flow_kg_s * (
                inlet.fluid.specific_enthalpy(hot_k) - inlet.fluid.specific_enthalpy(cold_k)
            )
            flux_w_m2 = (
                self.radiating_sides
                * self.emissivity
                * STEFAN_BOLTZMANN_W_M2_K4
                * (mean_k**4 - self.sink_temperature_k**4)
            )
            total_area_m2 += segment_duty_w / flux_w_m2
            total_duty_w += segment_duty_w

        enthalpy_duty_w = inlet.mass_flow_kg_s * (
            inlet.specific_enthalpy_j_kg - inlet.fluid.specific_enthalpy(outlet_temperature_k)
        )
        residual_w = total_duty_w - enthalpy_duty_w
        return CalculationReport(
            model="segmented_solid_radiator",
            outputs={
                "duty_w": total_duty_w,
                "required_planform_area_m2": total_area_m2,
                "inlet_temperature_k": inlet.temperature_k,
                "outlet_temperature_k": outlet_temperature_k,
                "average_heat_flux_w_m2": total_duty_w / total_area_m2,
            },
            equations=[
                "Q_dot = m_dot * (h_in - h_out)",
                "q''_rad = N_sides * emissivity * sigma * (T_surface^4 - T_sink^4)",
                "A = sum(Q_dot_segment / q''_segment)",
            ],
            assumptions=[
                "Coolant temperature equals local radiator surface temperature",
                "Unobstructed view to a uniform radiative sink",
                "No solar, planetary infrared, or reflected environmental load",
                "No piping, header, armour, deployment, or structure mass model",
            ],
            checks=[
                ClosureCheck(
                    "segmented_enthalpy_balance",
                    residual_w,
                    max(abs(enthalpy_duty_w), 1.0) * 1.0e-9,
                    "W",
                )
            ],
        )


@dataclass(frozen=True)
class DropletRadiator:
    """First-order, optically thin monodisperse droplet-flight model."""

    droplet_radius_m: float
    spray_length_m: float
    droplet_velocity_m_s: float
    emissivity: float
    optical_escape_factor: float = 1.0
    collection_efficiency: float = 1.0
    evaporation_mass_flux_kg_m2_s: float = 0.0
    sink_temperature_k: float = 3.0
    segments: int = 200

    def __post_init__(self) -> None:
        for value, label in (
            (self.droplet_radius_m, "droplet radius"),
            (self.spray_length_m, "spray length"),
            (self.droplet_velocity_m_s, "droplet velocity"),
        ):
            if value <= 0.0:
                raise ValueError(f"{label} must be positive")
        if not 0.0 < self.emissivity <= 1.0:
            raise ValueError("emissivity must be in (0, 1]")
        if not 0.0 < self.optical_escape_factor <= 1.0:
            raise ValueError("optical escape factor must be in (0, 1]")
        if not 0.0 <= self.collection_efficiency <= 1.0:
            raise ValueError("collection efficiency must be in [0, 1]")
        if self.evaporation_mass_flux_kg_m2_s < 0.0:
            raise ValueError("evaporation mass flux cannot be negative")
        if self.segments < 1:
            raise ValueError("segments must be positive")

    def calculate(self, inlet: MaterialStream) -> CalculationReport:
        flight_time_s = self.spray_length_m / self.droplet_velocity_m_s
        dt_s = flight_time_s / self.segments
        temperature_k = inlet.temperature_k
        remaining_mass_fraction = 1.0
        radiated_energy_per_kg_j_kg = 0.0
        reached_property_floor = False

        area_per_mass_m2_kg = 3.0 / (inlet.fluid.density_kg_m3 * self.droplet_radius_m)
        evaporation_rate_fraction_s = self.evaporation_mass_flux_kg_m2_s * area_per_mass_m2_kg

        for _ in range(self.segments):
            radiative_power_per_kg_w_kg = (
                area_per_mass_m2_kg
                * self.emissivity
                * self.optical_escape_factor
                * STEFAN_BOLTZMANN_W_M2_K4
                * (temperature_k**4 - self.sink_temperature_k**4)
            )
            delta_h_j_kg = radiative_power_per_kg_w_kg * dt_s
            candidate_h_j_kg = inlet.fluid.specific_enthalpy(temperature_k) - delta_h_j_kg
            minimum_h_j_kg = inlet.fluid.specific_enthalpy(inlet.fluid.minimum_temperature_k)
            if candidate_h_j_kg <= minimum_h_j_kg:
                candidate_h_j_kg = minimum_h_j_kg
                reached_property_floor = True
            new_temperature_k = inlet.fluid.temperature_from_enthalpy(candidate_h_j_kg)
            radiated_energy_per_kg_j_kg += (
                inlet.fluid.specific_enthalpy(temperature_k) - candidate_h_j_kg
            )
            temperature_k = new_temperature_k

            if evaporation_rate_fraction_s > 0.0:
                remaining_mass_fraction *= exp(-evaporation_rate_fraction_s * dt_s)

        evaporated_fraction = 1.0 - remaining_mass_fraction
        capture_loss_fraction = remaining_mass_fraction * (1.0 - self.collection_efficiency)
        total_loss_fraction = evaporated_fraction + capture_loss_fraction
        makeup_flow_kg_s = inlet.mass_flow_kg_s * total_loss_fraction
        duty_w = inlet.mass_flow_kg_s * radiated_energy_per_kg_j_kg
        in_flight_inventory_kg = inlet.mass_flow_kg_s * flight_time_s
        exposed_area_m2 = in_flight_inventory_kg * area_per_mass_m2_kg

        warnings = [
            "Optically thin monodisperse approximation; mutual droplet shielding is "
            "represented only by the supplied escape factor",
            "Constant droplet radius is assumed despite evaporation",
            "Collector dynamics, electrostatic charging, breakup, collision, and "
            "spacecraft acceleration are not modelled",
            "Evaporation mass flux is a user input; the model does not infer vapour pressure",
        ]
        if total_loss_fraction > 0.01:
            warnings.append("More than 1% of circulating radiator fluid is lost per pass")
        if reached_property_floor:
            warnings.append(
                "Droplets reached the fluid model's minimum temperature; extend the "
                "property model or shorten the flight before using this endpoint"
            )

        enthalpy_duty_w = inlet.mass_flow_kg_s * (
            inlet.specific_enthalpy_j_kg - inlet.fluid.specific_enthalpy(temperature_k)
        )
        return CalculationReport(
            model="optically_thin_droplet_radiator",
            outputs={
                "duty_w": duty_w,
                "outlet_temperature_k": temperature_k,
                "flight_time_s": flight_time_s,
                "in_flight_inventory_kg": in_flight_inventory_kg,
                "exposed_droplet_area_m2": exposed_area_m2,
                "evaporated_fraction_per_pass": evaporated_fraction,
                "uncaptured_fraction_per_pass": capture_loss_fraction,
                "makeup_flow_kg_s": makeup_flow_kg_s,
            },
            equations=[
                "A_droplets / m = 3 / (rho * r)",
                "d(h)/dt = -(A/m) * emissivity * escape_factor * sigma * (T^4 - T_sink^4)",
                "flight_time = spray_length / droplet_velocity",
                "mass_remaining/mass_initial = exp[-j_evap*(A/m)*flight_time]",
            ],
            assumptions=[
                "Steady monodisperse spray",
                "Single liquid phase throughout the flight",
                "Uniform spherical droplets",
                "Negligible conductive and convective heat transfer",
                f"Property provenance: {inlet.fluid.provenance}",
            ],
            warnings=warnings,
            checks=[
                ClosureCheck(
                    "radiative_enthalpy_balance",
                    duty_w - enthalpy_duty_w,
                    max(abs(duty_w), 1.0) * 1.0e-8,
                    "W",
                )
            ],
        )
