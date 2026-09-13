"""Read-only integrity and document checks for the dated DW2 review package.

The manifest records this uncommitted workspace's before/after hashes. Historical
DW0/DW1 evidence remains unchanged; later work must create its own evidence instead
of rewriting these files. This checker grants no scientific or release approval.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[4]
EVIDENCE = Path(__file__).resolve().parent


def heading_ids(content: str) -> set[str]:
    """Match the existing review helper's bounded GitHub-style heading convention."""
    result: set[str] = set()
    counts: dict[str, int] = {}
    for heading in re.findall(r"^#{1,6} (.+)$", content, flags=re.MULTILINE):
        slug = re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        result.add(f"{slug}-{count}" if count else slug)
    return result


def digest(path: Path) -> str:
    """Hash exact on-disk bytes, including binary visual review assets."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    """Check recorded files, old decisions, Markdown links and requirement statuses."""
    inventory = json.loads((EVIDENCE / "file-inventory.json").read_text())
    errors: list[str] = []
    if digest(EVIDENCE / "changes.patch") != inventory["patch_sha256"]:
        errors.append("DW2 text review patch changed")
    for name, record in inventory["files"].items():
        path = ROOT / name
        if not path.is_file() or digest(path) != record["after_sha256"]:
            errors.append("Dated DW2 file changed or missing: " + name)
    for name, expected in inventory["browser_baseline_sha256"].items():
        path = ROOT / name
        if not path.is_file() or digest(path) != expected:
            errors.append("Retained browser file changed or missing: " + name)

    paths = [
        ROOT / "README.md",
        *sorted((ROOT / "docs").rglob("*.md")),
        *sorted((ROOT / "tests/fixtures").rglob("README.md")),
    ]
    links = 0
    for path in paths:
        content = path.read_text()
        if len(re.findall(r"^```", content, re.MULTILINE)) % 2:
            errors.append("Unbalanced fences: " + str(path.relative_to(ROOT)))
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

    decisions = (ROOT / "docs/DECISIONS.md").read_text()
    sections = re.findall(r"^## ADR-\d{3} .*?(?=^## ADR-|\Z)", decisions, re.MULTILINE | re.DOTALL)
    for section in sections:
        identifier = section.split()[1]
        if hashlib.sha256(section.rstrip().encode()).hexdigest() != inventory[
            "accepted_adr_sha256"
        ].get(identifier):
            errors.append("Accepted ADR body changed: " + identifier)
    if len(sections) != 10 or "ACCEPTED WITH OWNER ANNOTATIONS" not in sections[-1]:
        errors.append("Expected ten accepted decisions including annotated ADR-010")

    matrix = (ROOT / "docs/REQUIREMENTS_VERIFICATION.md").read_text()
    identifiers = re.findall(r"^\| ([A-Z]+(?:-[A-Z]+)*-\d{3}) \|", matrix, re.MULTILINE)
    if len(identifiers) != len(set(identifiers)):
        errors.append("Duplicate requirement IDs")
    for row in matrix.splitlines():
        if row.startswith("| UIX-") and row.endswith("| VERIFIED |"):
            errors.append("DW2 software evidence cannot complete a full staged native requirement")
    counts = {
        state: sum(item["status"] == state for item in inventory["files"].values())
        for state in ("preserved", "modified", "added")
    }
    print(f"Checked {len(paths)} Markdown files, {links} local links/fragments and balanced fences")
    print(f"Checked DW2 inventory: {counts}; binary captures included by hash")
    print(f"Checked {len(inventory['browser_baseline_sha256'])} retained browser files")
    print(f"Checked 10 preserved ADR bodies and {len(identifiers)} unique requirements")
    print("Excluded owner notes, live app state, generated metadata/runtime and recursive outputs")
    if errors:
        raise SystemExit("\n".join(errors))
    print("PASS: DW2 review integrity; no native witness, scientific or release approval implied")


if __name__ == "__main__":
    main()
