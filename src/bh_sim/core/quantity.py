"""Small serializable quantity boundary backed by Pint conversion."""

from __future__ import annotations

import math
from dataclasses import dataclass

import pint


class UnitDefinitionError(ValueError):
    """Raised for unknown or dimensionally incompatible units."""


_REGISTRY = pint.UnitRegistry(autoconvert_offset_to_baseunit=True)

# The schema accepts a reviewed vocabulary even though Pint knows many more units.
# unit -> (engineering dimension, canonical SI spelling)
_UNITS: dict[str, tuple[str, str]] = {
    "1": ("dimensionless", "1"),
    "%": ("dimensionless", "1"),
    "K": ("temperature", "K"),
    "degC": ("temperature", "K"),
    "Pa": ("pressure", "Pa"),
    "kPa": ("pressure", "Pa"),
    "MPa": ("pressure", "Pa"),
    "bar": ("pressure", "Pa"),
    "kg": ("mass", "kg"),
    "g": ("mass", "kg"),
    "m": ("length", "m"),
    "mm": ("length", "m"),
    "m^2": ("area", "m^2"),
    "s": ("time", "s"),
    "min": ("time", "s"),
    "kg/s": ("mass_flow", "kg/s"),
    "kg/h": ("mass_flow", "kg/s"),
    "W": ("power", "W"),
    "kW": ("power", "W"),
    "MW": ("power", "W"),
    "W/K": ("thermal_conductance", "W/K"),
    "kW/K": ("thermal_conductance", "W/K"),
    "W/m^2": ("heat_flux", "W/m^2"),
    "W/(m^2*K^4)": ("radiation_constant", "W/(m^2*K^4)"),
    "J": ("energy", "J"),
    "kJ": ("energy", "J"),
    "J/kg": ("specific_energy", "J/kg"),
    "kJ/kg": ("specific_energy", "J/kg"),
    "J/(kg*K)": ("specific_heat", "J/(kg*K)"),
    "kJ/(kg*K)": ("specific_heat", "J/(kg*K)"),
    "kg/m^3": ("density", "kg/m^3"),
    "m/s": ("velocity", "m/s"),
}


@dataclass(frozen=True)
class Quantity:
    """A finite scalar and explicit recognized unit."""

    value: float
    unit: str

    def __post_init__(self) -> None:
        if self.unit not in _UNITS:
            raise UnitDefinitionError(f"unknown unit: {self.unit!r}")
        if not math.isfinite(self.value):
            raise ValueError("quantity value must be finite")

    @property
    def dimension(self) -> str:
        return _UNITS[self.unit][0]

    @property
    def si_value(self) -> float:
        canonical = self.si_unit
        return float(_REGISTRY.Quantity(self.value, self.unit).to(canonical).magnitude)

    @property
    def si_unit(self) -> str:
        return _UNITS[self.unit][1]

    def to(self, unit: str) -> Quantity:
        if unit not in _UNITS:
            raise UnitDefinitionError(f"unknown unit: {unit!r}")
        target_dimension, _ = _UNITS[unit]
        if target_dimension != self.dimension:
            raise UnitDefinitionError(
                f"cannot convert {self.dimension} ({self.unit}) to {target_dimension} ({unit})"
            )
        converted = _REGISTRY.Quantity(self.value, self.unit).to(unit)
        return Quantity(float(converted.magnitude), unit)

    def require_dimension(self, expected: str) -> Quantity:
        if self.dimension != expected:
            raise UnitDefinitionError(
                f"expected {expected}, received {self.dimension} ({self.unit})"
            )
        return self
