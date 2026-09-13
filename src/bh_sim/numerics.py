"""Small deterministic numerical methods used by the core models."""

from __future__ import annotations

from collections.abc import Callable


def bisect(
    function: Callable[[float], float],
    lower: float,
    upper: float,
    *,
    absolute_tolerance: float = 1.0e-9,
    maximum_iterations: int = 200,
) -> float:
    """Return a root in a bracket using a dependency-free bisection method."""

    f_lower = function(lower)
    f_upper = function(upper)
    if f_lower == 0.0:
        return lower
    if f_upper == 0.0:
        return upper
    if f_lower * f_upper > 0.0:
        raise ValueError("root is not bracketed")

    for _ in range(maximum_iterations):
        midpoint = 0.5 * (lower + upper)
        f_midpoint = function(midpoint)
        if abs(f_midpoint) <= absolute_tolerance or upper - lower <= absolute_tolerance:
            return midpoint
        if f_lower * f_midpoint <= 0.0:
            upper = midpoint
            f_upper = f_midpoint
        else:
            lower = midpoint
            f_lower = f_midpoint
    raise RuntimeError("bisection did not converge")
