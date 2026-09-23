"""AI-001/003, UIX-AI-001: observable authority and explicit-context behavior."""

from __future__ import annotations

import hashlib
import json

import pytest
from harness import ROOT, SECRET, codes, contract, plain, response
from oracles import approved, contains_no_secret, unchanged


def ready(client, profile="REVIEW"):
    client.seed()
    client.configure()
    session = client.session(profile)
    return client.send(session, response())


def test_send_requires_explicit_provider_configuration(client):
    client.seed()
    session = client.session()
    outcome = client.call(
        "ai.session.send", "AiSendParameters", session["session_id"], session["context_hash"]
    )
    assert outcome.disposition == "REJECTED"
    assert "PROVIDER_NOT_CONFIGURED" in codes(outcome)
    assert not client.transport.calls


def test_review_requires_approval_and_applies_exact_change_atomically(client):
    session = ready(client)
    before = client.head()
    assert session["proposals"][-1]["status"] == "PROPOSED"
    assert session["proposals"][-1]["schema_version"] == "bh-ai-proposal-v1"
    denied = client.proposal_action("apply", session)
    assert denied.disposition == "REJECTED" and "APPROVAL_REQUIRED" in codes(denied)
    unchanged(before, client.head())
    accepted = client.proposal_action("approve", session)
    assert accepted.disposition == "COMPLETED"
    approved(plain(accepted.data)["proposals"][-1])
    applied = client.proposal_action("apply", plain(accepted.data))
    assert applied.disposition == "COMPLETED"
    after = client.head()
    assert len(after["entries"]) == len(before["entries"]) + 1
    heater = next(
        n for n in after["document"]["draft"]["equipment"] if n["object_id"] == "heater-1"
    )
    assert heater["parameters"] == [{"name": "duty", "quantity": {"value": 600_000, "unit": "W"}}]
    unchanged(before["document"]["draft"]["connections"], after["document"]["draft"]["connections"])
    export = client.export(session)
    assert any(
        r["kind"] == "human_decision" and r["actor_id"] == "human:reviewer"
        for r in export["records"]
    )


def test_rejection_retains_proposal_without_editing_source(client):
    session = ready(client)
    before = client.head()
    rejected = client.proposal_action("reject", session)
    assert rejected.disposition == "COMPLETED"
    assert plain(rejected.data)["proposals"][-1]["status"] == "REJECTED"
    unchanged(before, client.head())
    assert client.export(session)["records"]


def test_edit_invalidates_approval_and_retains_original_proposal(client):
    session = ready(client)
    approved_session = plain(client.proposal_action("approve", session).data)
    original = approved_session["proposals"][-1]
    edit = contract(
        "AiParameterChange",
        "heater-1",
        "duty",
        contract("QuantityDto", 500_000, "W"),
        contract("QuantityDto", 650_000, "W"),
    )
    edited = client.ok(
        "ai.proposal.edit",
        "AiProposalEditParameters",
        client.proposal_target(approved_session),
        (edit,),
    )
    assert edited["proposals"][-1]["status"] == "PROPOSED"
    assert edited["proposals"][-1]["proposal_hash"] != original["proposal_hash"]
    assert original in edited["proposals"]
    assert "APPROVAL_REQUIRED" in codes(client.proposal_action("apply", edited))


def test_stale_approval_cannot_overwrite_a_new_source_head(client):
    session = ready(client)
    session = plain(client.proposal_action("approve", session).data)
    edit = contract("ConfigureInputEdit", "heater-1", "duty", "550000", "W")
    client.ok("history.edit", "HistoryEditParameters", client.target(), edit)
    current = client.head()
    denied = client.proposal_action("apply", session)
    assert denied.disposition == "REJECTED" and "STALE_PROPOSAL" in codes(denied)
    unchanged(current, client.head())


@pytest.mark.parametrize("extra", ["approved_by", "status", "command", "undeclared_field"])
def test_provider_cannot_smuggle_authority_or_unreviewed_fields(client, extra):
    client.seed()
    client.configure()
    before = client.head()
    payload = response()
    payload[extra] = "human:reviewer" if extra == "approved_by" else "APPROVED"
    session = client.send(client.session(), payload)
    assert session["state"] == "FAILED"
    assert "PROVIDER_OUTPUT_INVALID" in codes(session)
    unchanged(before, client.head())


def test_ai_actor_cannot_approve_a_review_proposal(client):
    session = ready(client)
    result = client.proposal_action("approve", session, actor="ai:participant")
    assert result.disposition == "REJECTED" and "FORBIDDEN_AUTHORITY" in codes(result)
    assert client.inspect(session)["proposals"][-1]["status"] == "PROPOSED"


def test_narrative_profile_survives_restart_and_cannot_be_hidden(client):
    session = ready(client, "NARRATIVE")
    assert session["profile"] == "NARRATIVE"
    client.close()
    reopened = client.inspect(session)
    assert reopened["profile"] == "NARRATIVE"
    # Calling a command with a Review envelope does not relabel a Narrative session.
    result = client.call(
        "ai.exploration.adopt",
        "AiAdoptParameters",
        session["session_id"],
        "narrative:unapproved",
        client.target(),
    )
    assert result.disposition == "REJECTED"
    assert {"NARRATIVE_PROMOTION_FORBIDDEN", "NOT_FOUND"} & codes(result)


