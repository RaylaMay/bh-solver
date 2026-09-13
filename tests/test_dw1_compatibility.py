"""Frozen pre-DW1 behavior; fixtures are evidence, not regenerated expectations.

Only generated run identifiers and wall-clock timestamps are normalized. Canonical
fixtures retain exact JSON bytes and independently recorded SHA-256 digests.
"""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
from copy import deepcopy
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

import bh_sim
from bh_sim.api import create_app
from bh_sim.api.adapter import draft_to_contract, reference_property_package
from bh_sim.api.schemas import PfdDraftDto
from bh_sim.cli import demonstration_report
from bh_sim.core import StableId
from bh_sim.engine import AcyclicRunEngine, PropertyRegistry, reference_model_catalog
from bh_sim.persistence import canonical_json, contract_digest, contract_from_json

FIXTURES = Path(__file__).parent / "fixtures" / "dw1"
FIXED_TIME = "2026-08-27T00:00:00+00:00"
FIXED_RUN_ID = "run:00000000-0000-4000-8000-000000000000"
COMMANDS = ("solid-radiator", "droplet-radiator", "surge-buffer")


def fixture_json(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def normalized_response(response: Any) -> dict[str, Any]:
    """Replace only generated response fields, checking their original syntax."""

    payload = response.json()
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        data = payload["data"]
        for key in ("updatedAt", "completedAt"):
            if key in data:
                assert datetime.fromisoformat(data[key].replace("Z", "+00:00")).tzinfo
                data[key] = FIXED_TIME
        if "runId" in data:
            assert data["runId"].startswith("run:")
            assert UUID(data["runId"].removeprefix("run:")).version == 4
            data["runId"] = FIXED_RUN_ID
    return {"status": response.status_code, "body": payload}


def http_trace(root: Path, draft: dict[str, Any]) -> dict[str, Any]:
    """Exercise the existing browser workflow and its documented legacy errors."""

    client = TestClient(create_app(root))
    route = f"/api/v1alpha/drafts/{draft['draftId']}"
    trace = {
        "health": normalized_response(client.get("/api/v1alpha/health")),
        "missing": normalized_response(client.get(route)),
        "save": normalized_response(client.put(route, json=draft)),
        "open": normalized_response(client.get(route)),
        "validate": normalized_response(client.post(f"{route}/validate", json=draft)),
    }
    initial_run = client.post(f"{route}/runs", json=draft)
    initial_run_id = initial_run.json()["data"]["runId"]
    trace["run"] = normalized_response(initial_run)
    transient = deepcopy(draft)
    transient["updatedAt"] = "2026-08-27T01:00:00Z"
    transient["revision"] = 9
    for node in transient["nodes"]:
        node["data"].update(
            status="valid", validity="VALID", metrics=[{"label": "T", "displayValue": "300 K"}]
        )
    trace["save_transient"] = normalized_response(client.put(route, json=transient))
    repeated_run = client.post(f"{route}/runs", json=transient)
    # An explicit second legacy Run remains a distinct attempt, even with the
    # same saved content. Normalizing the trace must not hide ID reuse.
    assert repeated_run.json()["data"]["runId"] != initial_run_id
    trace["repeat_run"] = normalized_response(repeated_run)
    changed = deepcopy(draft)
    changed["nodes"][0]["position"]["x"] += 50
    trace["save_presentation_edit"] = normalized_response(client.put(route, json=changed))
    for method, suffix in (("PUT", ""), ("POST", "/validate"), ("POST", "/runs")):
        trace[f"mismatch_{method}_{suffix}"] = normalized_response(
            client.request(method, f"/api/v1alpha/drafts/other{suffix}", json=draft)
        )
    broken = deepcopy(draft)
    broken["edges"] = broken["edges"][:-1]
    trace["unconnected_validate"] = normalized_response(
        client.post(f"{route}/validate", json=broken)
    )
    trace["unconnected_run"] = normalized_response(client.post(f"{route}/runs", json=broken))
    invalid = deepcopy(draft)
    invalid["edges"][0]["sourceHandle"] = "out-99"
    trace["invalid_handle_validate"] = normalized_response(
        client.post(f"{route}/validate", json=invalid)
    )
    trace["invalid_handle_run"] = normalized_response(client.post(f"{route}/runs", json=invalid))
    return trace


def canonical_artifacts(draft: dict[str, Any]) -> dict[str, Any]:
    """Build old persisted forms with stable generated run metadata only."""

    adapted = draft_to_contract(PfdDraftDto.model_validate(draft))
    revision = adapted.revision
    engine = AcyclicRunEngine(
        reference_model_catalog(), PropertyRegistry((reference_property_package(),))
    )
    compiled = engine.validate(revision.case, revision_id=revision.revision_id).compiled
    run = replace(
        engine.run(revision.case, revision_id=revision.revision_id),
        run_id=StableId(FIXED_RUN_ID),
        created_at=FIXED_TIME,
    )
    return {"case": revision.case, "revision": revision, "compiled": compiled, "run": run}


@pytest.mark.parametrize("scenario", ("baseline", "units_extensions", "splitter"))
def test_legacy_browser_workflow_matches_pre_extraction_fixture(
    tmp_path: Path, scenario: str
) -> None:
    draft = fixture_json(f"{scenario}.request.json")
    assert http_trace(tmp_path, draft) == fixture_json(f"{scenario}.http.json")


@pytest.mark.parametrize("scenario", ("baseline", "units_extensions", "splitter"))
def test_canonical_bytes_and_hashes_remain_exact(scenario: str) -> None:
    manifest = fixture_json("manifest.json")
    for kind, contract in canonical_artifacts(fixture_json(f"{scenario}.request.json")).items():
        filename = f"{scenario}.{kind}.canonical.json"
        encoded = (FIXTURES / filename).read_text(encoding="utf-8")
        assert canonical_json(contract) == encoded
        assert contract_digest(contract) == manifest["canonical_sha256"][filename]
        assert canonical_json(contract_from_json(encoded)) == encoded


def test_existing_browser_test_payload_remains_the_frozen_baseline() -> None:
    from tests.test_api import draft_payload

    assert draft_payload() == fixture_json("baseline.request.json")


@pytest.mark.parametrize("command", COMMANDS)
def test_legacy_cli_json_and_report_identity_remain_compatible(command: str) -> None:
    expected = (FIXTURES / f"cli.{command}.json").read_text(encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "bh_sim", command],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).parents[1] / "src")},
    )
    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout == expected
    report = demonstration_report(command)
    assert type(report) is bh_sim.CalculationReport
    assert report.to_dict() == json.loads(expected)


def test_legacy_cli_rejects_unknown_and_missing_commands() -> None:
    for arguments, fragment in (([], "required"), (["unknown"], "invalid choice")):
        result = subprocess.run(
            [sys.executable, "-m", "bh_sim", *arguments],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 2
        assert result.stdout == ""
        assert fragment in result.stderr
    with pytest.raises(ValueError, match="unknown command unknown"):
        demonstration_report("unknown")


def test_package_public_exports_retain_names_and_identity() -> None:
    expected = fixture_json("public_exports.json")
    assert bh_sim.__all__ == list(expected)
    for name, module in expected.items():
        assert getattr(bh_sim, name) is getattr(importlib.import_module(module), name)
    missing_name = "missing_public_symbol"
    with pytest.raises(AttributeError):
        getattr(bh_sim, missing_name)
