"""Fixed additive command shapes and repository failure semantics, without Qt."""

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from bh_sim.adapters.desktop_preview import create_preview_gateway
from bh_sim.boundary.contracts import (
    CommandRequest,
    CreateDraftParameters,
    DraftListDto,
    DraftSummaryDto,
    ListDraftsParameters,
)
from bh_sim.boundary.json_codec import boundary_from_json, boundary_json


def test_dw2_command_shapes_match_frozen_fixtures() -> None:
    fixtures = json.loads((Path(__file__).parent / "fixtures/dw2/commands.json").read_text())
    values = {
        "create": CommandRequest(
            "draft.create", "dw2:create:1", "fixture-owner", CreateDraftParameters("Fixture draft")
        ),
        "list": CommandRequest("draft.list", "dw2:list:1", "fixture-owner", ListDraftsParameters()),
        "catalog": DraftListDto(
            (DraftSummaryDto("Fixture draft", 1, "2026-09-11T00:00:00+00:00"),)
        ),
    }
    for name, value in values.items():
        assert json.loads(boundary_json(value)) == fixtures[name]
        assert boundary_from_json(json.dumps(fixtures[name])) == value
    summary = DraftSummaryDto("Fixture draft", 1, "2026-09-11T00:00:00+00:00")
    with pytest.raises(FrozenInstanceError):
        setattr(summary, "revision", 2)  # noqa: B010 - intentionally exercise frozen runtime guard
    fixtures["create"]["parameters"]["approve"] = True
    with pytest.raises(ValueError):
        boundary_from_json(json.dumps(fixtures["create"]))


def test_catalog_corruption_returns_visible_diagnostic(tmp_path: Path) -> None:
    gateway = create_preview_gateway(tmp_path)
    (tmp_path / "drafts/corrupt.r000001.json").write_text("not JSON")
    outcome = gateway.dispatch(
        CommandRequest("draft.list", "corrupt-catalog", "owner", ListDraftsParameters())
    )
    assert outcome.disposition == "REJECTED"
    assert outcome.data is None
    assert outcome.diagnostics[0].code == "INVALID_COMMAND"
    assert "corrupt.r000001.json" not in boundary_json(outcome)
