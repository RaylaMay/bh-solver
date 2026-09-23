"""DW3 application and immutable-storage behavior; no scientific approval implied."""

import json
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest

from bh_sim.adapters.desktop_preview import create_preview_gateway
from bh_sim.adapters.pfd import ExistingQuantityAdapter, NativePfdRepository, reference_catalogue
from bh_sim.application.commands import CommandRegistry
from bh_sim.application.pfd import pfd_engineering_content_hash
from bh_sim.boundary import contracts as c
from bh_sim.boundary.json_codec import boundary_from_json, boundary_json


@pytest.fixture
def gateway(tmp_path: Path) -> CommandRegistry:
    return create_preview_gateway(tmp_path)


def call(gateway: CommandRegistry, name: str, params: c.CommandParameters) -> c.CommandOutcome:
    return gateway.dispatch(c.CommandRequest(name, uuid4().hex, "test-owner", params))


def new_document(gateway: CommandRegistry) -> c.PfdDocumentDto:
    draft = call(gateway, "draft.create", c.CreateDraftParameters("Native test")).data
    assert isinstance(draft, c.DraftDto)
    result = call(gateway, "pfd.import", c.DraftParameters(draft)).data
    assert isinstance(result, c.PfdDocumentDto)
    return result


def edited(
    gateway: CommandRegistry, document: c.PfdDocumentDto, edit: c.PfdEdit
) -> c.PfdDocumentDto:
    result = call(gateway, "pfd.edit", c.PfdEditParameters(document, edit))
    assert result.disposition == "COMPLETED", result.diagnostics
    assert isinstance(result.data, c.PfdDocumentDto)
    return result.data


def connected(gateway: CommandRegistry) -> c.PfdDocumentDto:
    document = new_document(gateway)
    for model, x in (("source", 0.0), ("sink", 250.0), ("sink", 500.0)):
        document = edited(gateway, document, c.AddEquipmentEdit(model, c.CanvasPointDto(x, 0.0)))
    nodes = document.draft.equipment
    return edited(
        gateway,
        document,
        c.ConnectPortsEdit(nodes[0].object_id, "out-0", nodes[1].object_id, "in-0"),
    )


def test_native_save_round_trip_and_idempotency(gateway: CommandRegistry, tmp_path: Path) -> None:
    document = connected(gateway)
    source = document.draft.equipment[0].object_id
    stream = document.draft.connections[0].object_id
    document = edited(gateway, document, c.ConfigureInputEdit(source, "pressure", "1.000", "bar"))
    document = edited(
        gateway,
        document,
        c.RouteStreamEdit(stream, (c.CanvasPointDto(150.0, 30.0), c.CanvasPointDto(150.0, 70.0))),
    )
    document = edited(gateway, document, c.ViewportEdit(c.CanvasPointDto(90.0, 10.0), 0.75))
    saved = call(gateway, "pfd.save", c.PfdDocumentParameters(document)).data
    assert isinstance(saved, c.PfdDocumentDto)
    paths = list((tmp_path / "native-drafts").glob("*.json"))
    assert len(paths) == 1
    original_bytes = paths[0].read_bytes()
    assert call(gateway, "pfd.save", c.PfdDocumentParameters(document)).data == saved
    assert call(gateway, "pfd.open", c.OpenDraftParameters(document.draft.draft_id)).data == saved
    changed = edited(gateway, saved, c.MoveObjectsEdit(((source, c.CanvasPointDto(80.0, 90.0)),)))
    result = call(gateway, "pfd.save", c.PfdDocumentParameters(changed)).data
    assert (
        isinstance(result, c.PfdDocumentDto) and result.draft.revision == saved.draft.revision + 1
    )
    assert paths[0].read_bytes() == original_bytes
    assert list((tmp_path / "drafts").glob("*.json")) == []


def test_input_notation_units_and_missing_are_distinct(gateway: CommandRegistry) -> None:
    doc = connected(gateway)
    identifier = doc.draft.equipment[0].object_id
    changed = edited(gateway, doc, c.ConfigureInputEdit(identifier, "pressure", "1.000", "bar"))
    quantity = changed.draft.equipment[0].parameters[0].quantity
    assert ExistingQuantityAdapter().convert(quantity, "Pa").value == 100000
    assert next(o for o in changed.objects if o.object_id == identifier).notation[0].text == "1.000"
    assert ExistingQuantityAdapter().convert(c.QuantityDto(20.0, "degC"), "K").value == 293.15
    display = edited(gateway, changed, c.DisplayUnitEdit(identifier, "pressure", "kPa"))
    assert display.draft.equipment == changed.draft.equipment
    cleared = edited(gateway, changed, c.ConfigureInputEdit(identifier, "pressure", "", "bar"))
    assert cleared.draft.equipment[0].parameters == ()
    assert boundary_from_json(boundary_json(changed)) == changed


