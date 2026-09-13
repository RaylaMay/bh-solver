"""Check DW0 document integrity, preserved ADRs and unchanged baseline files.

This standard-library audit helper reads repository Markdown and the DW0 baseline
manifest. It writes nothing and exits nonzero on failed checks. It checks local
inline Markdown links/heading fragments and fence balance, not rendered diagrams,
external web availability, scientific correctness or owner approval. Run from
any directory using Python 3.11 or later. Later source changes intentionally make
baseline-preservation checks fail; preserve the original report as dated evidence.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = Path(__file__).resolve().parent


def heading_ids(content: str) -> set[str]:
    """Return GitHub-style heading IDs used by this bounded document package."""
    result: set[str] = set()
    counts: dict[str, int] = {}
    for heading in re.findall(r"^#{1,6} (.+)$", content, flags=re.MULTILINE):
        slug = re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        result.add(f"{slug}-{count}" if count else slug)
    return result


def main() -> None:
    """Fail visibly if the prepared package loses links or alters preserved inputs."""
    baseline = json.loads((EVIDENCE / "baseline.json").read_text(encoding="utf-8"))
    errors: list[str] = []
    preserved = 0
    for name, record in baseline["files"].items():
        if name in baseline["edited_documents"] or name in baseline["observed_unrelated_changes"]:
            continue
        path = ROOT / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
            errors.append(f"Baseline file changed or missing: {name}")
        preserved += 1

    decisions = (ROOT / "docs/DECISIONS.md").read_text(encoding="utf-8")
    sections = re.findall(r"^## ADR-\d{3} .*?(?=^## ADR-|\Z)", decisions, re.MULTILINE | re.DOTALL)
    for section in sections:
        identifier = section.split()[1]
        expected = baseline["accepted_adr_sha256"].get(identifier)
        if expected and hashlib.sha256(section.rstrip().encode()).hexdigest() != expected:
            errors.append(f"Accepted decision changed: {identifier}")
    if len(sections) != 10 or "**Status:** PROPOSED" not in sections[-1]:
        errors.append("Expected nine accepted ADRs and a proposed ADR-010")

    links = 0
    paths = [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md"))]
    for path in paths:
        content = path.read_text(encoding="utf-8")
        if len(re.findall(r"^```", content, re.MULTILINE)) % 2:
            errors.append(f"Unbalanced fences: {path.relative_to(ROOT)}")
        for target in re.findall(r"\[[^\]\n]+\]\(([^)\n]+)\)", content):
            parsed = urlsplit(target.strip("<>"))
            if parsed.scheme:
                continue
            destination = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
            links += 1
            if not destination.exists():
                errors.append(f"Missing link from {path.relative_to(ROOT)}: {target}")
            elif (
                parsed.fragment
                and destination.suffix == ".md"
                and unquote(parsed.fragment)
                not in heading_ids(destination.read_text(encoding="utf-8"))
            ):
                errors.append(f"Missing heading from {path.relative_to(ROOT)}: {target}")

    matrix = (ROOT / "docs/REQUIREMENTS_VERIFICATION.md").read_text(encoding="utf-8")
    identifiers = re.findall(r"^\| ([A-Z]+(?:-[A-Z]+)*-\d{3}) \|", matrix, re.MULTILINE)
    if len(identifiers) != len(set(identifiers)):
        errors.append("Duplicate requirement IDs")
    for row in matrix.splitlines():
        if row.startswith("| UIX-") and not row.endswith("| PLANNED |"):
            errors.append("Native requirement promoted beyond PLANNED")
    print(f"Checked {len(paths)} Markdown files and {links} local links/fragments")
    print(f"Checked {preserved} preserved baseline files and 9 accepted ADR bodies")
    print(f'Excluded unrelated live changes: {list(baseline["observed_unrelated_changes"])}')
    print(f"Checked {len(identifiers)} unique requirement IDs and proposed UIX states")
    if errors:
        raise SystemExit("\n".join(errors))
    print("PASS: document integrity and baseline preservation; no approval implied")


if __name__ == "__main__":
    main()
