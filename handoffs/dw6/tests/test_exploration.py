"""UIX-AI-001/AUDIT-001: bounded actual worker execution and isolated ownership."""

from __future__ import annotations

import json
import os
import signal

import pytest
from harness import LIMITS, codes, contract, response
from oracles import budget_within, unchanged


def prepare(client):
    client.seed()
    client.configure()
    return client.session("EXPLORATION")


def execute(client, session, payload=None, limits=None):
    client.transport.queue(payload or response())
    plan = client.plan(session, limits=limits)
    client.start(session, plan=plan)
    return client.wait(session)


def artifact_objects(export):
    return [
        (item, json.loads(item["content_utf8"]))
        for item in export["artifacts"]
        if item["media_type"] == "application/json"
    ]


@pytest.mark.worker
def test_real_worker_result_matches_hand_fixture_and_keeps_source_unchanged(client, monkeypatch):
    session = prepare(client)
    baseline = client.baseline_run()
    before = client.protected()
    assert before["last_valid"]["run_id"] == baseline["run_id"]
    pid = client.runtime.worker_pid
    assert type(pid) is int and pid != os.getpid() and pid > 0
    os.kill(pid, 0)
    from bh_sim.engine import AcyclicRunEngine

    def forbid_in_process(*args, **kwargs):
        raise AssertionError("Scientific execution occurred in the desktop process")

    monkeypatch.setattr(AcyclicRunEngine, "run", forbid_in_process)
    result = execute(client, session)
    assert result["state"] == "COMPLETED"
    assert result["ledger"]["schema_version"] == "bh-ai-budget-v1"
    assert len(result["candidates"]) == result["ledger"]["runs"] == 1
    candidate = result["candidates"][0]
    assert candidate["case_id"] != "case:dw6-baseline"
    assert candidate["profile"] == "EXPLORATION"
    unchanged(before, client.protected())
    export = client.export(result)
    runs = [
        (item, value)
        for item, value in artifact_objects(export)
        if value.get("$type") == "RunResult"
    ]
    assert len(runs) == 1, "Need the real canonical run, not just an AI summary"
    artifact, run = runs[0]
    assert artifact["sha256"] == candidate["artifact_hash"]
    assert run["run_id"]["value"] == candidate["run_id"]
    assert run["case_id"]["value"] == candidate["case_id"]
    assert [
        run[k].upper()
        for k in ("convergence", "closure", "physical_validity", "correlation_validity")
    ] == ["CONVERGED", "PASSED", "VALID", "VALID"]
    heater = next(u for u in run["unit_evaluations"] if u["unit_id"]["value"] == "unit:heater-1")
    stream = next(p for p in heater["output_port_values"] if p["$type"] == "MaterialPortValue")
    assert stream["state"]["thermo"]["temperature"]["value"] == pytest.approx(900, abs=1e-8)
    # 300 K + 600,000 W / (1 kg/s * 1000 J/kg/K), independent literal in README.
    cases = [
        value for _, value in artifact_objects(export) if value.get("$type") == "CaseDefinition"
    ]
    assert any(
        v["case_id"]["value"] == candidate["case_id"] and v["ai_profile"].upper() == "EXPLORATION"
        for v in cases
    )
    events = [json.loads(r["body_json"]) for r in export["records"] if r["kind"] == "run"]
    assert any(e["worker_pid"] == pid and e["run_id"] == candidate["run_id"] for e in events)
    inspected = client.ok("run.inspect", "InspectRunParameters", candidate["run_id"])
    assert inspected["run_id"] == candidate["run_id"]
    client.close()
    reopened = client.inspect(result)
    assert reopened["profile"] == "EXPLORATION"
    assert reopened["candidates"] == result["candidates"]


def test_plan_and_session_creation_do_not_run_or_send(client):
    session = prepare(client)
    client.plan(session)
    assert not client.transport.calls
    assert client.inspect(session)["ledger"]["runs"] == 0


