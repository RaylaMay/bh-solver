"""SciPy bounded least-squares implementation of the steady solver port."""

from __future__ import annotations

import numpy as np
from scipy.optimize import least_squares

from bh_sim.core import (
    ConvergenceStatus,
    ResidualProblem,
    SolverIteration,
    SolverResult,
)


class ScipyLeastSquaresSolver:
    @property
    def solver_id(self) -> str:
        return "scipy.least_squares"

    def solve(self, problem: ResidualProblem) -> SolverResult:
        variables = problem.variables
        initial = np.asarray([item.initial_value / item.scale for item in variables])
        lower = np.asarray(
            [
                -np.inf if item.lower_bound is None else item.lower_bound / item.scale
                for item in variables
            ]
        )
        upper = np.asarray(
            [
                np.inf if item.upper_bound is None else item.upper_bound / item.scale
                for item in variables
            ]
        )
        history: list[SolverIteration] = []

        def residuals(scaled_values: np.ndarray) -> np.ndarray:
            physical_values = tuple(
                float(value * variable.scale)
                for value, variable in zip(scaled_values, variables, strict=True)
            )
            evaluated = problem.evaluate(physical_values)
            scaled_residuals = np.asarray([item.value / item.scale for item in evaluated])
            history.append(SolverIteration(len(history), float(np.linalg.norm(scaled_residuals))))
            return scaled_residuals

        result = least_squares(residuals, initial, bounds=(lower, upper))
        physical = tuple(
            (variable.name, float(value * variable.scale))
            for value, variable in zip(result.x, variables, strict=True)
        )
        final = problem.evaluate(tuple(value for _, value in physical))
        status = ConvergenceStatus.CONVERGED if result.success else ConvergenceStatus.FAILED
        return SolverResult(status, physical, tuple(history), final, result.message)
