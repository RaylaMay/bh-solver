"""Persistence, source compatibility and real native interaction acceptance."""

from __future__ import annotations

import contextlib
import importlib
import io
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest
from harness import ROOT, codes, contract, response


def prepared(client):
    client.seed()
    client.configure()
    return client.session()


def test_audit_reconstructs_submission_response_and_human_disposition(client):
    session = client.send(prepared(client), response())
    client.proposal_action("reject", session)
    export = client.export(session)
    kinds = {r["kind"] for r in export["records"]}
    assert {
        "context",
        "submission",
        "reservation",
        "dispatch",
        "usage",
        "response",
        "proposal",
        "human_decision",
    } <= kinds
    client.ok("ai.session.hide", "AiSessionTarget", session["session_id"])
    retained = client.export(session)
    assert all(record in retained["records"] for record in export["records"])
    client.close()
    assert client.export(session)["records"] == retained["records"]


def test_reservation_and_approval_are_durable_before_provider_dispatch(client):
    session = prepared(client)
    captured = []
    client.transport.on_generate = lambda: captured.append(client.export(session))
    client.send(session, response())
    assert captured
    events = [r["kind"] for r in captured[0]["records"]]
    assert "submission" in events and "reservation" in events and "dispatch" in events
    assert events.index("reservation") < events.index("dispatch")


def test_audit_write_failure_prevents_provider_effect(client, monkeypatch):
    session = prepared(client)
    audit_root = (client.root / "ai-audit").resolve()
    original_open, original_os_open = io.open, os.open

    def affected(path):
        return isinstance(path, (str, bytes, os.PathLike)) and Path(
            os.fsdecode(path)
        ).resolve().is_relative_to(audit_root)

    def guarded_open(file, mode="r", *args, **kwargs):
        if affected(file) and any(x in mode for x in "wax+"):
            raise PermissionError("Synthetic audit write failure")
        return original_open(file, mode, *args, **kwargs)

    def guarded_os_open(file, flags, *args, **kwargs):
        if affected(file) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT):
            raise PermissionError("Synthetic audit write failure")
        return original_os_open(file, flags, *args, **kwargs)

    monkeypatch.setattr(io, "open", guarded_open)
    monkeypatch.setattr("builtins.open", guarded_open)
    monkeypatch.setattr(os, "open", guarded_os_open)
    result = client.call(
        "ai.session.send", "AiSendParameters", session["session_id"], session["context_hash"]
    )
    assert result.disposition == "REJECTED" and "AUDIT_WRITE_FAILED" in codes(result)
    assert not client.transport.calls


