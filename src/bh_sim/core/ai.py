"""Guardrails for AI-authored changes to simulator drafts."""

from __future__ import annotations

from dataclasses import replace

from .contracts import (
    AiProfile,
    ChangeSet,
    ChangeSetStatus,
    DraftRevision,
)


def approve_change_set(change_set: ChangeSet) -> ChangeSet:
    """Approve a review-profile proposal without applying it."""

    if change_set.status is not ChangeSetStatus.PROPOSED:
        raise ValueError("only a proposed change set can be approved")
    return replace(change_set, status=ChangeSetStatus.APPROVED)


def apply_change_set(
    change_set: ChangeSet, baseline: DraftRevision
) -> tuple[DraftRevision, ChangeSet]:
    """Return an isolated new revision; the baseline object is never mutated."""

    if change_set.base_revision_id != baseline.revision_id:
        raise ValueError("change set does not target the supplied baseline revision")
    if change_set.proposed_revision.base_case_id != baseline.base_case_id:
        raise ValueError("change set cannot move a draft to another case")
    if change_set.proposed_revision.revision_number <= baseline.revision_number:
        raise ValueError("change set must advance the revision number")
    if change_set.status is ChangeSetStatus.REJECTED:
        raise ValueError("a rejected change set cannot be applied")
    if change_set.profile is AiProfile.REVIEW and change_set.status is not ChangeSetStatus.APPROVED:
        raise PermissionError("review-profile changes require explicit approval")
    if change_set.profile is AiProfile.EXPLORATION and change_set.exploration_limits is None:
        raise ValueError("exploration changes require declared limits")
    if change_set.proposed_revision.case.ai_profile is not change_set.profile:
        raise ValueError("proposed case must retain the change set's visible AI profile")
    return change_set.proposed_revision, replace(change_set, status=ChangeSetStatus.APPLIED)