def test_preview_freezes_exact_attachment_and_selected_context(client, tmp_path):
    client.seed()
    client.configure()
    path = tmp_path / "chosen.txt"
    original = (ROOT / "fixtures/evidence.txt").read_bytes()
    path.write_bytes(original)
    context = client.preview(attachments=(path,))
    assert context["selected_ids"] == ["heater-1"]
    assert context["attachments"][0]["text"] == original.decode()
    assert context["attachments"][0]["source_hash"] == hashlib.sha256(original).hexdigest()
    extraction = context["attachments"][0]["extraction"]
    assert extraction["extractor_id"] and extraction["extractor_version"]
    assert extraction["page_count"] == 0
    assert context["attachments"][0]["text_hash"] == hashlib.sha256(original).hexdigest()
    path.write_text("CHANGED AFTER PREVIEW — MUST NOT BE SENT")
    session = client.session(context=context)
    completed = client.send(session, response(kind="explanation"))
    body = json.dumps(client.transport.generations[-1]["body"])
    assert "TEST FIXTURE ONLY" in body
    assert "CHANGED AFTER PREVIEW" not in body
    assert str(tmp_path) not in body
    assert completed["context_hash"] == context["context_hash"]
    contains_no_secret(client.export(completed), SECRET)


def test_stale_context_hash_is_rejected_before_transmission(client):
    client.seed()
    client.configure()
    session = client.session()
    denied = client.call("ai.session.send", "AiSendParameters", session["session_id"], "0" * 64)
    assert denied.disposition == "REJECTED" and "STALE_CONTEXT" in codes(denied)
    assert not client.transport.calls


def test_tab_switch_cannot_replace_the_approved_source(client):
    client.seed()
    client.configure()
    session = client.session()
    client.seed("unselected-second-case")
    completed = client.send(session, response())
    assert completed["source_draft_id"] == "dw6-baseline"
    assert "unselected-second-case" not in json.dumps(client.transport.generations[-1]["body"])


def test_missing_or_cross_case_selection_is_rejected(client):
    client.seed()
    outcome = client.call(
        "ai.context.preview", "AiContextParameters", client.target(), ("not-in-this-case",), ()
    )
    assert outcome.disposition == "REJECTED"
    assert not client.transport.calls


def test_injection_attachment_cannot_grant_tools_or_modify_baseline(client):
    client.seed()
    client.configure()
    before = client.head()
    context = client.preview(attachments=(ROOT / "fixtures/injection.md",))
    payload = response()
    payload["requested_tools"] = ["read_all_files", "approve_case"]
    session = client.send(client.session(context=context), payload)
    assert {"TOOL_NOT_ALLOWED", "PROVIDER_OUTPUT_INVALID"} & codes(session)
    unchanged(before, client.head())
    assert session["ledger"]["runs"] == 0
    contains_no_secret(client.export(session), SECRET)


@pytest.mark.parametrize("filename,accepted", [("text.pdf", True), ("scan.pdf", False)])
def test_pdf_attachment_uses_local_text_or_reports_ocr_requirement(client, filename, accepted):
    client.seed()
    result = client.call(
        "ai.context.preview",
        "AiContextParameters",
        client.target(),
        ("heater-1",),
        (str(ROOT / "fixtures" / filename),),
    )
    assert not client.transport.calls
    if accepted:
        assert result.disposition == "COMPLETED"
        assert "DW6 synthetic PDF" in plain(result.data)["attachments"][0]["text"]
    else:
        assert result.disposition == "REJECTED"
        assert "DOCUMENT_TEXT_UNAVAILABLE" in codes(result)


def test_oversized_attachment_is_rejected_without_truncation(client, tmp_path):
    client.seed()
    path = tmp_path / "too-large.txt"
    path.write_bytes(b"x" * 200_001)
    outcome = client.call(
        "ai.context.preview", "AiContextParameters", client.target(), ("heater-1",), (str(path),)
    )
    assert outcome.disposition == "REJECTED" and "DOCUMENT_LIMIT_EXCEEDED" in codes(outcome)
    assert not client.transport.calls


def test_unknown_structured_claim_is_flagged_without_becoming_a_result(client):
    client.seed()
    client.configure()
    before = client.protected()
    payload = response(kind="explanation")
    payload["claims"] = [
        {"artifact_id": "invented:run", "field": "temperature", "value": 999, "unit": "K"}
    ]
    session = client.send(client.session(), payload)
    assert "UNVERIFIED_CLAIM" in session["responses"][-1]["flags"]
    unchanged(before, client.protected())
    flagged = client.ok(
        "ai.response.flag",
        "AiResponseFlagParameters",
        session["session_id"],
        session["responses"][-1]["response_id"],
        "Prose contradicts evidence",
    )
    assert "HUMAN_FLAGGED" in flagged["responses"][-1]["flags"]


@pytest.mark.worker
def test_known_artifact_contradiction_is_flagged_and_artifact_stays_authoritative(client):
    client.seed()
    client.configure()
    run = client.baseline_run()
    before = client.protected()
    context = client.preview(selected=("heater-1", run["run_id"]))
    payload = response(kind="explanation")
    payload["claims"] = [
        {
            "artifact_id": run["run_id"],
            "field": "/unit_evaluations/1/output_port_values/0/state/thermo/temperature/value",
            "value": 999,
            "unit": "K",
        }
    ]
    session = client.send(client.session(context=context), payload)
    assert "CONTRADICTORY_CLAIM" in session["responses"][-1]["flags"]
    unchanged(before, client.protected())


def test_inconsistent_before_value_cannot_partially_apply_a_multi_change_proposal(client):
    client.seed()
    client.configure()
    before = client.head()
    payload = response()
    payload["changes"].append(
        {
            "object_id": "source-1",
            "parameter": "temperature",
            "before": {"value": 999, "unit": "K"},
            "after": {"value": 310, "unit": "K"},
        }
    )
    session = client.send(client.session(), payload)
    assert session["state"] == "FAILED" and "PROVIDER_OUTPUT_INVALID" in codes(session)
    unchanged(before, client.head())
