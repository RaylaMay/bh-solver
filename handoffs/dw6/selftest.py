"""Challenge the acceptance runner/oracles; this does not implement or verify DW6."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from oracles import approved, audit_valid, budget_within, canonical, digest, unchanged
from run import assess, file_hash, invoke, package_files, verify_package

ROOT = Path(__file__).resolve().parent
CANDIDATE = ROOT.parents[1]


def good_audit():
    record = {
        "schema_version": "bh-ai-audit-v1",
        "session_id": "s:one",
        "sequence": 1,
        "previous_hash": "",
        "kind": "submission",
        "actor_id": "human:reviewer",
        "created_at": "2026-09-16T00:00:00Z",
        "body_json": '{"question":"test"}',
    }
    record["record_hash"] = digest(record)
    text = '{"fixture":true}'
    return {
        "schema_version": "bh-ai-audit-v1",
        "session_id": "s:one",
        "records": [record],
        "artifacts": [
            {
                "artifact_id": "a:one",
                "media_type": "application/json",
                "sha256": hashlib.sha256(text.encode()).hexdigest(),
                "content_utf8": text,
            }
        ],
    }


class OracleChallenges(unittest.TestCase):
    def test_authority_challenge(self):
        approved({"status": "APPROVED", "approved_by": "human:reviewer"})
        for bad in (
            {"status": "PROPOSED", "approved_by": ""},
            {"status": "APPROVED", "approved_by": "ai:participant"},
        ):
            with self.assertRaises(AssertionError):
                approved(bad)

    def test_isolation_challenge(self):
        before = {"head": "old", "last_valid": "run:baseline"}
        unchanged(before, copy.deepcopy(before))
        with self.assertRaises(AssertionError):
            unchanged(before, {**before, "last_valid": "run:exploration"})

    def test_budget_challenge(self):
        limits = {"iterations": 5, "runs": 5, "tool_calls": 20, "tokens": 50_000}
        ledger = {
            "iterations": 5,
            "runs": 5,
            "tool_calls": 20,
            "tokens_used": 49_000,
            "tokens_reserved": 1000,
            "elapsed_seconds": 300,
        }
        budget_within(ledger, limits)
        for name in ("iterations", "runs", "tool_calls", "tokens_reserved"):
            with self.assertRaises(AssertionError):
                budget_within({**ledger, name: ledger[name] + 1}, limits)

    def test_artifact_and_chain_challenge(self):
        export = good_audit()
        audit_valid(export)
        for kind in ("artifact", "record", "gap", "previous"):
            damaged = copy.deepcopy(export)
            if kind == "artifact":
                damaged["artifacts"][0]["content_utf8"] = "fabricated result"
            elif kind == "record":
                damaged["records"][0]["body_json"] = '{"question":"changed"}'
            elif kind == "gap":
                damaged["records"][0]["sequence"] = 2
            else:
                damaged["records"][0]["previous_hash"] = "unrelated"
            with self.assertRaises(AssertionError):
                audit_valid(damaged)

    def test_nonfinite_canonical_data_is_rejected(self):
        with self.assertRaises(ValueError):
            canonical({"value": float("nan")})


class GateChallenges(unittest.TestCase):
    def test_zero_exit_cannot_hide_skip_xfail_or_missing_test(self):
        expected = ["tests/test_x.py::test_one"]
        good = {
            "collected": expected,
            "outcomes": {expected[0]: "passed"},
            "collection_errors": [],
            "pytest_exit": 0,
        }
        self.assertEqual(assess(good, expected, 0), [])
        for status in ("skipped", "xfail-or-xpass", "failed"):
            self.assertTrue(assess({**good, "outcomes": {expected[0]: status}}, expected, 0))
        self.assertTrue(assess({**good, "collected": []}, expected, 0))
        self.assertTrue(assess({**good, "outcomes": {}}, expected, 0))
        self.assertTrue(assess(good, expected, 1))

    def test_manifest_and_suite_tampering_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "test.py"
            source.write_text("assert True\n")
            manifest = {
                "schema_version": "bh-dw6-acceptance-manifest-v1",
                "files_sha256": package_files(root),
                "required_nodeids": ["test.py::one"],
            }
            path = root / "manifest.json"
            path.write_text(json.dumps(manifest))
            anchor = file_hash(path)
            verify_package(root, anchor)
            source.write_text("assert False\n")
            with self.assertRaises(ValueError):
                verify_package(root, anchor)
            source.write_text("assert True\n")
            (root / "injected.py").write_text("# unexpected\n")
            with self.assertRaises(ValueError):
                verify_package(root, anchor)
            (root / "injected.py").unlink()
            manifest["required_nodeids"] = []
            path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                verify_package(root, anchor)

    def test_actual_pytest_skip_and_xfail_are_not_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            package = Path(temp)
            (package / "tests").mkdir()
            shutil.copyfile(ROOT / "gate_plugin.py", package / "gate_plugin.py")
            (package / "pytest.ini").write_text("[pytest]\n")
            (package / "tests/test_probe.py").write_text(
                "import pytest\n"
                "def test_pass(): assert True\n"
                "@pytest.mark.skip(reason='challenge')\n"
                "def test_skip(): pass\n"
                "@pytest.mark.xfail(reason='challenge')\n"
                "def test_xfail(): assert False\n"
            )
            report = package / "report.json"
            process = invoke(CANDIDATE, package, report, timeout=30)
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
            data = json.loads(report.read_text())
            self.assertEqual(
                set(data["outcomes"].values()), {"passed", "skipped", "xfail-or-xpass"}
            )
            self.assertTrue(assess(data, data["collected"], process.returncode))

    def test_candidate_pytest_configuration_cannot_hide_external_tests(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            candidate, package = root / "candidate", root / "package"
            (candidate / "src/bh_sim").mkdir(parents=True)
            (candidate / "src/bh_sim/__init__.py").write_text("")
            (candidate / "pytest.ini").write_text("[pytest]\naddopts = -k never_collect\n")
            (candidate / "conftest.py").write_text(
                "raise RuntimeError('candidate conftest loaded')\n"
            )
            (package / "tests").mkdir(parents=True)
            shutil.copyfile(ROOT / "gate_plugin.py", package / "gate_plugin.py")
            (package / "pytest.ini").write_text("[pytest]\n")
            (package / "tests/test_probe.py").write_text("def test_required(): assert True\n")
            report = package / "report.json"
            process = invoke(candidate, package, report, timeout=30)
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
            data = json.loads(report.read_text())
            self.assertEqual(len(data["collected"]), 1)
            self.assertFalse(assess(data, data["collected"], process.returncode))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, default=CANDIDATE)
    args = parser.parse_args()
    CANDIDATE = args.candidate.resolve()
    unittest.main(argv=[sys_arg for sys_arg in [__file__, "-v"]])
