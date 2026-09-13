"""Reproduce bounded DW0 observations without touching the user's runtime store.

Run from the repository root with its existing API test dependencies. Inputs are
the illustrative fixture in tests/test_api.py; its numerical outputs are not
scientific evidence. HTTP calls use an in-process TestClient and write only to an
automatically removed temporary directory. Output describes observed behaviour,
not desired acceptance criteria. No network server or production migration runs.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from bh_sim.api import create_app
from bh_sim.api.adapter import draft_to_contract
from bh_sim.api.schemas import PfdDraftDto
from bh_sim.core.json_codec import contract_digest
from tests.test_api import draft_payload


def main() -> None:
    """Print hash/admission/status observations for the unchanged browser fixture."""
    payload = draft_payload()
    base_hash = contract_digest(
        draft_to_contract(PfdDraftDto.model_validate(payload)).revision.case
    )
    for edit in ("move", "label"):
        changed = deepcopy(payload)
        if edit == "move":
            changed["nodes"][0]["position"]["x"] = 250
        else:
            changed["nodes"][0]["data"]["label"] = "Renamed feed"
        changed_hash = contract_digest(
            draft_to_contract(PfdDraftDto.model_validate(changed)).revision.case
        )
        print(f"{edit}_changes_case_hash={base_hash != changed_hash}")

    with TemporaryDirectory(prefix="bh-dw0-probe-") as temporary:
        root = Path(temporary)
        with TestClient(create_app(root)) as client:
            endpoint = "/api/v1alpha/drafts/thermal-loop-concept"
            response = client.post(endpoint + "/runs", json=payload)
            print(f"run_without_prior_validate_http={response.status_code}")
            print(f'run_response_fields={sorted(response.json()["data"])}')
            before = len(list((root / "contracts" / "artifacts").rglob("*.json")))
            malformed = deepcopy(payload)
            malformed["nodes"][0]["data"]["parameters"]["temperature"]["quantity"]["unit"] = (
                "unreviewed"
            )
            rejected = client.post(endpoint + "/runs", json=malformed)
            after = len(list((root / "contracts" / "artifacts").rglob("*.json")))
            print(
                f"unadaptable_run_http={rejected.status_code}, new_core_artifacts={after - before}"
            )


if __name__ == "__main__":
    main()