@pytest.mark.parametrize("forgery", ["hash", "actor"])
def test_plan_start_requires_exact_human_authorization(client, forgery):
    session = prepare(client)
    plan = client.plan(session)
    result = client.call(
        "ai.exploration.start",
        "AiPlanTarget",
        session["session_id"],
        plan["plan_id"],
        "0" * 64 if forgery == "hash" else plan["plan_hash"],
        actor="ai:participant" if forgery == "actor" else "human:reviewer",
    )
    assert result.disposition == "REJECTED"
    assert not client.transport.calls
    assert client.inspect(session)["ledger"]["runs"] == 0


@pytest.mark.parametrize("duty", [400_000, 700_000])
@pytest.mark.worker
def test_inclusive_parameter_bounds_are_accepted(client, duty):
    result = execute(client, prepare(client), response(duty=duty))
    assert result["state"] == "COMPLETED" and result["ledger"]["runs"] == 1
    assert result["candidates"][0]["changes"][0]["after"]["value"] == duty


@pytest.mark.parametrize(
    "mutation,expected",
    [
        ("low", "PARAMETER_OUT_OF_BOUNDS"),
        ("high", "PARAMETER_OUT_OF_BOUNDS"),
        ("unit", "INVALID_UNITS"),
        ("other_parameter", "PARAMETER_OUT_OF_SCOPE"),
        ("topology", "PROVIDER_OUTPUT_INVALID"),
        ("backend", "PROVIDER_OUTPUT_INVALID"),
    ],
)
def test_unapproved_changes_never_reach_the_worker(client, mutation, expected):
    session = prepare(client)
    before = client.protected()
    payload = response()
    change = payload["changes"][0]
    if mutation == "low":
        change["after"]["value"] = 399_999
    elif mutation == "high":
        change["after"]["value"] = 700_001
    elif mutation == "unit":
        change["after"]["unit"] = "Pa"
    elif mutation == "other_parameter":
        change["object_id"], change["parameter"] = "source-1", "temperature"
    else:
        change[mutation] = "unapproved"
    result = execute(client, session, payload)
    assert expected in codes(result)
    assert result["ledger"]["runs"] == 0
    unchanged(before, client.protected())


@pytest.mark.parametrize(
    "field,value",
    [
        ("participants", 2),
        ("iterations", 6),
        ("runs", 6),
        ("elapsed_seconds", 301),
        ("tokens", 50_001),
        ("tool_calls", 21),
        ("retries", 1),
    ],
)
def test_approved_budget_ceiling_cannot_be_raised(client, field, value):
    session = prepare(client)
    limits = {**LIMITS, field: value}
    try:
        budget = contract("AiBudget", **limits)
    except ValueError:
        return  # Fail-closed constructor validation is an allowed public boundary.
    ranges = (
        contract(
            "AiRange",
            "heater-1",
            "duty",
            contract("QuantityDto", 400_000, "W"),
            contract("QuantityDto", 700_000, "W"),
        ),
    )
    outcome = client.call(
        "ai.exploration.plan", "AiPlanParameters", session["session_id"], ranges, budget
    )
    assert outcome.disposition == "REJECTED"
    assert not client.transport.calls


@pytest.mark.worker
def test_iteration_budget_counts_rejected_candidates_and_stops_at_five(client):
    session = prepare(client)
    for _ in range(6):
        client.transport.queue(response(duty=900_000, done=False))
    client.start(session)
    result = client.wait(session)
    assert result["state"] == "LIMIT_REACHED"
    assert result["ledger"]["iterations"] == len(client.transport.generations) == 5
    assert result["ledger"]["runs"] == 0
    assert len(result["candidates"]) == 5
    budget_within(result["ledger"], LIMITS)


