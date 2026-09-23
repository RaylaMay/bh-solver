"""Content-addressed artifacts with a replaceable SQLite metadata index."""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from bh_sim.boundary.contracts import RunAttemptRecord
from bh_sim.boundary.file_names import identifier_json_filename, is_windows_safe_filename
from bh_sim.boundary.json_codec import boundary_from_json, boundary_json
from bh_sim.core import CaseDefinition, DraftRevision, RunResult, StableId

from .json_codec import canonical_json, contract_digest, contract_from_json

_TERMINAL_ATTEMPT_STATES = frozenset(
    ("COMPLETED", "FAILED", "CANCELLED", "INTERRUPTED", "TIMED_OUT")
)


def _attempt_winner(
    existing: RunAttemptRecord | None, proposed: RunAttemptRecord
) -> RunAttemptRecord:
    """Keep immutable admission identity and the first terminal disposition."""
    if existing is None:
        return proposed
    identity_fields = (
        "attempt_id",
        "run_id",
        "case_id",
        "engineering_hash",
        "context_hash",
        "admitted_at",
        "protocol_version",
    )
    if any(getattr(existing, key) != getattr(proposed, key) for key in identity_fields):
        raise ValueError(
            f"Attempt ID {proposed.attempt_id} already exists with differing immutable inputs"
        )
    if existing.state in _TERMINAL_ATTEMPT_STATES:
        return existing
    if existing.state == "RUNNING" and proposed.state == "ADMITTED":
        return existing
    return proposed


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
                CREATE TABLE IF NOT EXISTS attempts (
                    attempt_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    engineering_hash TEXT NOT NULL,
                    context_hash TEXT NOT NULL,
                    state TEXT NOT NULL,
                    admitted_at TEXT NOT NULL,
                    terminal_at TEXT,
                    failure_reason TEXT,
                    artifact_hash TEXT,
                    persisted INTEGER NOT NULL DEFAULT 0,
                    protocol_version TEXT NOT NULL
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
                     AND NOT EXISTS (
                       SELECT 1 FROM attempts WHERE attempts.run_id = runs.run_id
                         AND (attempts.state != 'COMPLETED' OR attempts.persisted = 0)
                     )
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

    def index_attempt(
        self,
        attempt: RunAttemptRecord,
        *,
        publish: Callable[[RunAttemptRecord | None], RunAttemptRecord] | None = None,
    ) -> tuple[RunAttemptRecord, bool]:
        """Serialize writers; publish canonical JSON before updating this cache.

        The publisher resolves against durable JSON, including a previous write
        whose index commit failed. Holding SQLite's write reservation also
        serializes independent store instances without making SQLite authoritative.
        """
        with self._session() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """SELECT attempt_id, run_id, case_id, engineering_hash, context_hash,
                          state, admitted_at, terminal_at, failure_reason, artifact_hash,
                          persisted, protocol_version
                   FROM attempts WHERE attempt_id = ?""",
                (attempt.attempt_id,),
            ).fetchone()
            existing = (
                None
                if row is None
                else RunAttemptRecord(*row[:10], persisted=bool(row[10]), protocol_version=row[11])
            )
            winner = publish(existing) if publish else _attempt_winner(existing, attempt)
            connection.execute(
                """INSERT INTO attempts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(attempt_id) DO UPDATE SET
                     state = excluded.state, terminal_at = excluded.terminal_at,
                     failure_reason = excluded.failure_reason,
                     artifact_hash = excluded.artifact_hash, persisted = excluded.persisted""",
                (
                    winner.attempt_id,
                    winner.run_id,
                    winner.case_id,
                    winner.engineering_hash,
                    winner.context_hash,
                    winner.state,
                    winner.admitted_at,
                    winner.terminal_at,
                    winner.failure_reason,
                    winner.artifact_hash,
                    int(winner.persisted),
                    winner.protocol_version,
                ),
            )
            return winner, winner != existing

    def get_attempt(self, attempt_id: str) -> RunAttemptRecord | None:
        with self._session() as connection:
            row = connection.execute(
                """SELECT attempt_id, run_id, case_id, engineering_hash, context_hash,
                          state, admitted_at, terminal_at, failure_reason, artifact_hash,
                          persisted, protocol_version
                   FROM attempts WHERE attempt_id = ?""",
                (attempt_id,),
            ).fetchone()
        if row is None:
            return None
        return RunAttemptRecord(
            attempt_id=row[0],
            run_id=row[1],
            case_id=row[2],
            engineering_hash=row[3],
            context_hash=row[4],
            state=row[5],
            admitted_at=row[6],
            terminal_at=row[7],
            failure_reason=row[8],
            artifact_hash=row[9],
            persisted=bool(row[10]),
            protocol_version=row[11],
        )

    def list_attempts(self, case_id: str | None = None) -> tuple[RunAttemptRecord, ...]:
        query = """SELECT attempt_id, run_id, case_id, engineering_hash, context_hash,
                          state, admitted_at, terminal_at, failure_reason, artifact_hash,
                          persisted, protocol_version
                   FROM attempts"""
        params: tuple[str, ...] = ()
        if case_id is not None:
            alt_case_id = case_id[5:] if case_id.startswith("case:") else f"case:{case_id}"
            query += " WHERE (case_id = ? OR case_id = ?)"
            params = (case_id, alt_case_id)
        query += " ORDER BY admitted_at ASC, attempt_id ASC"
        with self._session() as connection:
            rows = connection.execute(query, params).fetchall()
        return tuple(
            RunAttemptRecord(
                attempt_id=row[0],
                run_id=row[1],
                case_id=row[2],
                engineering_hash=row[3],
                context_hash=row[4],
                state=row[5],
                admitted_at=row[6],
                terminal_at=row[7],
                failure_reason=row[8],
                artifact_hash=row[9],
                persisted=bool(row[10]),
                protocol_version=row[11],
            )
            for row in rows
        )

    def reconcile_startup_attempts(self) -> tuple[RunAttemptRecord, ...]:
        """Mark unclosed (ADMITTED or RUNNING) attempts as INTERRUPTED on supervisor startup."""
        with self._session() as connection:
            rows = connection.execute(
                "SELECT attempt_id FROM attempts WHERE state IN ('ADMITTED', 'RUNNING')"
            ).fetchall()
            if not rows:
                return ()
            reconciled_time = datetime.now(UTC).isoformat()
            fail_msg = "Process interrupted during application restart/loss of supervisor"
            connection.execute(
                """UPDATE attempts
                   SET state = 'INTERRUPTED',
                       terminal_at = ?,
                       failure_reason = ?
                   WHERE state IN ('ADMITTED', 'RUNNING')""",
                (reconciled_time, fail_msg),
            )
        reconciled = []
        for (attempt_id,) in rows:
            record = self.get_attempt(attempt_id)
            if record is not None:
                reconciled.append(record)
        return tuple(reconciled)


