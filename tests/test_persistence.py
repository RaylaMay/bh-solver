from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from bh_sim.core import (
    CaseDefinition,
    ClosureStatus,
    CompiledFlowsheet,
    ConvergenceStatus,
    DraftRevision,
    RunResult,
    SolverResult,
    StableId,
    ValidityStatus,
)
from bh_sim.persistence import (
    ArtifactStore,
    PersistenceStore,
    canonical_json,
    contract_digest,
    contract_from_json,
    read_contract,
    write_contract,
)
from tests.test_contracts import sample_case


def sample_revision(case: CaseDefinition) -> DraftRevision:
    return DraftRevision(
        StableId("revision:r1"),
        case.case_id,
        1,
        case,
        (),
        "2026-08-27T00:00:00Z",
    )


def sample_run(revision: DraftRevision) -> RunResult:
    solver = SolverResult(ConvergenceStatus.CONVERGED, (), (), (), "No free variables")
    return RunResult(
        StableId("run:one"),
        revision.case.case_id,
        revision.revision_id,
        StableId("compiled:one"),
        "2026-08-27T00:01:00Z",
        (),
        (),
        solver,
        ConvergenceStatus.CONVERGED,
        ClosureStatus.PASSED,
        ValidityStatus.VALID,
        ValidityStatus.EXTRAPOLATED,
        (),
    )


class JsonCodecTests(unittest.TestCase):
    def test_case_round_trip_is_exact_and_canonical(self) -> None:
        case = sample_case()
        encoded = canonical_json(case)
        self.assertEqual(contract_from_json(encoded), case)
        self.assertEqual(canonical_json(contract_from_json(encoded)), encoded)
        self.assertEqual(encoded, canonical_json(case))
        self.assertEqual(json.loads(encoded)["schema_version"], "v1alpha")

    def test_all_four_state_forms_round_trip(self) -> None:
        case = sample_case()
        revision = sample_revision(case)
        compiled = CompiledFlowsheet(
            StableId("compiled:one"), case.case_id, revision.revision_id, "a" * 64, (), (), 0, ()
        )
        run = sample_run(revision)
        for value in (case, revision, compiled, run):
            with self.subTest(contract=type(value).__name__):
                self.assertEqual(contract_from_json(canonical_json(value)), value)

    def test_digest_changes_with_engineering_content(self) -> None:
        case = sample_case()
        changed = CaseDefinition(
            case.case_id,
            "Changed title",
            case.materials,
            case.property_packages,
            case.units,
            case.connections,
            case.specifications,
        )
        self.assertNotEqual(contract_digest(case), contract_digest(changed))

    def test_file_helpers_round_trip(self) -> None:
        case = sample_case()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "case.json"
            write_contract(path, case)
            self.assertEqual(read_contract(path), case)

    def test_unknown_or_extra_contract_fields_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            contract_from_json('{"$type":"Unknown"}')
        payload = json.loads(canonical_json(sample_case()))
        payload["unexpected"] = 1
        with self.assertRaises(ValueError):
            contract_from_json(json.dumps(payload))


