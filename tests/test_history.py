"""Durable history behaviour and faults, independent of widgets and solver execution."""

from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest

from bh_sim.adapters.desktop_preview import create_preview_gateway
from bh_sim.adapters.history import JsonHistoryRepository
from bh_sim.application.commands import CommandRegistry
from bh_sim.boundary import contracts as c
from bh_sim.boundary.json_codec import boundary_from_json, boundary_json


def dispatch(
    gateway: CommandRegistry,
    name: str,
    parameters: c.CommandParameters,
    *,
    actor: str = "reviewer",
    request_id: str = "",
) -> c.CommandOutcome:
    return gateway.dispatch(c.CommandRequest(name, request_id or uuid4().hex, actor, parameters))


def completed(
    gateway: CommandRegistry, name: str, parameters: c.CommandParameters
) -> c.CommandData:
    outcome = dispatch(gateway, name, parameters)
    assert outcome.disposition == "COMPLETED", outcome
    return outcome.data


def begin(root: Path, name: str = "History fixture") -> tuple[CommandRegistry, c.HistoryState]:
    gateway = create_preview_gateway(root)
    draft = completed(gateway, "draft.create", c.CreateDraftParameters(name))
    assert isinstance(draft, c.DraftDto)
    doc = completed(gateway, "pfd.import", c.DraftParameters(draft))
    assert isinstance(doc, c.PfdDocumentDto)
    state = completed(gateway, "history.start", c.PfdDocumentParameters(doc))
    assert isinstance(state, c.HistoryState)
    return gateway, state


def target(state: c.HistoryState, *, name: str = "", entry: str = "") -> c.HistoryTarget:
    return c.HistoryTarget(state.document.draft.draft_id, state.entries[-1].entry_id, entry, name)


def action(
    gateway: CommandRegistry,
    state: c.HistoryState,
    command: str,
    edit: c.PfdEdit | None = None,
    name: str = "",
    entry: str = "",
) -> c.HistoryState:
    params = target(state, name=name, entry=entry)
    data = completed(
        gateway, "history." + command, c.HistoryEditParameters(params, edit) if edit else params
    )
    assert isinstance(data, c.HistoryState)
    return data


def add(gateway: CommandRegistry, state: c.HistoryState) -> c.HistoryState:
    return action(gateway, state, "edit", c.AddEquipmentEdit("source", c.CanvasPointDto(0.0, 0.0)))


def test_save_restart_undo_redo_and_saved_marker(tmp_path: Path) -> None:
    gateway, state = begin(tmp_path)
    state = add(gateway, state)
    before = state.document
    state = action(gateway, state, "save")
    assert not state.dirty
    state = action(gateway, state, "undo")
    assert not state.document.objects and state.dirty
    gateway = create_preview_gateway(tmp_path)
    state = action(gateway, state, "open")
    state = action(gateway, state, "redo")
    assert state.document == before and not state.dirty
    assert [e.kind for e in state.entries] == ["start", "edit", "save", "undo", "redo"]
    assert state.entries[-1].reverses_entry_id == state.entries[1].entry_id


def test_alternatives_and_snapshot_view_never_change_current_head(tmp_path: Path) -> None:
    gateway, state = begin(tmp_path)
    state = add(gateway, state)
    state = action(gateway, state, "snapshot", name="Review baseline")
    baseline = state
    state = action(gateway, state, "undo")
    state = add(gateway, state)
    assert state.entries[-1].branch != baseline.entries[-1].branch
    assert any(e.snapshot and e.snapshot.name == "Review baseline" for e in state.entries)
    view = action(gateway, state, "view", entry=baseline.entries[-1].entry_id)
    assert view.document == baseline.document
    assert action(gateway, state, "open").document == state.document
    branch = action(
        gateway, state, "branch", name="Alternate design", entry=view.entries[-1].entry_id
    )
    assert branch.document == baseline.document
    assert branch.entries[-1].branch.name == "Alternate design"
    assert branch.entries[-1].branch.origin_entry_id == view.entries[-1].entry_id


def test_classification_and_structural_comparison(tmp_path: Path) -> None:
    gateway, state = begin(tmp_path)
    state = add(gateway, state)
    identifier = state.document.objects[0].object_id
    before = state
    moved = action(
        gateway, state, "edit", c.MoveObjectsEdit(((identifier, c.CanvasPointDto(80.0, 40.0)),))
    )
    assert moved.entries[-1].classification == "presentation"
    assert moved.entries[-1].before_engineering_hash == moved.entries[-1].after_engineering_hash
    configured = action(
        gateway, moved, "edit", c.ConfigureInputEdit(identifier, "pressure", "1.000", "bar")
    )
    assert configured.entries[-1].classification == "engineering"
    comparison = completed(
        gateway, "history.compare", c.CompareHistoryParameters(target(before), target(configured))
    )
    # Target entry IDs select exact immutable versions, not the latest shared head.
    comparison = completed(
        gateway,
        "history.compare",
        c.CompareHistoryParameters(
            target(before, entry=before.entries[-1].entry_id),
            target(configured, entry=configured.entries[-1].entry_id),
        ),
    )
    assert isinstance(comparison, c.HistoryComparison)
    assert {d.category for d in comparison.differences} == {"engineering", "presentation"}
    subsystem = c.EngineeringSubsystem("subsystem:1", "Feed system", (identifier,), "Test")
    changed = action(gateway, configured, "edit", c.UpsertEngineeringSubsystemEdit(subsystem))
    assert changed.entries[-1].classification == "engineering"


