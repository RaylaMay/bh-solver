from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from bh_sim.core import (
    AiProfile,
    ChangeRecord,
    ChangeSet,
    ChangeSetStatus,
    DraftRevision,
    ExplorationLimits,
    StableId,
    apply_change_set,
    approve_change_set,
)
from tests.test_engine import simple_case


def revisions(profile: AiProfile) -> tuple[DraftRevision, DraftRevision]:
    case = replace(simple_case(), ai_profile=profile)
    now = datetime.now(UTC).isoformat()
    baseline = DraftRevision(StableId("revision:one"), case.case_id, 1, case, (), now)
    proposed = DraftRevision(
        StableId("revision:two"),
        case.case_id,
        2,
        case,
        (ChangeRecord("replace", StableId("unit:heater"), "duty", "500 kW", "600 kW"),),
        now,
    )
    return baseline, proposed


def change_set(profile: AiProfile) -> tuple[DraftRevision, ChangeSet]:
    baseline, proposed = revisions(profile)
    return baseline, ChangeSet(
        StableId("change:one"),
        profile,
        baseline.revision_id,
        proposed,
        proposed.changes,
        "Evaluate a declared heat-load variation.",
        exploration_limits=(
            ExplorationLimits(10, 10, 60.0) if profile is AiProfile.EXPLORATION else None
        ),
    )


def test_review_change_requires_approval_and_preserves_baseline() -> None:
    baseline, proposal = change_set(AiProfile.REVIEW)
    with pytest.raises(PermissionError):
        apply_change_set(proposal, baseline)
    approved = approve_change_set(proposal)
    revision, applied = apply_change_set(approved, baseline)
    assert revision.revision_number == 2
    assert baseline.revision_number == 1
    assert applied.status is ChangeSetStatus.APPLIED


def test_exploration_runs_in_an_isolated_revision_with_limits() -> None:
    baseline, proposal = change_set(AiProfile.EXPLORATION)
    revision, applied = apply_change_set(proposal, baseline)
    assert revision is proposal.proposed_revision
    assert revision is not baseline
    assert applied.exploration_limits == ExplorationLimits(10, 10, 60.0)


def test_narrative_profile_cannot_be_hidden_by_a_review_case() -> None:
    baseline, proposal = change_set(AiProfile.NARRATIVE)
    hidden = replace(
        proposal,
        proposed_revision=replace(
            proposal.proposed_revision,
            case=replace(proposal.proposed_revision.case, ai_profile=AiProfile.REVIEW),
        ),
    )
    with pytest.raises(ValueError, match="visible AI profile"):
        apply_change_set(hidden, baseline)
