"""Read-only integrity check for the dated DW1 review package.

Run from the repository root with its Python interpreter. The file inventory
records before/after hashes because this workspace has no initial Git commit.
This check verifies that dated state, local Markdown links, accepted ADR history
and requirement IDs. It does not approve scientific models or future releases.
Later intentional edits require new evidence, not rewriting the DW0 record.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

from check_review import heading_ids

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = Path(__file__).resolve().parent


def main() -> None:
    """Fail on loss of the recorded implementation, preserved files or doc links."""
    inventory = json.loads((EVIDENCE / "dw1-file-inventory.json").read_text())
    errors: list[str] = []
    patch = EVIDENCE / "dw1-changes.patch"
    if hashlib.sha256(patch.read_bytes()).hexdigest() != inventory["patch_sha256"]:
        errors.append("Dated DW1 review patch changed")
    for name, record in inventory["files"].items():
        path = ROOT / name
        if (
            not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != record["after_sha256"]
        ):
            errors.append(f"Dated DW1 file changed or missing: {name}")

    old_evidence = json.loads((EVIDENCE / "baseline.json").read_text())
    decisions = (ROOT / "docs/DECISIONS.md").read_text()
    sections = re.findall(r"^## ADR-\d{3} .*?(?=^## ADR-|\Z)", decisions, re.MULTILINE | re.DOTALL)
    for identifier, expected in old_evidence["accepted_adr_sha256"].items():
        matches = [section for section in sections if section.split()[1] == identifier]
        if (
            len(matches) != 1
            or hashlib.sha256(matches[0].rstrip().encode()).hexdigest() != expected
        ):
            errors.append(f"Accepted ADR history changed: {identifier}")
    if len(sections) != 10 or "ACCEPTED WITH OWNER ANNOTATIONS" not in sections[-1]:
        errors.append("Expected accepted ADR-010 with recorded owner annotations")

    paths = [
        ROOT / "README.md",
        *sorted((ROOT / "docs").rglob("*.md")),
        ROOT / "tests/fixtures/dw1/README.md",
    ]
    links = 0
    for path in paths:
        content = path.read_text()
        if len(re.findall(r"^```", content, re.MULTILINE)) % 2:
            errors.append(f"Unbalanced fences: {path.relative_to(ROOT)}")
        for target in re.findall(r"\[[^\]\n]+\]\(([^)\n]+)\)", content):
            parsed = urlsplit(target.strip("<>"))
            if parsed.scheme:
                continue
            links += 1
            destination = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
            if not destination.exists():
                errors.append(f"Missing link from {path.relative_to(ROOT)}: {target}")
            elif (
                parsed.fragment
                and destination.suffix == ".md"
                and unquote(parsed.fragment) not in heading_ids(destination.read_text())
            ):
                errors.append(f"Missing heading from {path.relative_to(ROOT)}: {target}")

    matrix = (ROOT / "docs/REQUIREMENTS_VERIFICATION.md").read_text()
    identifiers = re.findall(r"^\| ([A-Z]+(?:-[A-Z]+)*-\d{3}) \|", matrix, re.MULTILINE)
    if len(identifiers) != len(set(identifiers)):
        errors.append("Duplicate requirement IDs")
    for row in matrix.splitlines():
        if row.startswith("| UIX-") and row.endswith("| VERIFIED |"):
            errors.append("DW1 evidence cannot complete an entire staged native requirement")

    counts = {
        state: sum(item["status"] == state for item in inventory["files"].values())
        for state in ("preserved", "modified", "added")
    }
    print(f"Checked {len(paths)} Markdown files, {links} local links/fragments and balanced fences")
    print(f"Checked dated inventory: {counts}")
    print(
        "Checked 9 preserved ADR bodies, annotated ADR-010 "
        f"and {len(identifiers)} unique requirements"
    )
    print(f"Excluded unrelated live state: {inventory['excluded_unrelated']}")
    if errors:
        raise SystemExit("\n".join(errors))
    print("PASS: DW1 review integrity; no scientific or release approval implied")


if __name__ == "__main__":
    main()
