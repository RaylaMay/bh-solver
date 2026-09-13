"""Existing browser draft persistence format plus immutable scientific repository ports.

DW1 retains legacy normalization, revision naming and write semantics. Atomic
browser saves, recovery and admission manifests remain explicit DW4 work.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from bh_sim.boundary.contracts import (
    CalculatedRunDto,
    PreparedRevisionDto,
    RunViewDto,
)
from bh_sim.core import RunResult
from bh_sim.core.json_codec import contract_from_json
from bh_sim.persistence import PersistenceStore

from .drafts import DraftRepository as DraftRepository
from .drafts import DraftRepositoryAdapter as DraftRepositoryAdapter
from .engineering import read_prepared_revision, run_to_view

_P = ParamSpec("_P")
_R = TypeVar("_R")


def _sanitize_index_failure(method: Callable[_P, _R]) -> Callable[_P, _R]:
    """Translate SQLite details into the neutral runtime port-failure category."""

    @wraps(method)
    def wrapped(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        try:
            return method(*args, **kwargs)
        except sqlite3.Error as error:
            raise RuntimeError("artifact index operation failed") from error

    return wrapped


class ArtifactRepositoryAdapter:
    """Scientific JSON reconstruction and immutable persistence behind a port."""

    def __init__(self, store: PersistenceStore) -> None:
        self.store = store

    @_sanitize_index_failure
    def save_inputs(self, prepared: PreparedRevisionDto) -> None:
        revision = read_prepared_revision(prepared)
        self.store.save_case(revision.case)
        self.store.save_revision(revision)

    @_sanitize_index_failure
    def save_run(self, result: CalculatedRunDto) -> None:
        run = contract_from_json(result.canonical_json)
        if not isinstance(run, RunResult):
            raise TypeError("calculated artifact is not RunResult")
        if run_to_view(run) != result.view:
            raise ValueError("run view does not match canonical artifact")
        self.store.save_run(run)

    @_sanitize_index_failure
    def load_run(self, run_id: str) -> RunViewDto:
        return run_to_view(self.store.load_run(run_id))

    @_sanitize_index_failure
    def latest_valid_run(self, case_id: str) -> RunViewDto | None:
        result = self.store.load_latest_valid_run(case_id)
        return run_to_view(result) if result is not None else None