class StoreTests(unittest.TestCase):
    def test_artifacts_are_content_addressed_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ArtifactStore(directory)
            first = store.put(sample_case())
            second = store.put(sample_case())
            self.assertEqual(first, second)
            self.assertEqual(first.path.name, f"{first.digest}.json")
            self.assertEqual(store.get(first.digest), sample_case())

    def test_artifact_corruption_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ArtifactStore(directory)
            record = store.put(sample_case())
            record.path.write_text(canonical_json(sample_case()).replace("Radiator", "Damaged"))
            with self.assertRaises(RuntimeError):
                store.get(record.digest)

    def test_repository_indexes_and_loads_immutable_run(self) -> None:
        case = sample_case()
        revision = sample_revision(case)
        run = sample_run(revision)
        with tempfile.TemporaryDirectory() as directory:
            store = PersistenceStore(directory)
            store.save_case(case)
            store.save_revision(revision)
            run_record = store.save_run(run)
            self.assertEqual(store.load_run(run.run_id), run)
            self.assertEqual(
                store.index.list_runs(str(case.case_id)),
                ((str(run.run_id), run.created_at, "converged"),),
            )
            with closing(sqlite3.connect(Path(directory) / "index.sqlite3")) as connection:
                indexed = connection.execute(
                    "SELECT artifact_hash FROM runs WHERE run_id = ?", (str(run.run_id),)
                ).fetchone()
            self.assertEqual(indexed, (run_record.digest,))

    def test_revision_save_is_idempotent_but_rejects_changed_content(self) -> None:
        case = sample_case()
        revision = sample_revision(case)
        with tempfile.TemporaryDirectory() as directory:
            store = PersistenceStore(directory)
            store.save_case(case)
            first = store.save_revision(revision)
            self.assertEqual(store.save_revision(revision), first)
            with self.assertRaisesRegex(ValueError, "immutable revision ID"):
                store.save_revision(
                    DraftRevision(
                        revision.revision_id,
                        revision.base_case_id,
                        revision.revision_number,
                        CaseDefinition(
                            case.case_id,
                            "Changed draft",
                            case.materials,
                            case.property_packages,
                            case.units,
                            case.connections,
                            case.specifications,
                        ),
                        revision.changes,
                        revision.created_at,
                    )
                )

    def test_failed_save_does_not_replace_existing_run(self) -> None:
        case = sample_case()
        revision = sample_revision(case)
        run = sample_run(revision)
        with tempfile.TemporaryDirectory() as directory:
            store = PersistenceStore(directory)
            store.save_case(case)
            store.save_revision(revision)
            original = store.save_run(run)
            changed = RunResult(
                run.run_id,
                run.case_id,
                run.revision_id,
                run.compiled_id,
                run.created_at,
                (),
                (),
                SolverResult(ConvergenceStatus.FAILED, (), (), (), "failed"),
                ConvergenceStatus.FAILED,
                ClosureStatus.NOT_CHECKED,
                ValidityStatus.UNKNOWN,
                ValidityStatus.UNKNOWN,
                (),
            )
            with self.assertRaises(sqlite3.IntegrityError):
                store.save_run(changed)
            self.assertEqual(store.load_run(run.run_id), run)
            self.assertTrue(original.path.exists())

    def test_failed_run_does_not_advance_last_valid_pointer(self) -> None:
        case = sample_case()
        revision = sample_revision(case)
        valid = sample_run(revision)
        failed = RunResult(
            StableId("run:failed"),
            valid.case_id,
            valid.revision_id,
            valid.compiled_id,
            "2026-08-27T00:02:00Z",
            (),
            (),
            SolverResult(ConvergenceStatus.FAILED, (), (), (), "failed"),
            ConvergenceStatus.FAILED,
            ClosureStatus.NOT_CHECKED,
            ValidityStatus.UNKNOWN,
            ValidityStatus.UNKNOWN,
            (),
        )
        with tempfile.TemporaryDirectory() as directory:
            store = PersistenceStore(directory)
            store.save_case(case)
            store.save_revision(revision)
            store.save_run(valid)
            store.save_run(failed)
            self.assertEqual(store.load_latest_valid_run(case.case_id), valid)

    def test_approved_case_index_is_not_overwritten_by_same_id(self) -> None:
        case = sample_case()
        changed = CaseDefinition(
            case.case_id,
            "Unapproved edit",
            case.materials,
            case.property_packages,
            case.units,
            case.connections,
            case.specifications,
        )
        with tempfile.TemporaryDirectory() as directory:
            store = PersistenceStore(directory)
            original = store.save_case(case)
            store.save_case(changed)
            self.assertEqual(store.index.artifact_hash_for_case(str(case.case_id)), original.digest)


if __name__ == "__main__":
    unittest.main()
