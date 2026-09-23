"""Actual OpenAI adapter serialization and errors through controlled HTTP transport."""

from __future__ import annotations

import json

import httpx
import pytest
from harness import MODEL, SECRET, codes, response
from oracles import contains_no_secret


def prepare(client):
    client.seed()
    client.configure()
    return client.session()


def test_real_adapter_uses_counting_strict_schema_and_no_remote_state(client):
    session = prepare(client)
    result = client.send(session, response(kind="explanation"))
    assert result["state"] == "REVIEW_READY"
    assert len(client.transport.generations) == 1
    paths = [call["path"] for call in client.transport.calls]
    assert paths == ["/v1/responses/input_tokens", "/v1/responses"]
    request = client.transport.generations[0]
    body = request["body"]
    assert body["model"] == MODEL
    assert body["store"] is False and body.get("background", False) is False
    assert body.get("stream", False) is False
    assert body.get("truncation", "disabled") == "disabled"
    assert not body.get("tools") and "previous_response_id" not in body
    assert body["text"]["format"]["type"] == "json_schema"
    assert body["text"]["format"]["strict"] is True
    assert 0 < body["max_output_tokens"] <= 4096
    assert request["authorization"] == "Bearer " + SECRET
    assert result["ledger"]["tokens_used"] == 120
    assert result["ledger"]["tokens_reserved"] == 0
    contains_no_secret(client.export(result), SECRET)


@pytest.mark.parametrize("status", [401, 429, 500, 503])
def test_http_failure_is_visible_and_never_retried(client, status):
    session = prepare(client)
    client.transport.queue({"error": {"message": "Synthetic failure"}}, status)
    result = client.send(session)
    assert result["state"] == "FAILED" and "PROVIDER_FAILURE" in codes(result)
    assert len(client.transport.generations) == 1
    assert result["ledger"]["runs"] == 0


def test_lost_provider_acknowledgement_keeps_reservation_and_never_replays(client):
    session = prepare(client)
    client.transport.queue(httpx.ReadTimeout("Synthetic lost acknowledgement"))
    failed = client.send(session)
    assert failed["state"] == "FAILED"
    assert failed["ledger"]["tokens_reserved"] > 0
    count = len(client.transport.generations)
    client.close()
    reopened = client.inspect(session)
    assert reopened["ledger"]["tokens_reserved"] == failed["ledger"]["tokens_reserved"]
    assert len(client.transport.generations) == count


@pytest.mark.parametrize(
    "payload",
    [
        "not json",
        "{",
        '{"schema_version":"wrong"}',
        '{"schema_version":"bh-ai-provider-output-v1","x":NaN}',
    ],
)
def test_malformed_or_wrong_version_response_is_not_a_proposal(client, payload):
    result = client.send(prepare(client), payload)
    assert result["state"] == "FAILED"
    assert "PROVIDER_OUTPUT_INVALID" in codes(result)
    assert not result["proposals"]


def test_refusal_has_no_proposal_or_run(client):
    session = prepare(client)
    payload = {
        "object": "response",
        "id": "resp_refusal",
        "status": "completed",
        "model": MODEL,
        "usage": {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120},
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "refusal", "refusal": "Synthetic refusal"}],
            }
        ],
    }
    result = client.send(session, payload)
    assert result["state"] == "FAILED" and "PROVIDER_REFUSED" in codes(result)
    assert not result["proposals"] and result["ledger"]["runs"] == 0


def test_incomplete_response_is_not_applied(client):
    session = prepare(client)
    payload = {
        "object": "response",
        "id": "resp_partial",
        "status": "incomplete",
        "model": MODEL,
        "incomplete_details": {"reason": "max_output_tokens"},
        "output": [],
        "usage": {"input_tokens": 100, "output_tokens": 4096, "total_tokens": 4196},
    }
    result = client.send(session, payload)
    assert result["state"] == "FAILED" and "PROVIDER_OUTPUT_INVALID" in codes(result)
    assert not result["proposals"]


def test_missing_usage_is_unknown_not_zero(client):
    session = prepare(client)
    client.transport.include_usage = False
    result = client.send(session, response())
    assert result["state"] == "FAILED" and "PROVIDER_USAGE_UNKNOWN" in codes(result)
    assert result["ledger"]["tokens_reserved"] > 0
    assert result["ledger"]["uncertain_actions"]


def test_provider_cannot_silently_substitute_a_model(client):
    session = prepare(client)
    client.transport.return_model = "unrequested-model"
    result = client.send(session, response())
    assert result["state"] == "FAILED" and "PROVIDER_MODEL_MISMATCH" in codes(result)
    assert not result["proposals"]


@pytest.mark.parametrize("remember", [False, True])
def test_key_storage_is_explicit_and_never_part_of_project_files(client, remember):
    client.seed()
    settings = client.configure(remember=remember)
    assert settings["remembered"] is remember
    assert (client.credentials.values.get("openai") == SECRET) is remember
    assert SECRET not in json.dumps(settings)
    for path in client.root.rglob("*"):
        if path.is_file():
            assert SECRET.encode() not in path.read_bytes(), f"Credential leaked to {path.name}"


def test_keychain_failure_does_not_fall_back_to_plaintext(client):
    client.seed()
    client.credentials.fail = True
    outcome = client.call(
        "ai.provider.configure", "AiProviderParameters", "openai", MODEL, SECRET, True
    )
    assert outcome.disposition == "REJECTED"
    for path in client.root.rglob("*"):
        if path.is_file():
            assert SECRET.encode() not in path.read_bytes()


def test_duplicate_send_is_deduplicated_across_restart(client):
    session = prepare(client)
    client.transport.queue(response())
    arguments = (session["session_id"], session["context_hash"])
    client.ok("ai.session.send", "AiSendParameters", *arguments, request_id="send:durable")
    result = client.wait(session)
    client.close()
    client.ok("ai.session.send", "AiSendParameters", *arguments, request_id="send:durable")
    assert len(client.transport.generations) == 1
    assert client.inspect(session)["responses"] == result["responses"]
    conflict = client.call(
        "ai.session.send",
        "AiSendParameters",
        session["session_id"],
        "0" * 64,
        request_id="send:durable",
    )
    assert conflict.disposition == "REJECTED"
    assert "REQUEST_ID_CONFLICT" in codes(conflict)