@pytest.mark.worker
@pytest.mark.parametrize("crash_point", ["provider_dispatch", "worker_admission"])
def test_process_crash_recovers_without_resend_or_run_replay(client, tmp_path, crash_point):
    assert client.runtime is not None  # Feature-specific pre-DW6 failure, before the child.
    client.close()
    launcher = importlib.import_module("bh_sim.desktop_launcher")
    assert launcher.__file__ is not None
    source_root = Path(launcher.__file__).resolve().parents[1]
    identity_file = tmp_path / "crash-identities.json"
    script = """
import json, os, signal, sys, time
from pathlib import Path
sys.path[:0] = [sys.argv[1], sys.argv[2]]
from harness import Client, response
client = Client(Path(sys.argv[3]))
client.seed()
client.configure()
session = client.session('EXPLORATION')
identity = {'session': session, 'worker_pid': client.runtime.worker_pid}
Path(sys.argv[4]).write_text(json.dumps(identity))
client.transport.queue(response())
if sys.argv[5] == 'provider_dispatch':
    client.transport.on_generate = lambda: os._exit(23)
else:
    # Stop this real synthetic worker before it can acknowledge its admitted run.
    os.kill(client.runtime.worker_pid, signal.SIGSTOP)
client.start(session)
deadline = time.monotonic() + 12
while time.monotonic() < deadline:
    client.pump()
    current = client.inspect(session)
    if sys.argv[5] == 'worker_admission' and current['ledger']['runs'] == 1:
        identity['session'] = current
        Path(sys.argv[4]).write_text(json.dumps(identity))
        os._exit(23)
    time.sleep(0.01)
raise SystemExit('Crash point was not reached')
"""
    worker_pid = None
    identity = None
    try:
        process = subprocess.run(
            [
                sys.executable,
                "-I",
                "-c",
                script,
                str(ROOT),
                str(source_root),
                str(client.root),
                str(identity_file),
                crash_point,
            ],
            env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
            capture_output=True,
            text=True,
            timeout=20,
        )
        if identity_file.exists():
            identity = json.loads(identity_file.read_text())
            worker_pid = identity["worker_pid"]
        assert process.returncode == 23, process.stdout + process.stderr
        assert identity is not None
        session = identity["session"]
        recovered = client.inspect(session)
        assert recovered["state"] == "INTERRUPTED"
        if crash_point == "provider_dispatch":
            assert recovered["ledger"]["tokens_reserved"] > 0
            assert recovered["ledger"]["runs"] == 0
        else:
            assert recovered["ledger"]["runs"] == 1
            assert len(recovered["candidates"]) == 1
            assert recovered["candidates"][0]["run_id"] == session["candidates"][0]["run_id"]
            assert recovered["candidates"][0]["run_id"]
            from PySide6.QtTest import QTest

            QTest.qWait(150)
            assert client.inspect(session)["ledger"]["runs"] == 1
        assert not client.transport.calls
        assert client.export(session)["records"]
    finally:
        # Clean up only the worker identity created by this synthetic child.
        if worker_pid is not None and worker_pid > 0 and worker_pid != os.getpid():
            with contextlib.suppress(ProcessLookupError):
                os.kill(worker_pid, signal.SIGKILL)


def test_spellcheck_suggests_corrections_without_rewriting_text(client):
    client.seed()
    client.ok("ai.dictionary.add", "AiDictionaryParameters", ("CO2", "kPa", "thermofluid"), "en")
    original = "recieve CO2 kPa thermofluid"
    result = client.ok("ai.spelling.check", "AiSpellcheckParameters", original, "en")
    assert result["text"] == original
    issue = next(i for i in result["issues"] if i["word"] == "recieve")
    assert "receive" in issue["suggestions"]
    assert not {"CO2", "kPa", "thermofluid"} & {i["word"] for i in result["issues"]}


def test_corrupt_canonical_audit_is_rejected_after_restart(client):
    session = client.send(prepared(client), response())
    export = client.export(session)
    record_hash = export["records"][-1]["record_hash"]
    client.close()
    matches = []
    for path in (client.root / "ai-audit").rglob("*.json"):
        text = path.read_text()
        if record_hash in text:
            matches.append(path)
            path.write_text(text.replace(record_hash, "0" * 64))
    assert matches, "Canonical audit bytes must be published under ai-audit"
    result = client.call("ai.session.export", "AiSessionTarget", session["session_id"])
    assert result.disposition == "REJECTED" and "AUDIT_CORRUPT" in codes(result)


@pytest.mark.parametrize("name", ["case", "revision", "run"])
def test_legacy_canonical_artifacts_keep_exact_bytes(name):
    codec = importlib.import_module("bh_sim.core.json_codec")
    data = (ROOT / "fixtures" / f"legacy-{name}.json").read_text()
    assert codec.canonical_json(codec.contract_from_json(data)) == data


