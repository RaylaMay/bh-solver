"""Verify the dated public Git baseline and current public Markdown file links.

Historical DW2 evidence is sanitized and cannot authenticate its pre-transition
bytes. This checker verifies the available public root tree, never rewrites it.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "docs/native/evidence/public-baseline-2026-09-13/baseline.json"


def git(*arguments: str) -> bytes:
    """Read Git metadata without network access or working-tree mutation."""
    return subprocess.check_output(["git", *arguments], cwd=ROOT)


def main() -> None:
    """Fail on changed historical bytes, missing Git objects or broken public file links."""
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    commit = baseline["commit"]
    files = baseline["files"]
    tree = set(git("ls-tree", "-rz", "--name-only", commit).decode().split("\0")) - {""}
    errors = []
    if tree != set(files):
        errors.append("Baseline inventory differs from the Git tree")
    for name, expected in files.items():
        actual = hashlib.sha256(git("show", f"{commit}:{name}")).hexdigest()
        if actual != expected:
            errors.append("Baseline Git hash mismatch: " + name)
        if name.startswith("docs/native/evidence/"):
            path = ROOT / name
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                errors.append("Historical public evidence changed: " + name)
    public = set(
        git("ls-files", "-z", "--cached", "--others", "--exclude-standard").decode().split("\0")
    ) - {""}
    checked = 0
    for name in sorted(public):
        if not name.endswith(".md") or name.startswith("docs/native/evidence/"):
            continue
        path = ROOT / name
        if not path.is_file():
            continue
        # Fenced command examples are documentation, not active Markdown hyperlinks.
        content = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.S)
        for link in re.findall(r"\]\((<[^>]+>|[^\s)]+)(?:\s+\"[^\"]*\")?\)", content):
            target = unquote(link.strip("<>"))
            if urlsplit(target).scheme or target.startswith("#"):
                continue
            target = target.split("#", 1)[0]
            if not target:
                continue
            resolved = (path.parent / target).resolve()
            try:
                relative = resolved.relative_to(ROOT).as_posix()
            except ValueError:
                errors.append(f"Nonportable local link: {name}: {target}")
                continue
            if not resolved.exists():
                errors.append(f"Missing link: {name}: {target}")
            elif resolved.is_file() and relative not in public:
                errors.append(f"Link depends on private/untracked ignored file: {name}: {target}")
            checked += 1
    if errors:
        raise SystemExit("\n".join(errors))
    print(
        f"PASS: {len(files)} baseline Git objects; historical bytes unchanged; "
        f"{checked} public file links"
    )


if __name__ == "__main__":
    main()
