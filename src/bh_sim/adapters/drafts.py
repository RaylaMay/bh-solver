"""Legacy PFD draft storage isolated from scientific artifact reconstruction.

The on-disk v1alpha format and immutable/idempotent save semantics are unchanged.
This module can serve the desktop shell without importing any solver or property
implementation. Discovery reads saved revisions; it never validates or runs them.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock

from bh_sim.api.schemas import PfdDraftDto
from bh_sim.boundary.contracts import DraftDto, DraftSummaryDto

from .browser_format import from_browser, to_browser


class DraftRepository:
    """Immutable on-disk PFD revisions with idempotent saves."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def _paths(self, draft_id: str) -> list[Path]:
        safe = "".join(
            character if character.isalnum() or character in "-_" else "-" for character in draft_id
        )
        return sorted(self.root.glob(f"{safe}.r*.json"))

    @staticmethod
    def _without_transient_results(draft: PfdDraftDto) -> PfdDraftDto:
        payload = draft.model_dump(mode="json", by_alias=True)
        for node in payload["nodes"]:
            node["data"]["status"] = "draft"
            node["data"]["validity"] = "UNKNOWN"
            node["data"].pop("metrics", None)
        return PfdDraftDto.model_validate(payload)

    def save(self, draft: PfdDraftDto) -> PfdDraftDto:
        with self._lock:
            draft = self._without_transient_results(draft)
            paths = self._paths(draft.draft_id)
            comparable = draft.model_dump(
                mode="json", by_alias=True, exclude={"revision", "updated_at"}
            )
            if paths:
                latest = PfdDraftDto.model_validate_json(paths[-1].read_text(encoding="utf-8"))
                latest_comparable = latest.model_dump(
                    mode="json", by_alias=True, exclude={"revision", "updated_at"}
                )
                if comparable == latest_comparable:
                    return latest
                revision = latest.revision + 1
            else:
                revision = 1
            saved = draft.model_copy(update={"revision": revision, "updated_at": datetime.now(UTC)})
            safe_id = "".join(
                character if character.isalnum() or character in "-_" else "-"
                for character in draft.draft_id
            )
            destination = self.root / f"{safe_id}.r{revision:06d}.json"
            if destination.exists():
                raise RuntimeError("immutable draft revision already exists")
            destination.write_text(
                json.dumps(saved.model_dump(mode="json", by_alias=True), indent=2) + "\n",
                encoding="utf-8",
            )
            return saved

    def latest(self, draft_id: str) -> PfdDraftDto:
        paths = self._paths(draft_id)
        if not paths:
            raise KeyError(draft_id)
        return PfdDraftDto.model_validate_json(paths[-1].read_text(encoding="utf-8"))


class DraftRepositoryAdapter:
    """Neutral draft port retaining the on-disk v1alpha browser format."""

    def __init__(self, repository: DraftRepository) -> None:
        self.repository = repository

    def save(self, draft: DraftDto) -> DraftDto:
        return from_browser(self.repository.save(to_browser(draft)))

    def latest(self, draft_id: str) -> DraftDto:
        return from_browser(self.repository.latest(draft_id))

    def summaries(self) -> tuple[DraftSummaryDto, ...]:
        """List latest saved identities, failing explicitly on unreadable revisions."""
        latest: dict[str, PfdDraftDto] = {}
        for path in sorted(self.repository.root.glob("*.r*.json")):
            draft = PfdDraftDto.model_validate_json(path.read_text(encoding="utf-8"))
            prior = latest.get(draft.draft_id)
            if prior is None or draft.revision > prior.revision:
                latest[draft.draft_id] = draft
        return tuple(
            DraftSummaryDto(item.draft_id, item.revision, item.updated_at.isoformat())
            for item in sorted(latest.values(), key=lambda item: item.draft_id)
        )
