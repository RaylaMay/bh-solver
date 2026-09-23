"""Future control graph contracts; numerical execution remains unavailable."""

from pathlib import Path

import pytest

from bh_sim.boundary import contracts as c
from bh_sim.boundary.json_codec import boundary_from_json, boundary_json


def diagram() -> c.ControlDiagram:
    source = c.ControlBlock(
        "block:sensor",
        "user",
        (c.SignalPort("out", "Measured pressure", "output", "real", "Pa"),),
        (("stableObjectId", "stream:feed"),),
        0.1,
        1,
    )
    controller = c.ControlBlock(
        "block:pid",
        "pid",
        (
            c.SignalPort("pv", "Process value", "input", "real", "Pa"),
            c.SignalPort("out", "Controller output", "output", "real", "%"),
        ),
        (("Kp", "proposal:unset"),),
        0.1,
        2,
    )
    return c.ControlDiagram(
        "control:example",
        1,
        (source, controller),
        (c.ControlSignalConnection("signal:pv", "block:sensor", "out", "block:pid", "pv"),),
    )


def test_control_graph_round_trip_and_deterministic_schedule_metadata() -> None:
    value = diagram()
    assert value.event_ordering == "time-then-execution-order-then-id"
    assert boundary_from_json(boundary_json(value)) == value
    fixture = Path(__file__).parent / "fixtures" / "dw3_1" / "control-diagram.json"
    assert boundary_from_json(fixture.read_text()) == value
    assert boundary_json(value) == fixture.read_text().strip()


def test_control_graph_rejects_missing_direction_and_unit_mismatch() -> None:
    value = diagram()
    with pytest.raises(ValueError):
        c.ControlDiagram(
            value.diagram_id,
            value.revision,
            value.blocks,
            (c.ControlSignalConnection("bad", "block:pid", "pv", "block:sensor", "out"),),
        )
    mismatched = c.ControlBlock(
        "block:other",
        "limit",
        (c.SignalPort("in", "Input", "input", "real", "K"),),
    )
    with pytest.raises(ValueError):
        c.ControlDiagram(
            value.diagram_id,
            value.revision,
            (value.blocks[0], mismatched),
            (c.ControlSignalConnection("bad-unit", "block:sensor", "out", "block:other", "in"),),
        )


def test_workspace_manifest_links_independent_revisions() -> None:
    manifest = c.WorkspaceProjectManifest(
        "project:example",
        c.WorkspaceDocumentRevision("flowsheet:example", 4, "bh-pfd-document-v1"),
        c.WorkspaceDocumentRevision("dynamics:example", 2, "future-dynamics-v1"),
        c.WorkspaceDocumentRevision("controls:example", 7, "bh-control-diagram-v1"),
    )
    assert manifest.flowsheet.revision == 4
    assert manifest.dynamics is not None and manifest.dynamics.revision == 2
    assert manifest.controls is not None and manifest.controls.revision == 7
    assert boundary_from_json(boundary_json(manifest)) == manifest


def test_cosimulation_exchange_is_typed_and_unit_aware() -> None:
    exchange = c.CoSimulationExchange(
        "exchange:1",
        0.1,
        (c.SignalValue("signal:pressure", "real", 101325.0, "Pa"),),
        (c.ControlEvent("event:1", 0.1, "block:pid", "out", "limited", 2),),
        1,
    )
    assert boundary_from_json(boundary_json(exchange)) == exchange
    with pytest.raises(ValueError):
        c.SignalValue("signal:wrong", "boolean", 1, None)
    with pytest.raises(ValueError):
        c.SignalValue("signal:unitless", "real", 1.0, None)
