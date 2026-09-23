"""Replaceable future control, plant and numerical ports; no engine implementation."""

from __future__ import annotations

from typing import Protocol

from bh_sim.boundary import contracts as c


class DynamicPlantEnginePort(Protocol):
    """Advance a governed dynamic plant to one coordinator exchange boundary."""

    def step(self, exchange: c.CoSimulationExchange) -> c.CoSimulationExchange: ...


class ControlEnginePort(Protocol):
    """Evaluate a versioned control diagram at one deterministic scheduler boundary."""

    def step(
        self, diagram: c.ControlDiagram, exchange: c.CoSimulationExchange
    ) -> c.CoSimulationExchange: ...


class CoSimulationCoordinatorPort(Protocol):
    """Coordinate replaceable plant/control engines and publish a complete trajectory."""

    def run(
        self, diagram: c.ControlDiagram, schedule: c.ControlSchedule
    ) -> c.ControlTrajectoryReference: ...


class OdeDaeAdapterPort(Protocol):
    """Future ODE/DAE adapter accepts governed problem and configuration artifacts."""

    def integrate(self, problem_artifact_id: str, configuration_id: str) -> str: ...


class RootFindingAdapterPort(Protocol):
    """Future root adapter accepts governed problem and configuration artifacts."""

    def solve(self, problem_artifact_id: str, configuration_id: str) -> str: ...
