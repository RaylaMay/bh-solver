"""Portable adapter-private filenames for externally visible identifiers."""

from __future__ import annotations

import hashlib

_WINDOWS_FORBIDDEN_CHARACTERS = frozenset('<>:"/\\|?*')
_WINDOWS_RESERVED_STEMS = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{number}" for number in range(1, 10)}
    | {f"LPT{number}" for number in range(1, 10)}
)


def identifier_json_filename(identifier: str) -> str:
    """Return a deterministic JSON filename safe on supported filesystems."""
    if not identifier:
        raise ValueError("Identifier must not be empty")
    digest = hashlib.sha256(identifier.encode("utf-8")).hexdigest()
    return f"{digest}.json"


def is_windows_safe_filename(filename: str) -> bool:
    """Return whether Windows can represent ``filename`` as one path component."""
    if (
        not filename
        or filename.endswith((" ", "."))
        or any(char in _WINDOWS_FORBIDDEN_CHARACTERS or ord(char) < 32 for char in filename)
    ):
        return False
    return filename.split(".", 1)[0].upper() not in _WINDOWS_RESERVED_STEMS
