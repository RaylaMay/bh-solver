"""Stable identifier values used by persisted contracts."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

_ID_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,127}$")


@dataclass(frozen=True, order=True)
class StableId:
    """A durable, user-visible identifier rather than an object address."""

    value: str

    def __post_init__(self) -> None:
        if not _ID_PATTERN.fullmatch(self.value):
            raise ValueError(
                "stable IDs must start with a letter and contain at most 128 "
                "letters, digits, underscores, dots, colons, or hyphens"
            )

    def __str__(self) -> str:
        return self.value


def new_stable_id(kind: str) -> StableId:
    """Create a random stable ID with a readable type prefix."""

    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,31}", kind):
        raise ValueError("identifier kind must be a short alphanumeric name")
    return StableId(f"{kind}:{uuid.uuid4()}")