def test_two_writers_stale_head_and_other_actor_undo_rejected(tmp_path: Path) -> None:
    gateway, state = begin(tmp_path)
    other = create_preview_gateway(tmp_path)
    updated = add(gateway, state)
    outcome = dispatch(
        other,
        "history.edit",
        c.HistoryEditParameters(
            target(state), c.AddEquipmentEdit("sink", c.CanvasPointDto(0.0, 0.0))
        ),
    )
    assert outcome.diagnostics[0].code == "HISTORY_CONFLICT"
    outcome = dispatch(other, "history.undo", target(updated), actor="second-reviewer")
    assert outcome.diagnostics[0].code == "UNDO_AUTHORITY"
    assert action(gateway, updated, "open").document == updated.document


def test_durable_request_dedup_and_reuse_conflict(tmp_path: Path) -> None:
    gateway, state = begin(tmp_path)
    params = c.HistoryEditParameters(
        target(state), c.AddEquipmentEdit("source", c.CanvasPointDto(0.0, 0.0))
    )
    first = dispatch(gateway, "history.edit", params, request_id="request:fixed")
    gateway = create_preview_gateway(tmp_path)
    repeated = dispatch(gateway, "history.edit", params, request_id="request:fixed")
    assert repeated.data == first.data
    conflict = dispatch(
        gateway,
        "history.edit",
        replace(params, edit=c.AddEquipmentEdit("sink", c.CanvasPointDto(0.0, 0.0))),
        request_id="request:fixed",
    )
    assert conflict.diagnostics[0].code == "REQUEST_ID_CONFLICT"


def test_failed_commit_and_orphan_checkpoint_preserve_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gateway, state = begin(tmp_path)
    assert gateway.history is not None

    def fail(*_args) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(gateway.history.repository, "append", fail)
    result = dispatch(
        gateway,
        "history.edit",
        c.HistoryEditParameters(
            target(state), c.AddEquipmentEdit("source", c.CanvasPointDto(0.0, 0.0))
        ),
    )
    assert result.disposition == "REJECTED"
    assert action(create_preview_gateway(tmp_path), state, "open") == state
    assert len(list((tmp_path / "history" / "checkpoints").glob("*.json"))) == 2


def test_corrupt_and_missing_record_fail_without_silent_rewind(tmp_path: Path) -> None:
    gateway, state = begin(tmp_path)
    state = add(gateway, state)
    root = tmp_path / "history"
    path = next(root.glob("*/000000000002.json"))
    before = path.read_bytes()
    path.write_text("{}")
    assert (
        dispatch(create_preview_gateway(tmp_path), "history.open", target(state)).disposition
        == "REJECTED"
    )
    path.write_bytes(before)
    checkpoint = root / "checkpoints" / (state.entries[-1].after_hash + ".json")
    checkpoint.write_text("{}")
    assert (
        dispatch(create_preview_gateway(tmp_path), "history.open", target(state)).disposition
        == "REJECTED"
    )


def test_legacy_import_preserves_bytes_and_has_no_invented_edits(tmp_path: Path) -> None:
    gateway = create_preview_gateway(tmp_path)
    draft = completed(gateway, "draft.create", c.CreateDraftParameters("Legacy"))
    assert isinstance(draft, c.DraftDto)
    doc = completed(gateway, "pfd.import", c.DraftParameters(draft))
    assert isinstance(doc, c.PfdDocumentDto)
    saved = completed(gateway, "pfd.save", c.PfdDocumentParameters(doc))
    paths = list((tmp_path / "native-drafts").glob("*.json"))
    original = paths[0].read_bytes()
    state = completed(gateway, "history.open", c.HistoryTarget("Legacy"))
    assert isinstance(state, c.HistoryState)
    assert len(state.entries) == 1 and not state.entries[0].undo_ids
    assert state.document == saved and paths[0].read_bytes() == original
    assert not state.dirty


def test_codec_rejects_unknown_history_versions_and_roundtrips(tmp_path: Path) -> None:
    _, state = begin(tmp_path)
    raw = boundary_json(state)
    assert boundary_from_json(raw) == state
    with pytest.raises(ValueError):
        boundary_from_json(raw.replace("bh-history-state-v1", "bh-history-state-v9"))
    repo = JsonHistoryRepository(tmp_path / "history")
    with pytest.raises(ValueError):
        repo.document("../untrusted")