@pytest.mark.parametrize("name", ["AiBudget", "AiSessionTarget", "AiProviderParameters"])
def test_new_contracts_are_frozen_and_strictly_round_trip(name):
    import dataclasses

    values = {
        "AiBudget": (),
        "AiSessionTarget": ("session:test",),
        "AiProviderParameters": ("openai", "explicit-model", "", False),
    }
    value = contract(name, *values[name])
    codec = importlib.import_module("bh_sim.boundary.json_codec")
    serialized = codec.boundary_json(value)
    assert codec.boundary_from_json(serialized) == value
    assert dataclasses.is_dataclass(value)
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(value, dataclasses.fields(value)[0].name, "modified")
    malformed = json.loads(serialized)
    malformed["unexpected_authority"] = True
    with pytest.raises((TypeError, ValueError)):
        codec.boundary_from_json(json.dumps(malformed))


@pytest.mark.native
def test_ordinary_entrypoint_calls_the_same_production_factory(client, tmp_path):
    # Resolve the required factory first, then test ordinary main in a fresh process.
    assert client.runtime is not None
    launcher = importlib.import_module("bh_sim.desktop_launcher")
    assert launcher.__file__ is not None
    source_root = Path(launcher.__file__).resolve().parents[1]
    script = """
import sys
sys.path.insert(0, sys.argv[1])
from bh_sim import desktop_launcher as launch
class Observed(Exception): pass
def observed(*args, **kwargs): raise Observed()
launch.create_workstation = observed
sys.argv = ['bh-workstation', '--data-root', sys.argv[2]]
try: launch.main()
except Observed: raise SystemExit(0)
raise SystemExit('Production main did not use the reviewed factory')
"""
    process = subprocess.run(
        [sys.executable, "-I", "-c", script, str(source_root), str(tmp_path)],
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert process.returncode == 0, process.stdout + process.stderr


@pytest.mark.native
def test_native_composer_is_multiline_and_preserves_technical_tokens(client):
    client.seed()
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QPlainTextEdit

    composer = client.window.findChild(QPlainTextEdit, "ai-composer")
    assert composer is not None and composer.accessibleName()
    composer.setFocus()
    QTest.keyClicks(composer, "CO2 kPa kg/s H2O")
    QTest.keyClick(composer, Qt.Key.Key_Return)
    QTest.keyClicks(composer, "Second line")
    assert composer.toPlainText() == "CO2 kPa kg/s H2O\nSecond line"
    assert not client.transport.calls
    dictionary = client.ok(
        "ai.dictionary.add", "AiDictionaryParameters", ("thermofluid", "CO2"), "en"
    )
    assert {"thermofluid", "CO2"} <= set(dictionary["words"])


@pytest.mark.native
def test_keyboard_send_is_responsive_during_provider_wait(client):
    client.seed()
    client.configure()
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QAbstractButton, QLabel, QPlainTextEdit

    client.window.canvas.select_ids(("heater-1",))
    preview = client.window.findChild(QAbstractButton, "ai-context-preview")
    composer = client.window.findChild(QPlainTextEdit, "ai-composer")
    send = client.window.findChild(QAbstractButton, "ai-send")
    stop = client.window.findChild(QAbstractButton, "ai-stop")
    status = client.window.findChild(QLabel, "ai-status")
    assert all(widget is not None for widget in (preview, composer, send, stop, status))
    preview.setFocus()
    QTest.keyClick(preview, Qt.Key.Key_Space)
    composer.setPlainText("Explain the selected heater.")
    client.transport.release.clear()
    client.transport.queue(response(kind="explanation"))
    ticks = []
    timer = QTimer()
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start(10)
    send.setFocus()
    QTest.keyClick(send, Qt.Key.Key_Space)
    QTest.qWait(150)
    timer.stop()
    assert client.transport.entered.is_set() and ticks, "Provider wait blocked the Qt event loop"
    assert stop.isEnabled() and "SENDING" in status.text()
    stop.setFocus()
    QTest.keyClick(stop, Qt.Key.Key_Space)
    client.transport.release.set()
    QTest.qWait(150)
    assert "CANCELLED" in status.text()


@pytest.mark.native
def test_preview_flushes_pending_inspector_edits(client):
    client.seed()
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QAbstractButton, QLineEdit

    client.window.canvas.select_ids(("heater-1",))
    client.pump()
    fields = client.window.input_panel.findChildren(QLineEdit)
    field = next((f for f in fields if f.text() in {"500000", "500000.0", "500,000"}), None)
    assert field is not None, "The actual selected heater duty field must be reachable"
    field.setText("550000")
    field.setModified(True)
    preview = client.window.findChild(QAbstractButton, "ai-context-preview")
    assert preview is not None
    preview.setFocus()
    QTest.keyClick(preview, Qt.Key.Key_Space)
    client.pump()
    # Verify the ordinary public history after the UI action, not a fake panel report.
    head = client.head()
    heater = next(n for n in head["document"]["draft"]["equipment"] if n["object_id"] == "heater-1")
    assert heater["parameters"][0]["quantity"]["value"] == 550_000
    assert not client.transport.calls


@pytest.mark.parametrize("profile", ["REVIEW", "EXPLORATION", "NARRATIVE"])
@pytest.mark.worker
def test_persisted_profile_survives_actual_worker_artifacts_and_reopen(client, profile):
    client.seed(profile=profile)
    client.configure()
    run = client.baseline_run(profile=profile)
    assert run["profile"] == profile and run["execution_scope"] == "ordinary"
    context = client.preview(selected=("heater-1", run["run_id"]))
    session = client.send(client.session(profile, context=context), response(kind="explanation"))
    exported = client.export(session)
    cases = [
        json.loads(a["content_utf8"])
        for a in exported["artifacts"]
        if a["media_type"] == "application/json"
    ]
    case = next(a for a in cases if a.get("$type") == "CaseDefinition")
    assert case["ai_profile"].upper() == profile
    client.close()
    assert client.head()["document"]["draft"]["profile"] == profile
    assert client.inspect(session)["profile"] == profile
    assert client.ok("run.inspect", "InspectRunParameters", run["run_id"])["profile"] == profile
    if profile == "NARRATIVE":
        denied = client.call(
            "ai.session.create",
            "AiSessionParameters",
            context["context_id"],
            "REVIEW",
            "Try to relabel narrative",
        )
        assert denied.disposition == "REJECTED"
        assert "NARRATIVE_PROMOTION_FORBIDDEN" in codes(denied)


@pytest.mark.native
@pytest.mark.parametrize("decision", ["apply", "reject"])
def test_keyboard_proposal_decision_reaches_actual_history(client, decision):
    client.seed()
    client.configure()
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QAbstractButton, QLabel, QPlainTextEdit

    client.window.canvas.select_ids(("heater-1",))
    preview = client.window.findChild(QAbstractButton, "ai-context-preview")
    composer = client.window.findChild(QPlainTextEdit, "ai-composer")
    send = client.window.findChild(QAbstractButton, "ai-send")
    status = client.window.findChild(QLabel, "ai-status")
    assert all(w is not None for w in (preview, composer, send, status))
    preview.setFocus()
    QTest.keyClick(preview, Qt.Key.Key_Space)
    composer.setPlainText("Propose a heater change.")
    client.transport.queue(response())
    send.setFocus()
    QTest.keyClick(send, Qt.Key.Key_Space)
    for _ in range(100):
        QTest.qWait(20)
        if "REVIEW_READY" in status.text():
            break
    assert "REVIEW_READY" in status.text()
    for action in ["approve", "apply"] if decision == "apply" else ["reject"]:
        button = client.window.findChild(QAbstractButton, "ai-" + action)
        assert button is not None and button.isEnabled() and button.accessibleName()
        button.setFocus()
        QTest.keyClick(button, Qt.Key.Key_Space)
        client.pump()
    head = client.head()
    heater = next(n for n in head["document"]["draft"]["equipment"] if n["object_id"] == "heater-1")
    assert heater["parameters"][0]["quantity"]["value"] == (
        600_000 if decision == "apply" else 500_000
    )
