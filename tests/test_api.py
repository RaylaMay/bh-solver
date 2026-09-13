from __future__ import annotations

from copy import deepcopy

from fastapi.testclient import TestClient

from bh_sim.api import create_app


def draft_payload() -> dict:
    def node(identifier: str, kind: str, parameters: dict) -> dict:
        return {
            "id": identifier,
            "type": "equipment",
            "position": {"x": 0, "y": 0},
            "data": {
                "label": identifier,
                "kind": kind,
                "status": "draft",
                "validity": "UNKNOWN",
                "parameters": parameters,
            },
        }

    def parameter(label: str, value: float, unit: str) -> dict:
        return {"label": label, "quantity": {"value": value, "unit": unit}}

    return {
        "schemaVersion": "v1alpha",
        "draftId": "thermal-loop-concept",
        "revision": 1,
        "baseCaseId": None,
        "updatedAt": "2026-08-27T00:00:00Z",
        "nodes": [
            node(
                "source-1",
                "source",
                {
                    "temperature": parameter("Temperature", 300, "K"),
                    "pressure": parameter("Pressure", 101325, "Pa"),
                    "massFlow": parameter("Mass flow", 1, "kg/s"),
                },
            ),
            node("heater-1", "heater", {"duty": parameter("Duty", 500000, "W")}),
            node(
                "radiator-1",
                "radiator",
                {
                    "targetTemperature": parameter("Target", 500, "K"),
                    "emissivity": parameter("Emissivity", 0.9, "1"),
                },
            ),
            node("sink-1", "sink", {}),
        ],
        "edges": [
            {
                "id": "edge-1",
                "source": "source-1",
                "sourceHandle": "out-0",
                "target": "heater-1",
                "targetHandle": "in-0",
            },
            {
                "id": "edge-2",
                "source": "heater-1",
                "sourceHandle": "out-0",
                "target": "radiator-1",
                "targetHandle": "in-0",
            },
            {
                "id": "edge-3",
                "source": "radiator-1",
                "sourceHandle": "out-0",
                "target": "sink-1",
                "targetHandle": "in-0",
            },
        ],
    }


def test_pfd_save_is_idempotent_and_revisions_are_immutable(tmp_path) -> None:
    client = TestClient(create_app(tmp_path))
    draft = draft_payload()
    first = client.put("/api/v1alpha/drafts/thermal-loop-concept", json=draft).json()["data"]
    second = client.put("/api/v1alpha/drafts/thermal-loop-concept", json=draft).json()["data"]
    assert first == second
    changed = deepcopy(draft)
    changed["nodes"][1]["data"]["parameters"]["duty"]["quantity"]["value"] = 600000
    third = client.put("/api/v1alpha/drafts/thermal-loop-concept", json=changed).json()["data"]
    assert third["revision"] == 2
    assert len(list((tmp_path / "drafts").glob("*.json"))) == 2
    loaded = client.get("/api/v1alpha/drafts/thermal-loop-concept").json()["data"]
    assert loaded == third


def test_pfd_validates_runs_and_returns_auditable_overlays(tmp_path) -> None:
    client = TestClient(create_app(tmp_path))
    draft = draft_payload()
    validation = client.post(
        "/api/v1alpha/drafts/thermal-loop-concept/validate", json=draft
    ).json()["data"]
    assert validation == {"valid": True, "degreesOfFreedom": 0, "diagnostics": []}

    response = client.post("/api/v1alpha/drafts/thermal-loop-concept/runs", json=draft)
    assert response.status_code == 200
    run = response.json()["data"]
    assert run["converged"]
    assert run["conservationClosed"]
    assert any(item["code"] == "REFERENCE_FIXTURE_ONLY" for item in run["diagnostics"])
    assert {item["nodeId"] for item in run["nodeResults"]} == {
        "source-1",
        "heater-1",
        "radiator-1",
        "sink-1",
    }
    radiator = next(item for item in run["nodeResults"] if item["nodeId"] == "radiator-1")
    assert radiator["status"] == "warning"
    assert any(metric["label"] == "Required Planform Area" for metric in radiator["metrics"])

    repeated = deepcopy(draft)
    repeated["updatedAt"] = "2026-08-27T00:05:00Z"
    repeated["nodes"][0]["data"].update(
        {
            "status": "valid",
            "validity": "VALID",
            "metrics": [{"label": "T", "displayValue": "300 K"}],
        }
    )
    repeated_run = client.post(
        "/api/v1alpha/drafts/thermal-loop-concept/runs", json=repeated
    ).json()["data"]
    assert repeated_run["revision"] == run["revision"] == 1


def test_failed_draft_returns_subject_specific_validation(tmp_path) -> None:
    client = TestClient(create_app(tmp_path))
    draft = draft_payload()
    draft["edges"] = draft["edges"][:-1]
    validation = client.post(
        "/api/v1alpha/drafts/thermal-loop-concept/validate", json=draft
    ).json()["data"]
    assert not validation["valid"]
    assert validation["degreesOfFreedom"] == 1
    assert validation["diagnostics"][0]["subjectId"] == "sink-1"
