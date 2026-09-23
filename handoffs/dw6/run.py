"""Run an externally pinned acceptance suite against explicit candidate source.

This is a verification runner, not an OS security sandbox. It ignores candidate
pytest configuration/conftest/plugins and fails closed on altered/incomplete tests.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent
BOOTSTRAP = """
import importlib, os, sys
from pathlib import Path
candidate, package, report, mode = sys.argv[1:]
sys.path[:0] = [package, str(Path(candidate) / 'src')]
os.environ['DW6_GATE_REPORT'] = report
import bh_sim
source_root = (Path(candidate) / 'src').resolve()
assert Path(bh_sim.__file__).resolve().is_relative_to(source_root), 'Wrong bh_sim imported'
import pytest
args = [str(Path(package) / 'tests'), '-c', str(Path(package) / 'pytest.ini'),
        '--rootdir=' + package, '--confcutdir=' + package, '--import-mode=importlib',
        '-p', 'gate_plugin', '-p', 'no:cacheprovider', '-q', '--tb=short']
if mode == 'collect':
    args += ['--collect-only']
raise SystemExit(pytest.main(args))
"""


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package_files(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): file_hash(p)
        for p in sorted(root.rglob("*"))
        if p.is_file()
        and p != root / "manifest.json"
        and "__pycache__" not in p.parts
        and p.suffix != ".pyc"
    }


def verify_package(root: Path, trust_anchor: str) -> dict:
    manifest_path = root / "manifest.json"
    if file_hash(manifest_path) != trust_anchor:
        raise ValueError("Manifest differs from the reviewer-supplied SHA-256")
    manifest = json.loads(manifest_path.read_text())
    if manifest["schema_version"] != "bh-dw6-acceptance-manifest-v1":
        raise ValueError("Unsupported acceptance manifest version")
    if package_files(root) != manifest["files_sha256"]:
        raise ValueError("Package file inventory/hash mismatch (including unexpected files)")
    expected = manifest["required_nodeids"]
    if not expected or len(expected) != len(set(expected)):
        raise ValueError("Manifest has an empty or duplicate test inventory")
    return manifest


def assess(report: dict, expected: list[str], process_exit: int) -> list[str]:
    reasons = []
    if process_exit != 0 or report.get("pytest_exit") != 0:
        reasons.append("pytest/process did not complete successfully")
    if sorted(report.get("collected", [])) != sorted(expected):
        reasons.append("mandatory collection differs from the frozen inventory")
    if report.get("collection_errors"):
        reasons.append("collection errors occurred")
    if set(report.get("outcomes", {})) != set(expected):
        reasons.append("mandatory test outcomes are incomplete or unexpected")
    if any(report.get("outcomes", {}).get(name) != "passed" for name in expected):
        reasons.append("mandatory tests failed, skipped, xfailed, or did not execute")
    return reasons


def source_identity(candidate: Path) -> dict:
    """Hash executable inputs, including untracked source; omit runtime/user data."""
    files = []
    for family in ("src", "tests", "tools", ".github/workflows"):
        base = candidate / family
        if base.exists():
            files.extend(
                p
                for p in base.rglob("*")
                if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
            )
    files.extend(
        candidate / name for name in ("pyproject.toml", "uv.lock") if (candidate / name).is_file()
    )
    hashes = {p.relative_to(candidate).as_posix(): file_hash(p) for p in sorted(files)}
    result = {
        "files_sha256": hashes,
        "tree_sha256": hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest(),
    }
    for key, args in (("commit", ["rev-parse", "HEAD"]), ("branch", ["branch", "--show-current"])):
        proc = subprocess.run(["git", "-C", str(candidate), *args], capture_output=True, text=True)
        result[key] = proc.stdout.strip() if proc.returncode == 0 else None
    return result


def invoke(candidate: Path, package: Path, report: Path, *, collect=False, timeout=900):
    env = {
        k: v
        for k, v in os.environ.items()
        if k in {"PATH", "HOME", "TMPDIR", "TMP", "TEMP", "SYSTEMROOT", "WINDIR", "LANG", "LC_ALL"}
    }
    env.update(
        {
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "QT_QPA_PLATFORM": "offscreen",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    return subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            BOOTSTRAP,
            str(candidate),
            str(package),
            str(report),
            "collect" if collect else "run",
        ],
        cwd=package,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--manifest-sha256",
        required=True,
        help="Obtain from the reviewer outside the candidate/package",
    )
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()
    candidate, output = args.candidate.resolve(), args.output.resolve()
    if output.exists() and any(output.iterdir()):
        parser.error("Output must be a new or empty directory; preserve earlier evidence")
    output.mkdir(parents=True, exist_ok=True)
    try:
        manifest = verify_package(PACKAGE, args.manifest_sha256)
    except (ValueError, OSError, KeyError) as error:
        (output / "gate.json").write_text(
            json.dumps({"accepted": False, "reason": str(error)}) + "\n"
        )
        print("REJECTED:", error)
        return 2
    before = source_identity(candidate)
    (output / "candidate.json").write_text(json.dumps(before, indent=2, sort_keys=True) + "\n")
    try:
        process = invoke(candidate, PACKAGE, output / "pytest.json", timeout=args.timeout)
        log = process.stdout + process.stderr
        for path, token in (
            (candidate, "<candidate>"),
            (PACKAGE, "<package>"),
            (output, "<evidence>"),
        ):
            log = log.replace(str(path), token)
        # Private machine directory prefixes do not belong in portable evidence.
        log = log.replace(str(Path.home()), "<home>")
        (output / "pytest.log").write_text(log, encoding="utf-8")
        report_path = output / "pytest.json"
        report = json.loads(report_path.read_text()) if report_path.exists() else {}
        reasons = assess(report, manifest["required_nodeids"], process.returncode)
    except subprocess.TimeoutExpired:
        report, reasons = {}, ["acceptance process timed out; incomplete evidence"]
    if source_identity(candidate) != before:
        reasons.append("candidate executable inputs changed during verification")
    try:
        verify_package(PACKAGE, args.manifest_sha256)
    except (ValueError, OSError, KeyError) as error:
        reasons.append(str(error))
    counts = {
        name: list(report.get("outcomes", {}).values()).count(name)
        for name in ("passed", "failed", "skipped", "xfail-or-xpass")
    }
    result = {
        "schema_version": "bh-dw6-gate-result-v1",
        "accepted": not reasons,
        "reasons": reasons,
        "counts": counts,
        "required_tests": len(manifest["required_nodeids"]),
        "manifest_sha256": args.manifest_sha256,
        "candidate_tree_sha256": before["tree_sha256"],
        "python": platform.python_version(),
        "platform": platform.system() + "/" + platform.machine(),
        "note": "Software suite only; native/provider witness and review remain separate gates.",
    }
    (output / "gate.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