def test_empty_undo_and_invalid_inputs_do_not_create_events(tmp_path: Path) -> None:
    gateway, state = begin(tmp_path)
    assert dispatch(gateway, "history.undo", target(state)).diagnostics[0].code == "HISTORY_EMPTY"
    assert (
        dispatch(gateway, "history.snapshot", target(state, name=" ")).diagnostics[0].code
        == "SNAPSHOT_NAME"
    )
    assert action(gateway, state, "open") == state


def test_cache_still_checks_disk_bytes_and_save_ack_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gateway, state = begin(tmp_path)
    state = add(gateway, state)
    assert gateway.history is not None
    original_append = gateway.history.repository.append

    def fail(*_args) -> None:
        raise OSError("interrupted journal publication")

    monkeypatch.setattr(gateway.history.repository, "append", fail)
    rejected = dispatch(gateway, "history.save", target(state))
    assert rejected.disposition == "REJECTED"
    assert len(list((tmp_path / "native-drafts").glob("*.json"))) == 1
    monkeypatch.setattr(gateway.history.repository, "append", original_append)
    reopened = action(gateway, state, "open")
    assert reopened.dirty
    saved = action(gateway, reopened, "save")
    assert not saved.dirty
    assert len(list((tmp_path / "native-drafts").glob("*.json"))) == 1
    checkpoint = tmp_path / "history" / "checkpoints" / (saved.entries[-1].after_hash + ".json")
    checkpoint.write_text("{}")
    assert dispatch(gateway, "history.open", target(saved)).disposition == "REJECTED"


def test_recovery_never_replays_engineering_or_effectful_commands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bh_sim.adapters.desktop_preview import UnavailablePreviewPorts
    from bh_sim.application.pfd import PfdService

    gateway, state = begin(tmp_path)
    state = add(gateway, state)
    state = action(gateway, state, "save")

    def unexpected(*_args, **_kwargs):
        raise AssertionError("Recovery attempted an effectful or numerical operation")

    for method in ("prepare", "validate", "run", "evaluate", "save_run"):
        monkeypatch.setattr(UnavailablePreviewPorts, method, unexpected)
    monkeypatch.setattr(PfdService, "edit", unexpected)
    reopened = action(create_preview_gateway(tmp_path), state, "open")
    restored = action(create_preview_gateway(tmp_path), reopened, "undo")
    assert not restored.document.objects


def test_history_golden_bytes_and_source_identity() -> None:
    from bh_sim.application.history import document_hash

    raw = (
        (Path(__file__).parent / "fixtures" / "dw3_2" / "history-state-v1.json").read_text().strip()
    )
    state = boundary_from_json(raw)
    assert isinstance(state, c.HistoryState)
    assert boundary_json(state) == raw
    assert document_hash(state.document) == state.entries[0].after_hash
    assert state.entries[0].actor_id == "editor:golden"


@pytest.mark.parametrize("payload", ["[]", '{"record":4,"sha256":"bad"}', '{"unexpected":true}'])
def test_malformed_discovery_envelope_is_a_diagnostic(tmp_path: Path, payload: str) -> None:
    gateway, _ = begin(tmp_path)
    path = next((tmp_path / "history").glob("*/000000000001.json"))
    path.write_text(payload)
    outcome = dispatch(gateway, "history.list", c.ListDraftsParameters())
    assert outcome.disposition == "REJECTED"


def test_abrupt_process_exit_recovers_acknowledged_edit(tmp_path: Path) -> None:
    import subprocess
    import sys

    script = """
import os, sys
from pathlib import Path
from bh_sim.adapters.desktop_preview import create_preview_gateway
from bh_sim.boundary import contracts as c
g = create_preview_gateway(Path(sys.argv[1]))
def run(name, params, identifier):
    outcome = g.dispatch(c.CommandRequest(name, identifier, "crash-test", params))
    assert outcome.disposition == "COMPLETED"
    return outcome.data
d = run("draft.create", c.CreateDraftParameters("Crash fixture"), "create")
p = run("pfd.import", c.DraftParameters(d), "import")
h = run("history.start", c.PfdDocumentParameters(p), "start")
target = c.HistoryTarget("Crash fixture", h.entries[-1].entry_id)
run("history.edit", c.HistoryEditParameters(target,
    c.AddEquipmentEdit("source", c.CanvasPointDto(0.0, 0.0))), "add")
os._exit(7)
"""
    process = subprocess.run([sys.executable, "-c", script, str(tmp_path)], check=False)
    assert process.returncode == 7
    state = completed(
        create_preview_gateway(tmp_path), "history.open", c.HistoryTarget("Crash fixture")
    )
    assert isinstance(state, c.HistoryState)
    assert len(state.document.objects) == 1 and state.dirty
    assert state.entries[-1].actor_id == "crash-test"
