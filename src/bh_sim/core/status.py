"""Independent status dimensions for simulation results."""

from enum import StrEnum


class ValidityStatus(StrEnum):
    UNKNOWN = "unknown"
    VALID = "valid"
    EXTRAPOLATED = "extrapolated"
    INVALID = "invalid"


class ConvergenceStatus(StrEnum):
    NOT_RUN = "not_run"
    CONVERGED = "converged"
    FAILED = "failed"


class ClosureStatus(StrEnum):
    NOT_CHECKED = "not_checked"
    PASSED = "passed"
    FAILED = "failed"
