"""Structured, serializable calculation records."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ClosureCheck:
    """A numerical check with an explicit acceptance tolerance."""

    name: str
    residual: float
    tolerance: float
    units: str

    @property
    def passed(self) -> bool:
        return abs(self.residual) <= self.tolerance


@dataclass
class CalculationReport:
    """Numbers-first result with the reasoning needed to audit it."""

    model: str
    outputs: dict[str, Any]
    equations: list[str]
    assumptions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checks: list[ClosureCheck] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return all(check.passed for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["valid"] = self.valid
        for check, raw in zip(self.checks, result["checks"], strict=True):
            raw["passed"] = check.passed
        return result
