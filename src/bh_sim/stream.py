"""Material-stream state passed between unit operations."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .thermo import ThermoModel


@dataclass(frozen=True)
class MaterialStream:
    name: str
    fluid: ThermoModel
    mass_flow_kg_s: float
    temperature_k: float
    pressure_pa: float

    def __post_init__(self) -> None:
        if self.mass_flow_kg_s <= 0.0:
            raise ValueError("mass flow must be positive")
        if self.pressure_pa <= 0.0:
            raise ValueError("absolute pressure must be positive")
        self.fluid.validate_temperature(self.temperature_k)

    @property
    def specific_enthalpy_j_kg(self) -> float:
        return self.fluid.specific_enthalpy(self.temperature_k)

    @property
    def enthalpy_flow_w(self) -> float:
        return self.mass_flow_kg_s * self.specific_enthalpy_j_kg

    def at_temperature(self, temperature_k: float, *, name: str | None = None) -> MaterialStream:
        return replace(self, name=name or self.name, temperature_k=temperature_k)
