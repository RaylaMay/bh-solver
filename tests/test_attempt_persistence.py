from __future__ import annotations

import json
import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from bh_sim.boundary.contracts import RunAttemptRecord
from bh_sim.boundary.json_codec import boundary_json
from bh_sim.core import (
    CaseDefinition,
    ClosureStatus,
    ConvergenceStatus,
    DraftRevision,
    RunResult,
    SolverResult,
    StableId,
    ValidityStatus,
)
from bh_sim.persistence import PersistenceStore
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
        ValidityStatus.VALID,
        (),
    )


class AttemptPersistenceTests(unittest.TestCase):
    def test_record_attempt_lifecycle_progression(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = PersistenceStore(temp_dir)
            admitted = RunAttemptRecord(
                attempt_id="att:101",
                run_id="run:101",
                case_id="case:1",
                engineering_hash="eng_hash_1",
                context_hash="ctx_hash_1",
                state="ADMITTED",
                admitted_at="2026-09-15T00:00:00Z",
            )
            store.record_attempt(admitted)
            manifest_path = store._attempt_path(admitted.attempt_id)
            self.assertTrue(manifest_path.exists())
            self.assertNotIn(":", manifest_path.name)
            self.assertEqual(len(manifest_path.stem), 64)
            fetched = store.get_attempt("att:101")
            assert fetched is not None
            self.assertEqual(fetched.state, "ADMITTED")
            self.assertFalse(fetched.persisted)

            running = RunAttemptRecord(
                attempt_id="att:101",
                run_id="run:101",
                case_id="case:1",
                engineering_hash="eng_hash_1",
                context_hash="ctx_hash_1",
                state="RUNNING",
                admitted_at="2026-09-15T00:00:00Z",
            )
            store.record_attempt(running)
            fetched = store.get_attempt("att:101")
            assert fetched is not None
            self.assertEqual(fetched.state, "RUNNING")

            completed = RunAttemptRecord(
                attempt_id="att:101",
                run_id="run:101",
                case_id="case:1",
                engineering_hash="eng_hash_1",
                context_hash="ctx_hash_1",
                state="COMPLETED",
                admitted_at="2026-09-15T00:00:00Z",
                terminal_at="2026-09-15T00:01:00Z",
                artifact_hash="art_hash_101",
                persisted=True,
            )
            store.record_attempt(completed)
            fetched = store.get_attempt("att:101")
            assert fetched is not None
            self.assertEqual(fetched.state, "COMPLETED")
            self.assertEqual(fetched.artifact_hash, "art_hash_101")
            self.assertTrue(fetched.persisted)

            attempts = store.list_attempts("case:1")
            self.assertEqual(len(attempts), 1)
            self.assertEqual(attempts[0].attempt_id, "att:101")

    def test_record_attempt_conflict_on_changed_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = PersistenceStore(temp_dir)
            admitted = RunAttemptRecord(
                attempt_id="att:201",
                run_id="run:201",
                case_id="case:1",
                engineering_hash="eng_hash_original",
                context_hash="ctx_hash_1",
                state="ADMITTED",
                admitted_at="2026-09-15T00:00:00Z",
            )
            store.record_attempt(admitted)

            conflicting = RunAttemptRecord(
                attempt_id="att:201",
                run_id="run:201",
                case_id="case:1",
                engineering_hash="eng_hash_CHANGED",
                context_hash="ctx_hash_1",
                state="RUNNING",
                admitted_at="2026-09-15T00:00:00Z",
            )
            with self.assertRaises(ValueError) as ctx:
                store.record_attempt(conflicting)
            self.assertIn("already exists with differing immutable inputs", str(ctx.exception))

    def test_terminal_disposition_immutability(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = PersistenceStore(temp_dir)
            cancelled = RunAttemptRecord(
                attempt_id="att:301",
                run_id="run:301",
                case_id="case:1",
                engineering_hash="eng_hash_1",
                context_hash="ctx_hash_1",
                state="CANCELLED",
                admitted_at="2026-09-15T00:00:00Z",
                terminal_at="2026-09-15T00:00:30Z",
                failure_reason="User cancelled at boundary",
            )
            store.record_attempt(cancelled)

            late_failure = RunAttemptRecord(
                attempt_id="att:301",
                run_id="run:301",
                case_id="case:1",
                engineering_hash="eng_hash_1",
                context_hash="ctx_hash_1",
                state="FAILED",
                admitted_at="2026-09-15T00:00:00Z",
                terminal_at="2026-09-15T00:00:40Z",
                failure_reason="Late failure report",
            )
            store.record_attempt(late_failure)
            fetched = store.get_attempt("att:301")
            assert fetched is not None
            self.assertEqual(fetched.state, "CANCELLED")
            self.assertEqual(fetched.failure_reason, "User cancelled at boundary")

    def test_reconcile_startup_attempts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = PersistenceStore(temp_dir)
            att1 = RunAttemptRecord(
                attempt_id="att:401",
                run_id="run:401",
                case_id="case:1",
                engineering_hash="eng_1",
                context_hash="ctx_1",
                state="ADMITTED",
                admitted_at="2026-09-15T00:00:00Z",
            )
            att2 = RunAttemptRecord(
                attempt_id="att:402",
                run_id="run:402",
                case_id="case:1",
                engineering_hash="eng_2",
                context_hash="ctx_2",
                state="RUNNING",
                admitted_at="2026-09-15T00:01:00Z",
            )
            att3 = RunAttemptRecord(
                attempt_id="att:403",
                run_id="run:403",
                case_id="case:1",
                engineering_hash="eng_3",
                context_hash="ctx_3",
                state="COMPLETED",
                admitted_at="2026-09-15T00:02:00Z",
                terminal_at="2026-09-15T00:03:00Z",
                persisted=True,
            )
            store.record_attempt(att1)
            store.record_attempt(att2)
            store.record_attempt(att3)

            reconciled = store.reconcile_startup_attempts()
            self.assertEqual(len(reconciled), 2)
            reconciled_ids = {r.attempt_id for r in reconciled}
            self.assertEqual(reconciled_ids, {"att:401", "att:402"})

            for att_id in ("att:401", "att:402"):
                record = store.get_attempt(att_id)
                assert record is not None
                self.assertEqual(record.state, "INTERRUPTED")
                self.assertIsNotNone(record.terminal_at)
                assert record.failure_reason is not None
                self.assertIn("interrupted during application restart", record.failure_reason)

            # att3 remains COMPLETED
            record3 = store.get_attempt("att:403")
            assert record3 is not None
            self.assertEqual(record3.state, "COMPLETED")

    def test_rebuild_index_from_canonical_artifacts(self) -> None:
        case = sample_case()
        revision = sample_revision(case)
        run = sample_run(revision)

        with tempfile.TemporaryDirectory() as temp_dir:
            store = PersistenceStore(temp_dir)
            store.save_case(case)
            store.save_revision(revision)
            store.save_run(run)

            # Confirm functional before index loss
            self.assertEqual(store.load_run(run.run_id), run)
            self.assertEqual(store.load_latest_valid_run(case.case_id), run)

            # Simulate complete loss/corruption of SQLite index
            index_path = Path(temp_dir) / "index.sqlite3"
            index_path.unlink()

            # Create fresh store pointing to same data root
            new_store = PersistenceStore(temp_dir)
            # Before rebuild, index is empty
            self.assertIsNone(new_store.load_latest_valid_run(case.case_id))

            # Rebuild index from immutable artifacts
            restored_count = new_store.rebuild_index_from_artifacts()
            self.assertEqual(restored_count, 3)

            # Confirm functional after rebuild
            self.assertEqual(new_store.load_run(run.run_id), run)
            self.assertEqual(new_store.load_latest_valid_run(case.case_id), run)

    def test_manifest_preservation_against_rejected_updates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = PersistenceStore(temp_dir)
            completed = RunAttemptRecord(
                attempt_id="att:501",
                run_id="run:501",
                case_id="case:1",
                engineering_hash="eng_hash_1",
                context_hash="ctx_hash_1",
                state="COMPLETED",
                admitted_at="2026-09-15T00:00:00Z",
                terminal_at="2026-09-15T00:01:00Z",
                artifact_hash="art_hash_501",
                persisted=True,
            )
            store.record_attempt(completed)

            # Late failure report should be ignored
            late_failure = RunAttemptRecord(
                attempt_id="att:501",
                run_id="run:501",
                case_id="case:1",
                engineering_hash="eng_hash_1",
                context_hash="ctx_hash_1",
                state="FAILED",
                admitted_at="2026-09-15T00:00:00Z",
                terminal_at="2026-09-15T00:02:00Z",
                failure_reason="Late failure shouldn't overwrite manifest",
            )
            store.record_attempt(late_failure)

            # Check SQLite
            fetched = store.get_attempt("att:501")
            assert fetched is not None
            self.assertEqual(fetched.state, "COMPLETED")

            # Check manifest file on disk
            manifest_path = store._attempt_path("att:501")
            self.assertTrue(manifest_path.exists())

            with open(manifest_path, encoding="utf-8") as f:
                manifest_data = json.load(f)
            self.assertEqual(manifest_data["state"], "COMPLETED")

            # Now simulate DB loss and rebuild
            (Path(temp_dir) / "index.sqlite3").unlink()
            fresh_store = PersistenceStore(temp_dir)
            fresh_store.rebuild_index_from_artifacts()
            restored = fresh_store.get_attempt("att:501")
            assert restored is not None
            self.assertEqual(restored.state, "COMPLETED")
            self.assertTrue(restored.persisted)

    def test_manifest_preservation_against_conflicting_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = PersistenceStore(temp_dir)
            admitted = RunAttemptRecord(
                attempt_id="att:601",
                run_id="run:601",
                case_id="case:1",
                engineering_hash="eng_hash_initial",
                context_hash="ctx_hash_1",
                state="ADMITTED",
                admitted_at="2026-09-15T00:00:00Z",
            )
            store.record_attempt(admitted)

            conflicting = RunAttemptRecord(
                attempt_id="att:601",
                run_id="run:601",
                case_id="case:1",
                engineering_hash="eng_hash_MODIFIED",
                context_hash="ctx_hash_1",
                state="RUNNING",
                admitted_at="2026-09-15T00:00:00Z",
            )
            with self.assertRaises(ValueError):
                store.record_attempt(conflicting)

            # Manifest on disk must retain original eng_hash
            manifest_path = store._attempt_path("att:601")

            with open(manifest_path, encoding="utf-8") as f:
                manifest_data = json.load(f)
            self.assertEqual(manifest_data["engineering_hash"], "eng_hash_initial")
            self.assertEqual(manifest_data["state"], "ADMITTED")

    @unittest.skipIf(os.name == "nt", "Windows cannot create the legacy colon filename")
    def test_legacy_raw_id_manifest_remains_readable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = PersistenceStore(temp_dir)
            legacy = RunAttemptRecord(
                attempt_id="att:legacy",
                run_id="run:legacy",
                case_id="case:1",
                engineering_hash="eng_hash_legacy",
                context_hash="ctx_hash_legacy",
                state="COMPLETED",
                admitted_at="2026-09-15T00:00:00Z",
                terminal_at="2026-09-15T00:01:00Z",
                persisted=True,
            )
            store._legacy_attempt_path(legacy.attempt_id).write_text(
                boundary_json(legacy), encoding="utf-8"
            )

            self.assertEqual(store.get_attempt(legacy.attempt_id), legacy)
            self.assertEqual(store.list_attempts(), (legacy,))
            self.assertEqual(store.rebuild_index_from_artifacts(), 0)
            self.assertEqual(store.index.get_attempt(legacy.attempt_id), legacy)

    def test_windows_reads_supported_legacy_filename_before_terminal_update(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = PersistenceStore(temp_dir)
            cancelled = RunAttemptRecord(
                attempt_id="att-legacy",
                run_id="run-legacy",
                case_id="case-1",
                engineering_hash="eng_hash_legacy",
                context_hash="ctx_hash_legacy",
                state="CANCELLED",
                admitted_at="2026-09-15T00:00:00Z",
                terminal_at="2026-09-15T00:01:00Z",
                failure_reason="cancelled before migration",
            )
            store._legacy_attempt_path(cancelled.attempt_id).write_text(
                boundary_json(cancelled), encoding="utf-8"
            )
            late_completion = replace(
                cancelled,
                state="COMPLETED",
                artifact_hash="a" * 64,
                persisted=True,
            )

            with patch("bh_sim.persistence.store.os.name", "nt"):
                self.assertEqual(store.get_attempt(cancelled.attempt_id), cancelled)
                self.assertEqual(store.record_attempt(late_completion), cancelled)

            self.assertFalse(store._attempt_path(cancelled.attempt_id).exists())
