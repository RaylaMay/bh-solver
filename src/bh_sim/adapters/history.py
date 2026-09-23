"""Hash-verified JSON checkpoints and an append-only local history journal.

An event is acknowledged only after exclusive atomic publication and directory
fsync. Checkpoints published before an interrupted event are harmless orphans.
The journal is its own rebuildable ordered index; no database is authoritative.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections import OrderedDict
from pathlib import Path

from bh_sim.boundary import contracts as c
from bh_sim.boundary.json_codec import boundary_from_json, boundary_json

MAX_RECORD_BYTES = 20_000_000  # Same bounded-document limit as native PFD storage.


def content_hash(document: c.PfdDocumentDto) -> str:
    """Identify exact checkpoint bytes without changing scientific hash schemes."""
    return hashlib.sha256(boundary_json(document).encode()).hexdigest()


def publish(path: Path, payload: str) -> None:
    """Publish once; collision rejects a concurrent writer, never overwrites it."""
    data = payload.encode("utf-8")
    if len(data) > MAX_RECORD_BYTES:
        raise ValueError("History record exceeds the 20 MB bound")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
        if os.name != "nt":
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        Path(temporary).unlink(missing_ok=True)


def read_bounded(path: Path) -> str:
    """Bound parsing allocations; malformed or missing content remains explicit."""
    with path.open("rb") as handle:
        raw = handle.read(MAX_RECORD_BYTES + 1)
    if len(raw) > MAX_RECORD_BYTES:
        raise ValueError("History record exceeds the 20 MB bound")
    return raw.decode("utf-8")


class JsonHistoryRepository:
    """Single-host durable history; independent instances detect commit races."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._documents: OrderedDict[str, c.PfdDocumentDto] = OrderedDict()
        self._records: OrderedDict[str, c.HistoryEntry] = OrderedDict()
        # Cache decoded immutable DTOs, not filesystem integrity. Each read still
        # checks bytes against SHA-256. DW3.2 profiling found repeated decoding
        # dominated edit latency; bounded caches avoid retaining every checkpoint.

    def _directory(self, draft_id: str) -> Path:
        return self.root / hashlib.sha256(draft_id.encode()).hexdigest()

    def checkpoint(self, document: c.PfdDocumentDto) -> str:
        """Store immutable content once and verify an existing copy before reuse."""
        raw = boundary_json(document)
        digest = hashlib.sha256(raw.encode()).hexdigest()
        path = self.root / "checkpoints" / (digest + ".json")
        if path.exists():
            if read_bounded(path) != raw:
                raise ValueError("Checkpoint integrity failure")
        else:
            try:
                publish(path, raw)
            except FileExistsError:
                if read_bounded(path) != raw:
                    raise ValueError("Checkpoint integrity failure") from None
        self._cache_document(digest, document)
        return digest

    def _cache_document(self, digest: str, document: c.PfdDocumentDto) -> None:
        self._documents[digest] = document
        self._documents.move_to_end(digest)
        while len(self._documents) > 64:
            self._documents.popitem(last=False)

    def document(self, digest: str) -> c.PfdDocumentDto:
        """Verify before decoding; caller-supplied hashes cannot name arbitrary paths."""
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise ValueError("Invalid checkpoint hash")
        raw = read_bounded(self.root / "checkpoints" / (digest + ".json"))
        if hashlib.sha256(raw.encode()).hexdigest() != digest:
            raise ValueError("Checkpoint integrity failure")
        cached = self._documents.get(digest)
        if cached is not None:
            self._documents.move_to_end(digest)
            return cached
        document = boundary_from_json(raw)
        if not isinstance(document, c.PfdDocumentDto):
            raise ValueError("Expected PFD checkpoint")
        self._cache_document(digest, document)
        return document

    def _record(self, path: Path) -> c.HistoryEntry:
        """Decode only a complete, verified event envelope, including during discovery."""
        wrapper = json.loads(read_bounded(path))
        if not isinstance(wrapper, dict) or set(wrapper) != {"record", "sha256"}:
            raise ValueError("Invalid history envelope")
        raw = wrapper["record"]
        if (
            not isinstance(raw, str)
            or hashlib.sha256(raw.encode()).hexdigest() != wrapper["sha256"]
        ):
            raise ValueError("History integrity failure")
        digest = wrapper["sha256"]
        entry = self._records.get(digest)
        if entry is None:
            entry = boundary_from_json(raw)
            if isinstance(entry, c.HistoryEntry):
                self._records[digest] = entry
                while len(self._records) > 2048:
                    self._records.popitem(last=False)
        else:
            self._records.move_to_end(digest)
        if not isinstance(entry, c.HistoryEntry):
            raise ValueError("Invalid history entry")
        return entry

    def entries(self, draft_id: str) -> tuple[c.HistoryEntry, ...]:
        """Rebuild the ordered index and reject gaps, corruption or broken parentage."""
        result: list[c.HistoryEntry] = []
        for sequence, path in enumerate(sorted(self._directory(draft_id).glob("*.json")), 1):
            entry = self._record(path)
            if (
                not isinstance(entry, c.HistoryEntry)
                or entry.sequence != sequence
                or path.name != f"{sequence:012d}.json"
                or entry.parent_entry_id != (result[-1].entry_id if result else None)
                or (result and entry.before_hash != result[-1].after_hash)
            ):
                raise ValueError("History chain is incomplete or inconsistent")
            result.append(entry)
        if result and self.document(result[-1].after_hash).draft.draft_id != draft_id:
            raise ValueError("History identity mismatch")
        return tuple(result)

    def append(self, draft_id: str, entry: c.HistoryEntry) -> None:
        """Commit exactly the next sequence; no silent conflict retry or overwrite."""
        entries = self.entries(draft_id)
        if entry.sequence != len(entries) + 1 or entry.parent_entry_id != (
            entries[-1].entry_id if entries else None
        ):
            raise RuntimeError("History head changed")
        raw = boundary_json(entry)
        wrapper = json.dumps(
            {"record": raw, "sha256": hashlib.sha256(raw.encode()).hexdigest()},
            sort_keys=True,
            separators=(",", ":"),
        )
        publish(self._directory(draft_id) / f"{entry.sequence:012d}.json", wrapper)

    def draft_ids(self) -> tuple[str, ...]:
        """Discover committed histories, including drafts with no explicit Save yet."""
        ids: list[str] = []
        for directory in sorted(self.root.iterdir()):
            first = directory / "000000000001.json"
            if not directory.is_dir() or not first.exists():
                continue
            entry = self._record(first)
            identifier = self.document(entry.after_hash).draft.draft_id
            if directory != self._directory(identifier):
                raise ValueError("History identity mismatch")
            ids.append(identifier)
        return tuple(ids)