@pytest.mark.worker
def test_run_budget_is_session_wide_and_attempt_ids_are_unique(client):
    session = prepare(client)
    for _ in range(6):
        client.transport.queue(response(done=False))
    client.start(session)
    result = client.wait(session, timeout=30)
    assert result["state"] == "LIMIT_REACHED" and result["ledger"]["runs"] == 5
    identifiers = [c["run_id"] for c in result["candidates"]]
    assert len(identifiers) == len(set(identifiers)) == 5
    assert len(client.transport.generations) == 5
    budget_within(result["ledger"], LIMITS)


@pytest.mark.worker
def test_lower_run_limit_stops_before_another_provider_iteration(client):
    session = prepare(client)
    client.transport.queue(response(done=False))
    client.transport.queue(response())
    client.start(session, plan=client.plan(session, limits={**LIMITS, "runs": 1}))
    result = client.wait(session)
    assert result["state"] == "LIMIT_REACHED" and result["ledger"]["runs"] == 1
    assert len(client.transport.generations) == 1


def test_token_limit_is_reserved_before_generation(client):
    session = prepare(client)
    client.transport.input_tokens = 50_001
    result = execute(client, session)
    assert result["state"] == "LIMIT_REACHED"
    assert not client.transport.generations and result["ledger"]["runs"] == 0
    budget_within(result["ledger"], LIMITS)


@pytest.mark.worker
def test_exact_tool_limit_allows_one_complete_sequence_then_stops(client):
    session = prepare(client)
    client.transport.queue(response(done=False))
    client.transport.queue(response())
    client.start(session, plan=client.plan(session, limits={**LIMITS, "tool_calls": 3}))
    result = client.wait(session)
    assert result["state"] == "LIMIT_REACHED"
    assert result["ledger"]["tool_calls"] == 3 and result["ledger"]["runs"] == 1
    assert len(client.transport.generations) == 1


@pytest.mark.parametrize("elapsed,admitted", [(299, True), (300, False)])
@pytest.mark.worker
def test_deadline_admission_boundary(client, elapsed, admitted):
    now = [0.0]
    client.clock.monotonic = lambda: now[0]
    session = prepare(client)
    client.transport.on_generate = lambda: now.__setitem__(0, float(elapsed))
    result = execute(client, session)
    assert result["ledger"]["runs"] == int(admitted)
    assert result["state"] == ("COMPLETED" if admitted else "LIMIT_REACHED")


@pytest.mark.worker
def test_compatible_parameter_units_are_converted_before_bounds_check(client):
    session = prepare(client)
    payload = response()
    payload["changes"][0]["after"] = {"value": 600, "unit": "kW"}
    result = execute(client, session, payload)
    assert result["state"] == "COMPLETED" and result["ledger"]["runs"] == 1


def test_tool_budget_prevents_excess_requests(client):
    session = prepare(client)
    payload = response()
    payload["requested_tools"] = ["validate", "run", "inspect"] * 8
    result = execute(client, session, payload)
    assert {"BUDGET_EXHAUSTED", "TOOL_NOT_ALLOWED"} & codes(result)
    assert result["ledger"]["runs"] == 0 and result["ledger"]["tool_calls"] <= 20


def test_deadline_prevents_a_late_response_from_starting_a_run(client):
    session = prepare(client)
    client.transport.on_generate = lambda: client.clock.advance(301)
    result = execute(client, session)
    assert result["state"] == "LIMIT_REACHED" and result["ledger"]["runs"] == 0
    assert len(client.transport.generations) == 1


def test_cancel_discards_late_proposal_effects_and_remains_auditable(client):
    session = prepare(client)
    before = client.protected()
    client.transport.release.clear()
    client.transport.queue(response())
    client.start(session)
    assert client.transport.entered.wait(3)
    client.ok("ai.session.cancel", "AiSessionTarget", session["session_id"])
    client.transport.release.set()
    result = client.wait(session, {"CANCELLED"})
    assert result["ledger"]["runs"] == 0
    unchanged(before, client.protected())
    assert client.export(result)["records"]