@pytest.mark.parametrize("text,unit", [("nan", "Pa"), ("inf", "Pa"), ("1", "W"), ("1", "invented")])
def test_invalid_input_is_atomic(gateway: CommandRegistry, text: str, unit: str) -> None:
    doc = connected(gateway)
    before = boundary_json(doc)
    result = call(
        gateway,
        "pfd.edit",
        c.PfdEditParameters(
            doc, c.ConfigureInputEdit(doc.draft.equipment[0].object_id, "pressure", text, unit)
        ),
    )
    assert result.disposition == "REJECTED" and boundary_json(doc) == before


def test_catalogue_mapping_has_no_invented_defaults(gateway: CommandRegistry) -> None:
    doc = new_document(gateway)
    for model in reference_catalogue().models:
        doc = edited(gateway, doc, c.AddEquipmentEdit(model.model_id, c.CanvasPointDto(0.0, 0.0)))
        node = doc.draft.equipment[-1]
        assert node.parameters == ()
        for p in model.parameters:
            doc = edited(
                gateway, doc, c.ConfigureInputEdit(node.object_id, p.name, "1.0", p.canonical_unit)
            )


def test_port_rejections_and_connected_delete(gateway: CommandRegistry) -> None:
    doc = connected(gateway)
    nodes = doc.draft.equipment
    for edit, code in (
        (
            c.ConnectPortsEdit(nodes[0].object_id, "out-0", nodes[2].object_id, "in-0"),
            "PORT_OCCUPIED",
        ),
        (
            c.ConnectPortsEdit(nodes[1].object_id, "in-0", nodes[2].object_id, "in-0"),
            "PORT_DIRECTION",
        ),
        (c.RemoveObjectsEdit((nodes[0].object_id,)), "CONNECTED_DELETE"),
    ):
        result = call(gateway, "pfd.edit", c.PfdEditParameters(doc, edit))
        assert result.diagnostics[0].code == code
    removed = edited(gateway, doc, c.RemoveObjectsEdit((nodes[0].object_id,), True))
    assert not removed.draft.connections and len(removed.draft.equipment) == 2


def test_split_family_rename_unique_tags_and_paste(gateway: CommandRegistry) -> None:
    doc = connected(gateway)
    parent = doc.draft.connections[0].object_id
    doc = edited(
        gateway,
        doc,
        c.SplitStreamEdit(
            parent, c.CanvasPointDto(120.0, 30.0), doc.draft.equipment[2].object_id, "in-0"
        ),
    )
    assert len(doc.draft.equipment) == 4 and len(doc.draft.connections) == 3
    assert (
        doc.draft.equipment[-1].model_id == "splitter" and doc.draft.equipment[-1].parameters == ()
    )
    branches = [o for o in doc.objects if o.parent_stream_id == parent]
    assert {o.tag for o in branches} == {"S-001(a)", "S-001(b)"}
    customized = edited(gateway, doc, c.RenameObjectEdit(branches[0].object_id, "Custom"))
    renamed = edited(gateway, customized, c.RenameObjectEdit(parent, "Feed"))
    assert {o.tag for o in renamed.objects if o.object_id in {b.object_id for b in branches}} == {
        "Custom",
        "Feed(b)",
    }
    clash = call(
        gateway, "pfd.edit", c.PfdEditParameters(renamed, c.RenameObjectEdit(parent, "Custom"))
    )
    assert clash.diagnostics[0].code == "TAG_CONFLICT"
    swapped = edited(gateway, renamed, c.RenameObjectEdit(parent, "Custom", swap=True))
    assert (
        len(
            {
                o.tag
                for o in swapped.objects
                if o.object_id in {s.object_id for s in swapped.draft.connections}
            }
        )
        == 3
    )
    selection = tuple(n.object_id for n in renamed.draft.equipment)
    pasted = edited(gateway, renamed, c.PasteEquipmentEdit(renamed, selection))
    assert len(pasted.draft.equipment) == 8 and len(pasted.draft.connections) == 3
    pasted_connected = edited(
        gateway, renamed, c.PasteEquipmentEdit(renamed, selection, connections=True)
    )
    assert len(pasted_connected.draft.connections) == 6


