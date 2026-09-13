"""Auditable steady-state unit operations."""

from __future__ import annotations

from dataclasses import dataclass

from .audit import CalculationReport, ClosureCheck
from .stream import MaterialStream


@dataclass(frozen=True)
class HeaterCooler:
    name: str

    def calculate(self, inlet: MaterialStream, outlet_temperature_k: float) -> CalculationReport:
        outlet = inlet.at_temperature(outlet_temperature_k, name=f"{inlet.name}:out")
        duty_w = outlet.enthalpy_flow_w - inlet.enthalpy_flow_w
        return CalculationReport(
            model="heater_cooler",
            outputs={
                "unit_name": self.name,
                "outlet_temperature_k": outlet.temperature_k,
                "duty_w": duty_w,
            },
            equations=["Q_dot = m_dot * (h_out - h_in)"],
            assumptions=[
                "Steady state",
                "Single phase",
                "Negligible kinetic and potential energy changes",
            ],
            checks=[ClosureCheck("energy_balance", 0.0, max(abs(duty_w), 1.0) * 1.0e-10, "W")],
        )


@dataclass(frozen=True)
class CounterflowHeatExchanger:
    """Two-stream exchanger specified by thermal effectiveness."""

    name: str
    effectiveness: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.effectiveness <= 1.0:
            raise ValueError("effectiveness must be between zero and one")

    def calculate(self, hot_in: MaterialStream, cold_in: MaterialStream) -> CalculationReport:
        if hot_in.temperature_k <= cold_in.temperature_k:
            raise ValueError("hot inlet must be warmer than cold inlet")

        q_hot_limit_w = hot_in.mass_flow_kg_s * (
            hot_in.specific_enthalpy_j_kg - hot_in.fluid.specific_enthalpy(cold_in.temperature_k)
        )
        q_cold_limit_w = cold_in.mass_flow_kg_s * (
            cold_in.fluid.specific_enthalpy(hot_in.temperature_k) - cold_in.specific_enthalpy_j_kg
        )
        q_max_w = min(q_hot_limit_w, q_cold_limit_w)
        duty_w = self.effectiveness * q_max_w

        hot_h_out = hot_in.specific_enthalpy_j_kg - duty_w / hot_in.mass_flow_kg_s
        cold_h_out = cold_in.specific_enthalpy_j_kg + duty_w / cold_in.mass_flow_kg_s
        hot_out_temperature_k = hot_in.fluid.temperature_from_enthalpy(hot_h_out)
        cold_out_temperature_k = cold_in.fluid.temperature_from_enthalpy(cold_h_out)

        q_from_hot_w = hot_in.mass_flow_kg_s * (
            hot_in.specific_enthalpy_j_kg - hot_in.fluid.specific_enthalpy(hot_out_temperature_k)
        )
        q_to_cold_w = cold_in.mass_flow_kg_s * (
            cold_in.fluid.specific_enthalpy(cold_out_temperature_k) - cold_in.specific_enthalpy_j_kg
        )
        residual_w = q_from_hot_w - q_to_cold_w
        tolerance_w = max(abs(duty_w), 1.0) * 1.0e-8

        warnings: list[str] = []
        if hot_out_temperature_k < cold_in.temperature_k - 1.0e-6:
            warnings.append("Hot outlet is below the cold inlet temperature")
        if cold_out_temperature_k > hot_in.temperature_k + 1.0e-6:
            warnings.append("Cold outlet is above the hot inlet temperature")

        return CalculationReport(
            model="counterflow_heat_exchanger",
            outputs={
                "unit_name": self.name,
                "duty_w": duty_w,
                "maximum_duty_w": q_max_w,
                "hot_outlet_temperature_k": hot_out_temperature_k,
                "cold_outlet_temperature_k": cold_out_temperature_k,
            },
            equations=[
                "Q_dot,max = min[m_hot*(h_hot,in-h_hot@T_cold,in), "
                "m_cold*(h_cold@T_hot,in-h_cold,in)]",
                "Q_dot = effectiveness * Q_dot,max",
                "Q_dot = m_hot*(h_hot,in-h_hot,out) = m_cold*(h_cold,out-h_cold,in)",
            ],
            assumptions=[
                "Steady state",
                "Adiabatic exchanger shell",
                "Single phase on both sides",
                "No pressure-drop model in this release",
            ],
            warnings=warnings,
            checks=[ClosureCheck("energy_balance", residual_w, tolerance_w, "W")],
        )