@pytest.mark.worker
def test_failed_scientific_trial_preserves_existing_last_valid_result(client):
    session = prepare(client)
    client.baseline_run()
    before = client.protected()
    assert before["last_valid"] is not None
    ranges = (
        contract(
            "AiRange",
            "source-1",
            "temperature",
            contract("QuantityDto", 40, "K"),
            contract("QuantityDto", 350, "K"),
        ),
    )
    plan = client.plan(session, ranges=ranges)
    payload = response()
    payload["changes"] = [
        {
            "object_id": "source-1",
            "parameter": "temperature",
            "before": {"value": 300, "unit": "K"},
            "after": {"value": 50, "unit": "K"},
        }
    ]
    client.transport.queue(payload)
    client.start(session, plan=plan)
    result = client.wait(session)
    assert result["ledger"]["runs"] == 1
    candidate = result["candidates"][0]
    assert candidate["run_id"] and candidate["artifact_hash"]
    run = client.ok("run.inspect", "InspectRunParameters", candidate["run_id"])
    assert run["convergence"] == "FAILED" and run["physical_validity"] == "INVALID"
    unchanged(before, client.protected())


@pytest.mark.worker
def test_subsequent_turn_receives_only_approved_session_feedback(client):
    session = prepare(client)
    client.transport.queue(response(done=False))
    client.transport.queue(response(duty=650_000))
    client.start(session)
    result = client.wait(session)
    assert len(result["candidates"]) == len(client.transport.generations) == 2
    second_input = json.dumps(client.transport.generations[1]["body"]["input"])
    assert result["candidates"][0]["run_id"] in second_input
    assert "EXPLORATION" in second_input
    assert "600000" in second_input or "600,000" in second_input
    assert result["candidates"][1]["run_id"] not in second_input


@pytest.mark.worker
def test_token_usage_accumulates_across_turns(client):
    session = prepare(client)
    client.transport.queue(response(done=False))
    client.transport.queue(response())
    plan = client.plan(session, limits={**LIMITS, "tokens": 120})
    client.start(session, plan=plan)
    result = client.wait(session)
    assert result["state"] == "LIMIT_REACHED"
    assert result["ledger"]["tokens_used"] == 120
    assert len(client.transport.generations) == 1
    assert client.transport.generations[0]["body"]["max_output_tokens"] <= 20


@pytest.mark.worker
def test_source_edits_continue_snapshot_and_adoption_requires_fresh_review(client):
    session = prepare(client)
    client.transport.release.clear()
    client.transport.queue(response())
    client.start(session)
    assert client.transport.entered.wait(3)
    edit = contract("ConfigureInputEdit", "heater-1", "duty", "550000", "W")
    client.ok("history.edit", "HistoryEditParameters", client.target(), edit)
    current = client.protected()
    client.transport.release.set()
    result = client.wait(session)
    assert result["state"] == "COMPLETED" and result["source_stale"] is True
    unchanged(current, client.protected())
    adopted = client.ok(
        "ai.exploration.adopt",
        "AiAdoptParameters",
        session["session_id"],
        result["candidates"][0]["candidate_id"],
        client.target(),
    )
    assert adopted["profile"] == "REVIEW" and adopted["session_id"] != session["session_id"]
    assert adopted["proposals"][-1]["status"] == "PROPOSED"
    assert adopted["proposals"][-1]["changes"][0]["before"]["value"] == 550_000
    unchanged(current, client.protected())


@pytest.mark.worker
def test_worker_loss_is_retained_and_does_not_advance_original_result(client):
    session = prepare(client)
    before = client.protected()
    client.transport.release.clear()
    client.transport.queue(response())
    client.start(session)
    assert client.transport.entered.wait(3)
    pid = client.runtime.worker_pid
    assert pid != os.getpid() and pid > 0
    os.kill(pid, signal.SIGTERM)
    client.transport.release.set()
    result = client.wait(session)
    assert result["state"] in {"FAILED", "INTERRUPTED"}
    unchanged(before, client.protected())
    assert client.export(result)["records"]
