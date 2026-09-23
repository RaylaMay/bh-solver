"""Reviewer-only freeze operation; never run to bless a changed developer submission."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from run import PACKAGE, file_hash, invoke, package_files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as temp:
        report = Path(temp) / "collection.json"
        process = invoke(args.candidate.resolve(), PACKAGE, report, collect=True, timeout=60)
        if process.returncode:
            raise SystemExit(process.stdout + process.stderr)
        result = json.loads(report.read_text())
        if not result["collected"] or result["collection_errors"]:
            raise SystemExit("Cannot freeze incomplete/empty collection")
    manifest = {
        "schema_version": "bh-dw6-acceptance-manifest-v1",
        "revision": args.revision,
        "required_nodeids": result["collected"],
        "files_sha256": package_files(PACKAGE),
        "scope": "Reviewer-controlled DW6 software acceptance; witness/review are separate.",
    }
    path = PACKAGE / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"Frozen {len(result['collected'])} tests; manifest SHA-256: {file_hash(path)}")


if __name__ == "__main__":
    main()