def test_family_collision_rolls_back_entire_rename(gateway: CommandRegistry) -> None:
    doc = connected(gateway)
    parent = doc.draft.connections[0].object_id
    doc = edited(
        gateway,
        doc,
        c.SplitStreamEdit(
            parent, c.CanvasPointDto(120.0, 30.0), doc.draft.equipment[2].object_id, "in-0"
        ),
    )
    branches = [o for o in doc.objects if o.parent_stream_id == parent]
    doc = edited(gateway, doc, c.RenameObjectEdit(branches[1].object_id, "Feed(a)"))
    before = boundary_json(doc)
    result = call(gateway, "pfd.edit", c.PfdEditParameters(doc, c.RenameObjectEdit(parent, "Feed")))
    assert result.disposition == "REJECTED" and boundary_json(doc) == before


def test_failed_publication_preserves_saved_bytes(
    gateway: CommandRegistry, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    doc = connected(gateway)
    saved = call(gateway, "pfd.save", c.PfdDocumentParameters(doc)).data
    assert isinstance(saved, c.PfdDocumentDto)
    files = {p.name: p.read_bytes() for p in (tmp_path / "native-drafts").glob("*.json")}
    doc = edited(gateway, saved, c.SettingsEdit(replace(saved.settings, crossing="bridge")))

    def fail(*args):
        raise OSError("private path")

    monkeypatch.setattr("bh_sim.adapters.pfd.os.link", fail)
    outcome = call(gateway, "pfd.save", c.PfdDocumentParameters(doc))
    assert outcome.disposition == "REJECTED" and "private path" not in str(outcome)
    assert files == {p.name: p.read_bytes() for p in (tmp_path / "native-drafts").glob("*.json")}
    assert list((tmp_path / "native-drafts").glob(".pending-*")) == []


def test_native_filename_identity_collision_is_avoided(tmp_path: Path) -> None:
    repository = NativePfdRepository(tmp_path)
    for name in ("A/B", "A-B"):
        draft = c.DraftDto(name, 1, None, "", (), (), c.PresentationDto(()))
        repository.save(c.PfdDocumentDto(draft, ()))
    assert repository.latest("A/B").draft.draft_id == "A/B"
    assert repository.latest("A-B").draft.draft_id == "A-B"


def test_settings_and_routes_cannot_change_engineering(gateway: CommandRegistry) -> None:
    doc = connected(gateway)
    changed = edited(
        gateway,
        doc,
        c.SettingsEdit(
            replace(doc.settings, display_precision=3, units=(c.UnitPreferenceDto("Pa", "bar"),))
        ),
    )
    changed = edited(
        gateway,
        changed,
        c.MoveObjectsEdit(((doc.draft.equipment[0].object_id, c.CanvasPointDto(50.0, 80.0)),)),
    )
    assert changed.draft.equipment == doc.draft.equipment
    assert changed.draft.connections == doc.draft.connections
    assert changed.draft.presentation != doc.draft.presentation
    assert (
        "run.start" not in gateway.command_names and "draft.validate" not in gateway.command_names
    )


def test_legacy_import_does_not_rewrite_browser_file(
    gateway: CommandRegistry, tmp_path: Path
) -> None:
    doc = connected(gateway)
    legacy = call(gateway, "draft.save", c.DraftParameters(doc.draft)).data
    assert isinstance(legacy, c.DraftDto)
    before = {p.name: p.read_bytes() for p in (tmp_path / "drafts").glob("*.json")}
    opened = call(gateway, "pfd.open", c.OpenDraftParameters(legacy.draft_id)).data
    assert isinstance(opened, c.PfdDocumentDto)
    assert call(gateway, "pfd.save", c.PfdDocumentParameters(opened)).disposition == "COMPLETED"
    assert before == {p.name: p.read_bytes() for p in (tmp_path / "drafts").glob("*.json")}


def test_legacy_default_port_is_counted_as_occupied(gateway: CommandRegistry) -> None:
    doc = connected(gateway)
    doc = replace(
        doc,
        draft=replace(
            doc.draft, connections=(replace(doc.draft.connections[0], source_port=None),)
        ),
    )
    result = call(
        gateway,
        "pfd.edit",
        c.PfdEditParameters(
            doc,
            c.ConnectPortsEdit(
                doc.draft.equipment[0].object_id, "out-0", doc.draft.equipment[2].object_id, "in-0"
            ),
        ),
    )
    assert result.diagnostics[0].code == "PORT_OCCUPIED"


def test_cache_never_bypasses_payload_validation(gateway: CommandRegistry) -> None:
    doc = connected(gateway)
    call(gateway, "pfd.restore", c.PfdDocumentParameters(doc))
    # Deliberately forge an otherwise frozen DTO after static schema cache warm-up.
    malformed = c.QuantityDto(1.0, "Pa")
    object.__setattr__(malformed, "value", float("nan"))
    with pytest.raises((ValueError, TypeError)):
        c.QuantityDisplayParameters(malformed, "bar")
    with pytest.raises((ValueError, TypeError)):
        boundary_json(malformed)


def test_native_presentation_preserves_established_engineering_hash(
    gateway: CommandRegistry,
    tmp_path: Path,
) -> None:
    from bh_sim.adapters.browser_format import from_browser
    from bh_sim.api.schemas import PfdDraftDto
    from bh_sim.composition import create_services
    from tests.test_api import draft_payload

    assert gateway.pfd is not None
    document = gateway.pfd.import_draft(from_browser(PfdDraftDto.model_validate(draft_payload())))
    engineering = create_services(tmp_path / "engineering-check").engineering
    before = engineering.prepare(document.draft)
    changed = edited(
        gateway,
        document,
        c.MoveObjectsEdit(((document.draft.equipment[0].object_id, c.CanvasPointDto(30.0, 40.0)),)),
    )
    changed = edited(
        gateway, changed, c.SettingsEdit(replace(changed.settings, display_precision=3))
    )
    after = engineering.prepare(changed.draft)
    assert before.engineering_hash == after.engineering_hash


def test_visual_groups_overlap_persist_and_recover_missing_members(
    gateway: CommandRegistry,
) -> None:
    document = connected(gateway)
    stream = document.draft.connections[0].object_id
    first = c.VisualStreamGroup("visual:feed", "Feed train", (stream,), "#FFD166", 0)
    second = c.VisualStreamGroup("visual:hot", "Hot lines", (stream,), "#EF476F", 1)
    grouped = edited(gateway, document, c.UpsertVisualStreamGroupEdit(first))
    grouped = edited(gateway, grouped, c.UpsertVisualStreamGroupEdit(second))
    grouped = edited(
        gateway,
        grouped,
        c.SetPfdLayerPreferencesEdit(
            replace(grouped.layer_preferences, active_visual_group_id=second.group_id)
        ),
    )
    assert grouped.visual_groups == (first, second)
    assert grouped.draft == document.draft
    removed = edited(gateway, grouped, c.RemoveObjectsEdit((stream,), True))
    assert all(group.member_stream_ids == () for group in removed.visual_groups)
    assert removed.layer_preferences.active_visual_group_id == second.group_id
    assert boundary_from_json(boundary_json(removed)) == removed


def test_group_types_have_separate_engineering_hash_behavior(gateway: CommandRegistry) -> None:
    document = connected(gateway)
    stream = document.draft.connections[0].object_id
    before = pfd_engineering_content_hash(document)
    visual = edited(
        gateway,
        document,
        c.UpsertVisualStreamGroupEdit(c.VisualStreamGroup("visual:one", "One", (stream,))),
    )
    assert pfd_engineering_content_hash(visual) == before
    subsystem = edited(
        gateway,
        visual,
        c.UpsertEngineeringSubsystemEdit(
            c.EngineeringSubsystem(
                "subsystem:one",
                "Feed subsystem",
                (stream,),
                "Versioned process grouping",
                revision_provenance="draft-revision:1",
            )
        ),
    )
    assert pfd_engineering_content_hash(subsystem) != before
    presentation = edited(
        gateway,
        subsystem,
        c.SetPfdLayerPreferencesEdit(
            replace(subsystem.layer_preferences, line_width=4.0, animation_fps=15)
        ),
    )
    assert pfd_engineering_content_hash(presentation) == pfd_engineering_content_hash(subsystem)


def test_older_native_pfd_envelope_uses_new_presentation_defaults(
    gateway: CommandRegistry,
) -> None:
    document = connected(gateway)
    encoded = json.loads(boundary_json(document))
    for field in ("visual_groups", "engineering_subsystems", "layer_preferences"):
        del encoded[field]
    restored = boundary_from_json(json.dumps(encoded))
    assert isinstance(restored, c.PfdDocumentDto)
    assert restored.visual_groups == ()
    assert restored.engineering_subsystems == ()
    assert restored.layer_preferences == c.PfdLayerPreferences()
