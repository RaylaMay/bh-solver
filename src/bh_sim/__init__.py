"""Auditable components with lazy compatibility exports.

Importing a neutral subpackage must not load scientific implementations. Existing
public symbols resolve to the original classes only on explicit access.
"""

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .audit import CalculationReport, ClosureCheck
    from .radiators import DropletRadiator, SolidRadiator
    from .stream import MaterialStream
    from .thermo import PolynomialLiquid, ThermoModel
    from .transients import ThermalBuffer
    from .unit_ops import CounterflowHeatExchanger, HeaterCooler

_EXPORTS = {
    "CalculationReport": "audit",
    "ClosureCheck": "audit",
    "CounterflowHeatExchanger": "unit_ops",
    "DropletRadiator": "radiators",
    "HeaterCooler": "unit_ops",
    "MaterialStream": "stream",
    "PolynomialLiquid": "thermo",
    "SolidRadiator": "radiators",
    "ThermalBuffer": "transients",
    "ThermoModel": "thermo",
}

__all__ = [
    "CalculationReport",
    "ClosureCheck",
    "CounterflowHeatExchanger",
    "DropletRadiator",
    "HeaterCooler",
    "MaterialStream",
    "PolynomialLiquid",
    "SolidRadiator",
    "ThermalBuffer",
    "ThermoModel",
]


def __getattr__(name: str) -> Any:
    """Resolve historical explicit public exports on demand."""

    if name not in _EXPORTS:
        raise AttributeError(name)
    value = getattr(import_module(f".{_EXPORTS[name]}", __name__), name)
    globals()[name] = value
    return value