class PersistenceStore:
    """Coordinates immutable artifacts and the disposable lookup index."""

    def __init__(self, root: str | Path) -> None:
        root_path = Path(root)
        root_path.mkdir(parents=True, exist_ok=True)
        self.root = root_path
        self.artifacts = ArtifactStore(root_path / "artifacts")
        self.attempts_dir = root_path / "attempts"
        self.attempts_dir.mkdir(parents=True, exist_ok=True)
        self.index = RunIndex(root_path / "index.sqlite3")

    def _attempt_path(self, attempt_id: str) -> Path:
        """Map a validated wire ID to a portable adapter-private filename."""
        self._validate_attempt_id(attempt_id)
        return self.attempts_dir / identifier_json_filename(attempt_id)

    def _legacy_attempt_path(self, attempt_id: str) -> Path:
        """Return the pre-portability raw-ID path for backward-compatible reads."""
        self._validate_attempt_id(attempt_id)
        return self.attempts_dir / f"{attempt_id}.json"

    @staticmethod
    def _validate_attempt_id(attempt_id: str) -> None:
        if (
            not attempt_id
            or any(
                char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.:-"
                for char in attempt_id
            )
            or attempt_id in (".", "..")
        ):
            raise ValueError("Invalid attempt identifier")

    def _read_attempt_path(self, path: Path, expected_id: str | None = None) -> RunAttemptRecord:
        value = boundary_from_json(path.read_text(encoding="utf-8"))
        if not isinstance(value, RunAttemptRecord):
            raise TypeError(f"Attempt manifest {path.name} is not a RunAttemptRecord")
        if expected_id is not None and value.attempt_id != expected_id:
            raise ValueError("Attempt manifest identity mismatch")
        valid_names = {
            self._attempt_path(value.attempt_id).name,
            self._legacy_attempt_path(value.attempt_id).name,
        }
        if path.name not in valid_names:
            raise ValueError("Attempt manifest filename does not match its identity")
        return value

    def _read_attempt_manifest(self, attempt_id: str) -> RunAttemptRecord | None:
        winner: RunAttemptRecord | None = None
        paths = [self._attempt_path(attempt_id)]
        legacy_path = self._legacy_attempt_path(attempt_id)
        if os.name != "nt" or is_windows_safe_filename(legacy_path.name):
            paths.append(legacy_path)
        for path in dict.fromkeys(paths):
            if path.exists():
                winner = _attempt_winner(
                    winner, self._read_attempt_path(path, expected_id=attempt_id)
                )
        return winner

    def _write_attempt_manifest(self, attempt: RunAttemptRecord) -> None:
        """Publish a flushed sibling file atomically; leave the old winner on failure."""
        target = self._attempt_path(attempt.attempt_id)
        temporary_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.attempts_dir, delete=False
            ) as temporary:
                temporary_name = temporary.name
                temporary.write(boundary_json(attempt))
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_name, target)
        finally:
            if temporary_name is not None:
                Path(temporary_name).unlink(missing_ok=True)

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

    def load_case(self, case_id: StableId | str) -> CaseDefinition | None:
        digest = self.index.artifact_hash_for_case(str(case_id))
        if digest is None:
            return None
        value = self.artifacts.get(digest)
        if not isinstance(value, CaseDefinition):
            raise TypeError("case index does not point to a CaseDefinition")
        return value

    def load_revision(self, revision_id: StableId | str) -> DraftRevision | None:
        digest = self.index.artifact_hash_for_revision(str(revision_id))
        if digest is None:
            return None
        value = self.artifacts.get(digest)
        if not isinstance(value, DraftRevision):
            raise TypeError("revision index does not point to a DraftRevision")
        return value

    def list_runs(self, case_id: StableId | str) -> tuple[tuple[str, str, str], ...]:
        return self.index.list_runs(str(case_id))

    def record_attempt(self, attempt: RunAttemptRecord) -> RunAttemptRecord:
        """Resolve/publish the durable winner before updating the disposable index."""

        def publish(indexed: RunAttemptRecord | None) -> RunAttemptRecord:
            durable = self._read_attempt_manifest(attempt.attempt_id)
            winner = _attempt_winner(durable if durable is not None else indexed, attempt)
            if durable != winner:
                self._write_attempt_manifest(winner)
            return winner

        winner, _ = self.index.index_attempt(attempt, publish=publish)
        return winner

    def get_attempt(self, attempt_id: str) -> RunAttemptRecord | None:
        return self._read_attempt_manifest(attempt_id) or self.index.get_attempt(attempt_id)

    def list_attempts(self, case_id: str | None = None) -> tuple[RunAttemptRecord, ...]:
        records = {item.attempt_id: item for item in self.index.list_attempts()}
        manifests: dict[str, RunAttemptRecord] = {}
        for path in self.attempts_dir.glob("*.json"):
            item = self._read_attempt_path(path)
            manifests[item.attempt_id] = _attempt_winner(manifests.get(item.attempt_id), item)
        records.update(manifests)
        case_ids = (
            None
            if case_id is None
            else {case_id, case_id[5:] if case_id.startswith("case:") else f"case:{case_id}"}
        )
        return tuple(
            sorted(
                (item for item in records.values() if case_ids is None or item.case_id in case_ids),
                key=lambda item: (item.admitted_at, item.attempt_id),
            )
        )

    def reconcile_startup_attempts(self) -> tuple[RunAttemptRecord, ...]:
        """Close abandoned attempts through the same JSON-first publication path."""
        return tuple(
            self.record_attempt(
                replace(
                    item,
                    state="INTERRUPTED",
                    terminal_at=datetime.now(UTC).isoformat(),
                    failure_reason=(
                        "Process interrupted during application restart/loss of supervisor"
                    ),
                )
            )
            for item in self.list_attempts()
            if item.state in ("ADMITTED", "RUNNING")
        )

    def rebuild_index_from_artifacts(self) -> int:
        """Rebuild disposable SQLite lookup index from verified canonical JSON files."""
        cases: list[tuple[CaseDefinition, str]] = []
        revisions: list[tuple[DraftRevision, str]] = []
        runs: list[tuple[RunResult, str]] = []

        for path in sorted(self.artifacts.root.glob("*/*.json")):
            digest = path.stem
            data = path.read_text(encoding="utf-8")
            value = contract_from_json(data)
            if contract_digest(value) != digest:
                raise RuntimeError(f"artifact integrity check failed during rebuild: {digest}")
            if isinstance(value, CaseDefinition):
                cases.append((value, digest))
            elif isinstance(value, DraftRevision):
                revisions.append((value, digest))
            elif isinstance(value, RunResult):
                runs.append((value, digest))

        for case, digest in cases:
            self.index.index_case(case, digest)
        for revision, digest in revisions:
            self.index.index_revision(revision, digest)
        for run, digest in runs:
            self.index.index_run(run, digest)

        attempts: dict[str, RunAttemptRecord] = {}
        for path in sorted(self.attempts_dir.glob("*.json")):
            try:
                attempt = self._read_attempt_path(path)
                attempts[attempt.attempt_id] = _attempt_winner(
                    attempts.get(attempt.attempt_id), attempt
                )
            except Exception as exc:
                sys.stderr.write(
                    f"Recovery warning: failed to index attempt manifest {path}: {exc}\n"
                )

        for attempt in attempts.values():
            self.index.index_attempt(attempt)

        return len(cases) + len(revisions) + len(runs)
