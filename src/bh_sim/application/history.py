"""Durable editing history over immutable checkpoints and the existing PFD policy.

No numerical or effectful command is replayed. Undo restores verified checkpoint
content only when the intervening document still matches the original edit. This
single-editor implementation deliberately rejects cross-actor reversals; shared
selective undo belongs to the following collaboration milestone.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import fields, is_dataclass
from datetime import UTC, datetime
from typing import Literal, Protocol
from uuid import uuid4

from bh_sim.boundary import contracts as c
from bh_sim.boundary.json_codec import boundary_json

from .pfd import PfdService, pfd_engineering_content_hash
from .services import CommandRejected


class HistoryRepositoryPort(Protocol):
    """Atomic publication and verified loading of non-executable history data."""

    def checkpoint(self, document: c.PfdDocumentDto) -> str: ...
    def document(self, digest: str) -> c.PfdDocumentDto: ...
    def entries(self, draft_id: str) -> tuple[c.HistoryEntry, ...]: ...
    def append(self, draft_id: str, entry: c.HistoryEntry) -> None: ...
    def draft_ids(self) -> tuple[str, ...]: ...


def document_hash(document: c.PfdDocumentDto) -> str:
    """Exact history identity; independent of canonical scientific hashes."""
    return hashlib.sha256(boundary_json(document).encode()).hexdigest()


def _flatten(value: object, prefix: str = "") -> dict[str, str]:
    """Make stable object/field comparisons without positional list noise."""
    if is_dataclass(value) and not isinstance(value, type):
        result: dict[str, str] = {}
        for field in fields(value):
            result.update(_flatten(getattr(value, field.name), prefix + "/" + field.name))
        return result
    if isinstance(value, tuple):
        result = {}
        for index, item in enumerate(value):
            identity = next(
                (
                    getattr(item, key)
                    for key in ("object_id", "subsystem_id", "group_id", "name")
                    if hasattr(item, key)
                ),
                str(index),
            )
            result.update(_flatten(item, prefix + "/" + str(identity)))
        return result
    return {prefix: json.dumps(value, ensure_ascii=False)}


def compare_documents(
    before: c.PfdDocumentDto, after: c.PfdDocumentDto
) -> tuple[c.HistoryDifference, ...]:
    """Compare engineering inputs and shared presentation, never calculated deltas."""
    differences: list[c.HistoryDifference] = []
    for category, left, right in (
        (
            "engineering",
            (before.draft.equipment, before.draft.connections, before.engineering_subsystems),
            (after.draft.equipment, after.draft.connections, after.engineering_subsystems),
        ),
        (
            "presentation",
            (
                before.objects,
                before.settings,
                before.visual_groups,
                before.layer_preferences,
                before.next_stream_number,
            ),
            (
                after.objects,
                after.settings,
                after.visual_groups,
                after.layer_preferences,
                after.next_stream_number,
            ),
        ),
    ):
        a, b = _flatten(left), _flatten(right)
        for path in sorted(a.keys() | b.keys()):
            if a.get(path) != b.get(path):
                segments = path.split("/")
                differences.append(
                    c.HistoryDifference(
                        "engineering" if category == "engineering" else "presentation",
                        segments[2] if len(segments) > 2 else "document",
                        path,
                        a.get(path, "<absent>"),
                        b.get(path, "<absent>"),
                    )
                )
    return tuple(differences)


class HistoryService:
    """One local revision authority shared by GUI and typed command adapters."""

    def __init__(self, pfd: PfdService, repository: HistoryRepositoryPort) -> None:
        self.pfd, self.repository = pfd, repository

    def state(self, draft_id: str, entry_id: str = "") -> c.HistoryState:
        """Load a head or a read-only historical prefix; fail explicitly on corruption."""
        entries = self.repository.entries(draft_id)
        if entry_id:
            index = next(i for i, e in enumerate(entries) if e.entry_id == entry_id)
            entries = entries[: index + 1]
        if not entries:
            raise KeyError(draft_id)
        head = entries[-1]
        document = self.repository.document(head.after_hash)
        self.pfd.check(document)
        saved = any(
            e.saved_version is not None
            and e.saved_version.document_hash == head.after_hash
            and e.branch.branch_id == head.branch.branch_id
            for e in entries
        )
        return c.HistoryState(document, entries, not saved)

    def listing(self) -> c.DraftListDto:
        """Combine saved drafts with continuously recovered working documents."""
        rows = {row.draft_id: row for row in self.pfd.listing().drafts}
        for identifier in self.repository.draft_ids():
            state = self.state(identifier)
            versions = [e.saved_version for e in state.entries if e.saved_version]
            rows[identifier] = c.DraftSummaryDto(
                identifier,
                versions[-1].revision if versions else 0,
                state.entries[-1].created_at,
            )
        return c.DraftListDto(tuple(rows[k] for k in sorted(rows)))

    def dispatch(self, request: c.CommandRequest) -> c.CommandData:
        """Handle history commands; only typed PFD edits reach editing policy."""
        params = request.parameters
        if request.command_name == "history.list":
            return self.listing()
        if isinstance(params, c.CompareHistoryParameters):
            before = self.state(params.before.draft_id, params.before.entry_id)
            after = self.state(params.after.draft_id, params.after.entry_id)
            return c.HistoryComparison(
                before.entries[-1].entry_id,
                after.entries[-1].entry_id,
                compare_documents(before.document, after.document),
            )
        if isinstance(params, c.PfdDocumentParameters):
            doc = params.document
            self.pfd.check(doc)
            existing = self.repository.entries(doc.draft.draft_id)
            if existing:
                prior = next((e for e in existing if e.request_id == request.request_id), None)
                if prior is not None and prior.operation_json == boundary_json(request):
                    return self.state(doc.draft.draft_id, prior.entry_id)
                raise CommandRejected("HISTORY_EXISTS", "Open the existing recovered document")
            return self._commit(request, doc, (), "start", "Starting point", (), ())
        target = params.target if isinstance(params, c.HistoryEditParameters) else params
        if not isinstance(target, c.HistoryTarget):
            raise ValueError("Expected history target")
        entries = self.repository.entries(target.draft_id)
        if not entries and request.command_name == "history.open":
            # Import the latest legacy/native save without manufacturing earlier edits.
            doc = self.pfd.open(target.draft_id)
            return self._commit(
                request,
                doc,
                (),
                "start",
                "Imported starting point",
                (),
                (),
                saved_revision=doc.draft.revision,
            )
        if not entries:
            raise KeyError(target.draft_id)
        if request.command_name in {"history.open", "history.view"}:
            return self.state(target.draft_id, target.entry_id)
        for entry in entries:
            if entry.request_id == request.request_id:
                if entry.operation_json != boundary_json(request):
                    raise CommandRejected("REQUEST_ID_CONFLICT", "Request ID was already used")
                return self.state(target.draft_id, entry.entry_id)
        head = entries[-1]
        if target.expected_head != head.entry_id:
            raise CommandRejected(
                "HISTORY_CONFLICT", "The document changed; reopen its current head"
            )
        doc = self.repository.document(head.after_hash)
        if isinstance(params, c.HistoryEditParameters):
            updated = self.pfd.edit(doc, params.edit)
            if updated == doc:
                return self.state(target.draft_id)
            label = re.sub(r"(?<!^)(?=[A-Z])", " ", type(params.edit).__name__.removesuffix("Edit"))
            if isinstance(params.edit, c.ConfigureInputEdit):
                label = f"Set {params.edit.name}: {params.edit.text} {params.edit.unit}"
            elif isinstance(params.edit, c.RenameObjectEdit):
                previous_tag = next(
                    o.tag for o in doc.objects if o.object_id == params.edit.object_id
                )
                label = f"Rename {previous_tag} to {params.edit.tag}"
            return self._commit(
                request,
                updated,
                entries,
                "edit",
                label,
                head.undo_ids,
                (),
                add_undo=True,
                fork=bool(head.redo_ids),
            )
        if request.command_name in {"history.undo", "history.redo"}:
            undo = request.command_name == "history.undo"
            stack = head.undo_ids if undo else head.redo_ids
            if not stack:
                raise CommandRejected("HISTORY_EMPTY", "No edit is available to reverse")
            original = next(e for e in entries if e.entry_id == stack[-1])
            if original.actor_id != request.actor_id:
                raise CommandRejected("UNDO_AUTHORITY", "Undo can reverse only your own edits")
            expected = original.after_hash if undo else original.before_hash
            if head.after_hash != expected:
                raise CommandRejected("UNDO_CONFLICT", "Later changes conflict with this reversal")
            restored = self.repository.document(
                original.before_hash if undo else original.after_hash
            )
            return self._commit(
                request,
                restored,
                entries,
                "undo" if undo else "redo",
                ("Undo " if undo else "Redo ") + original.label,
                head.undo_ids[:-1] if undo else (*head.undo_ids, original.entry_id),
                (*head.redo_ids, original.entry_id) if undo else head.redo_ids[:-1],
                reverses=original.entry_id,
            )
        if request.command_name == "history.save":
            saved = self.pfd.save(doc)
            return self._commit(
                request,
                doc,
                entries,
                "save",
                "Saved version",
                head.undo_ids,
                head.redo_ids,
                saved_revision=saved.draft.revision,
            )
        if request.command_name == "history.snapshot":
            name = target.name.strip()
            if not name or len(name) > 120 or any(ord(ch) < 32 for ch in name):
                raise CommandRejected("SNAPSHOT_NAME", "Use 1–120 printable characters")
            return self._commit(
                request,
                doc,
                entries,
                "snapshot",
                name,
                head.undo_ids,
                head.redo_ids,
                snapshot_name=name,
            )
        if request.command_name == "history.branch":
            if len(target.name) > 120 or any(ord(ch) < 32 for ch in target.name):
                raise CommandRejected("BRANCH_NAME", "Use at most 120 printable characters")
            origin = next(e for e in entries if e.entry_id == target.entry_id)
            restored = self.repository.document(origin.after_hash)
            return self._commit(
                request,
                restored,
                entries,
                "branch",
                target.name.strip() or "Alternative",
                (),
                (),
                fork=True,
                origin=origin.entry_id,
            )
        raise ValueError("Unknown history command")

    def _commit(
        self,
        request: c.CommandRequest,
        document: c.PfdDocumentDto,
        entries: tuple[c.HistoryEntry, ...],
        kind: Literal["start", "edit", "undo", "redo", "save", "snapshot", "branch"],
        label: str,
        undo: tuple[str, ...],
        redo: tuple[str, ...],
        *,
        add_undo: bool = False,
        fork: bool = False,
        origin: str | None = None,
        reverses: str | None = None,
        saved_revision: int | None = None,
        snapshot_name: str = "",
    ) -> c.HistoryState:
        """Publish checkpoint before event; failed publication cannot advance the head."""
        self.pfd.check(document)
        head = entries[-1] if entries else None
        before = self.repository.document(head.after_hash) if head else document
        before_engineering = pfd_engineering_content_hash(before)
        after_engineering = pfd_engineering_content_hash(document)
        digest = self.repository.checkpoint(document)
        identifier = "history:" + uuid4().hex
        timestamp = datetime.now(UTC).isoformat()
        branch = (
            head.branch
            if head and not fork
            else c.HistoryBranchReference(
                "branch:" + uuid4().hex,
                (
                    label
                    if kind == "branch"
                    else f"Alternative {len({e.branch.branch_id for e in entries})}"
                )
                if head
                else "Main",
                origin or (head.entry_id if head else None),
            )
        )
        classification = (
            "engineering"
            if before_engineering != after_engineering
            else "presentation"
            if head and head.after_hash != digest
            else "metadata"
        )
        differences = compare_documents(before, document)
        entry = c.HistoryEntry(
            identifier,
            len(entries) + 1,
            head.entry_id if head else None,
            request.actor_id,
            request.request_id,
            timestamp,
            branch,
            kind,
            label,
            classification,
            tuple(sorted({d.object_id for d in differences})),
            head.after_hash if head else digest,
            digest,
            before_engineering,
            after_engineering,
            boundary_json(request),
            reverses,
            (*undo, identifier) if add_undo else undo,
            redo,
            c.SavedVersionReference(identifier, saved_revision, digest, timestamp)
            if saved_revision is not None
            else None,
            c.NamedSnapshot("snapshot:" + uuid4().hex, snapshot_name, identifier, digest)
            if snapshot_name
            else None,
        )
        self.repository.append(document.draft.draft_id, entry)
        return self.state(document.draft.draft_id)
