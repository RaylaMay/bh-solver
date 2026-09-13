"""Minimal thermophysical-property contracts and liquid models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from .numerics import bisect


@runtime_checkable
class ThermoModel(Protocol):
    """Property-service boundary consumed by streams and unit operations.

    Any future EOS, table, external property package, or test double can satisfy
    this protocol without making the calculation core depend on its package.
    """

    @property
    def name(self) -> str: ...

    @property
    def density_kg_m3(self) -> float: ...

    @property
    def minimum_temperature_k(self) -> float: ...

    @property
    def maximum_temperature_k(self) -> float: ...

    @property
    def provenance(self) -> str: ...

    def validate_temperature(self, temperature_k: float) -> None: ...

    def cp(self, temperature_k: float) -> float: ...

    def specific_enthalpy(self, temperature_k: float) -> float: ...

    def temperature_from_enthalpy(self, enthalpy_j_kg: float) -> float: ...


@dataclass(frozen=True)
class PolynomialLiquid:
    """Single-phase liquid with polynomial heat capacity.

    cp(T) = a + b*T + c*T^2 in J/(kg K). Enthalpy is measured relative to
    ``reference_temperature_k``. Density is presently constant; a later property
    backend can replace this class without changing unit-operation interfaces.
    """

    name: str
    density_kg_m3: float
    cp_a_j_kg_k: float
    cp_b_j_kg_k2: float = 0.0
    cp_c_j_kg_k3: float = 0.0
    minimum_temperature_k: float = 1.0
    maximum_temperature_k: float = 5000.0
    reference_temperature_k: float = 298.15
    provenance: str = "user-supplied coefficients"

    def __post_init__(self) -> None:
        if self.density_kg_m3 <= 0.0:
            raise ValueError("density must be positive")
        if self.minimum_temperature_k <= 0.0:
            raise ValueError("minimum temperature must be positive")
        if self.maximum_temperature_k <= self.minimum_temperature_k:
            raise ValueError("invalid temperature range")
        self.validate_temperature(self.reference_temperature_k)
        if self.cp(self.minimum_temperature_k) <= 0.0:
            raise ValueError("heat capacity must remain positive at minimum temperature")
        if self.cp(self.maximum_temperature_k) <= 0.0:
            raise ValueError("heat capacity must remain positive at maximum temperature")

    def validate_temperature(self, temperature_k: float) -> None:
        if not self.minimum_temperature_k <= temperature_k <= self.maximum_temperature_k:
            raise ValueError(
                f"{self.name} temperature {temperature_k:g} K is outside "
                f"[{self.minimum_temperature_k:g}, {self.maximum_temperature_k:g}] K"
            )

    def cp(self, temperature_k: float) -> float:
        self.validate_temperature(temperature_k)
        return (
            self.cp_a_j_kg_k
            + self.cp_b_j_kg_k2 * temperature_k
            + self.cp_c_j_kg_k3 * temperature_k**2
        )

    def specific_enthalpy(self, temperature_k: float) -> float:
        self.validate_temperature(temperature_k)
        t = temperature_k
        t0 = self.reference_temperature_k
        return (
            self.cp_a_j_kg_k * (t - t0)
            + 0.5 * self.cp_b_j_kg_k2 * (t**2 - t0**2)
            + (self.cp_c_j_kg_k3 / 3.0) * (t**3 - t0**3)
        )

    def temperature_from_enthalpy(self, enthalpy_j_kg: float) -> float:
        return bisect(
            lambda temperature: self.specific_enthalpy(temperature) - enthalpy_j_kg,
            self.minimum_temperature_k,
            self.maximum_temperature_k,
        )
