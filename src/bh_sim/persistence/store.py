"""Content-addressed artifacts with a replaceable SQLite metadata index."""

from __future__ import annotations

import os
import sqlite3
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from bh_sim.core import CaseDefinition, DraftRevision, RunResult, StableId

from .json_codec import canonical_json, contract_digest, contract_from_json


@dataclass(frozen=True)
class ArtifactRecord:
    digest: str
    path: Path
    size_bytes: int


class ArtifactStore:
    """Immutable SHA-256-addressed JSON files.

    A temporary file is hard-linked into its final hash-derived name.  Linking
    is atomic and cannot overwrite an existing artifact.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, digest: str) -> Path:
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise ValueError("artifact digest must be a lowercase SHA-256 digest")
        return self.root / digest[:2] / f"{digest}.json"

    def put(self, value: object) -> ArtifactRecord:
        encoded = (canonical_json(value) + "\n").encode("utf-8")
        digest = contract_digest(value)
        destination = self.path_for(digest)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=destination.parent, delete=False
            ) as temporary:
                temporary.write(encoded)
                temporary.flush()
                os.fsync(temporary.fileno())
                temporary_name = temporary.name
            try:
                os.link(temporary_name, destination)
            except FileExistsError as error:
                if destination.read_bytes() != encoded:
                    raise RuntimeError("content-address collision or corrupted artifact") from error
        finally:
            if temporary_name is not None:
                Path(temporary_name).unlink(missing_ok=True)
        return ArtifactRecord(digest, destination, len(encoded))

    def get(self, digest: str) -> object:
        path = self.path_for(digest)
        data = path.read_text(encoding="utf-8")
        value = contract_from_json(data)
        if contract_digest(value) != digest:
            raise RuntimeError(f"artifact integrity check failed: {digest}")
        return value


class RunIndex:
    """SQLite lookup index; canonical artifacts remain the source of truth."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def _session(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._session() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS cases (
                    case_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    artifact_hash TEXT NOT NULL,
                    schema_version TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS revisions (
                    revision_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    revision_number INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    artifact_hash TEXT NOT NULL,
                    UNIQUE(case_id, revision_number),
                    FOREIGN KEY(case_id) REFERENCES cases(case_id)
                );
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    revision_id TEXT,
                    created_at TEXT NOT NULL,
                    artifact_hash TEXT NOT NULL UNIQUE,
                    convergence TEXT NOT NULL,
                    closure TEXT NOT NULL,
                    physical_validity TEXT NOT NULL,
                    correlation_validity TEXT NOT NULL,
                    FOREIGN KEY(case_id) REFERENCES cases(case_id),
                    FOREIGN KEY(revision_id) REFERENCES revisions(revision_id)
                );
                """
            )

    def index_case(self, case: CaseDefinition, artifact_hash: str) -> None:
        with self._session() as connection:
            connection.execute(
                """INSERT INTO cases(case_id, title, artifact_hash, schema_version)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(case_id) DO NOTHING""",
                (str(case.case_id), case.title, artifact_hash, case.schema_version),
            )

    def index_revision(self, revision: DraftRevision, artifact_hash: str) -> None:
        with self._session() as connection:
            connection.execute(
                """INSERT INTO revisions(
                       revision_id, case_id, revision_number, created_at, artifact_hash
                   ) VALUES (?, ?, ?, ?, ?)""",
                (
                    str(revision.revision_id),
                    str(revision.base_case_id),
                    revision.revision_number,
                    revision.created_at,
                    artifact_hash,
                ),
            )

    def index_run(self, result: RunResult, artifact_hash: str) -> None:
        with self._session() as connection:
            connection.execute(
                """INSERT INTO runs(
                       run_id, case_id, revision_id, created_at, artifact_hash,
                       convergence, closure, physical_validity, correlation_validity
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(result.run_id),
                    str(result.case_id),
                    str(result.revision_id) if result.revision_id else None,
                    result.created_at,
                    artifact_hash,
                    result.convergence.value,
                    result.closure.value,
                    result.physical_validity.value,
                    result.correlation_validity.value,
                ),
            )

    def artifact_hash_for_run(self, run_id: str) -> str | None:
        with self._session() as connection:
            row = connection.execute(
                "SELECT artifact_hash FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        return row[0] if row is not None else None

    def artifact_hash_for_case(self, case_id: str) -> str | None:
        with self._session() as connection:
            row = connection.execute(
                "SELECT artifact_hash FROM cases WHERE case_id = ?", (case_id,)
            ).fetchone()
        return row[0] if row is not None else None

    def artifact_hash_for_revision(self, revision_id: str) -> str | None:
        with self._session() as connection:
            row = connection.execute(
                "SELECT artifact_hash FROM revisions WHERE revision_id = ?", (revision_id,)
            ).fetchone()
        return row[0] if row is not None else None

    def latest_valid_artifact_hash(self, case_id: str) -> str | None:
        with self._session() as connection:
            row = connection.execute(
                """SELECT artifact_hash FROM runs
                   WHERE case_id = ?
                     AND convergence = 'converged'
                     AND closure = 'passed'
                     AND physical_validity = 'valid'
                     AND correlation_validity IN ('valid', 'extrapolated')
                   ORDER BY created_at DESC, run_id DESC LIMIT 1""",
                (case_id,),
            ).fetchone()
        return row[0] if row is not None else None

    def list_runs(self, case_id: str) -> tuple[tuple[str, str, str], ...]:
        with self._session() as connection:
            rows = connection.execute(
                """SELECT run_id, created_at, convergence FROM runs
                   WHERE case_id = ? ORDER BY created_at, run_id""",
                (case_id,),
            ).fetchall()
        return tuple((row[0], row[1], row[2]) for row in rows)


class PersistenceStore:
    """Coordinates immutable artifacts and the disposable lookup index."""

    def __init__(self, root: str | Path) -> None:
        root_path = Path(root)
        root_path.mkdir(parents=True, exist_ok=True)
        self.artifacts = ArtifactStore(root_path / "artifacts")
        self.index = RunIndex(root_path / "index.sqlite3")

    def save_case(self, case: CaseDefinition) -> ArtifactRecord:
        record = self.artifacts.put(case)
        self.index.index_case(case, record.digest)
        return record

    def save_revision(self, revision: DraftRevision) -> ArtifactRecord:
        record = self.artifacts.put(revision)
        existing = self.index.artifact_hash_for_revision(str(revision.revision_id))
        if existing is None:
            self.index.index_revision(revision, record.digest)
        elif existing != record.digest:
            raise ValueError("immutable revision ID already refers to different content")
        return record

    def save_run(self, result: RunResult) -> ArtifactRecord:
        record = self.artifacts.put(result)
        self.index.index_run(result, record.digest)
        return record

    def load_run(self, run_id: StableId | str) -> RunResult:
        digest = self.index.artifact_hash_for_run(str(run_id))
        if digest is None:
            raise KeyError(f"unknown run ID: {run_id}")
        value = self.artifacts.get(digest)
        if not isinstance(value, RunResult):
            raise TypeError(f"run index points to {type(value).__name__}, not RunResult")
        return value

    def load_latest_valid_run(self, case_id: StableId | str) -> RunResult | None:
        digest = self.index.latest_valid_artifact_hash(str(case_id))
        if digest is None:
            return None
        value = self.artifacts.get(digest)
        if not isinstance(value, RunResult):
            raise TypeError("last-valid index does not point to a RunResult")
        return value
