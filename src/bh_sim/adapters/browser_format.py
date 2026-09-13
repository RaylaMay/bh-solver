"""Lossless v1alpha browser-schema translation, outside the neutral contracts.

Pydantic validates the existing browser format. Registered engineering parameter
names and labels/layout become separate neutral values. Unknown browser extension
fields remain namespaced JSON presentation data and never enter engineering input.
"""

from __future__ import annotations

import json
from typing import Any

from bh_sim.api.schemas import PfdDraftDto
from bh_sim.boundary.contracts import (
    ConnectionDto,
    DraftDto,
    EquipmentDto,
    ObjectPresentationDto,
    ParameterDto,
    ParameterPresentationDto,
    PresentationDto,
    QuantityDto,
)


def from_browser(draft: PfdDraftDto) -> DraftDto:
    """Translate a validated legacy payload without interpreting unit arithmetic."""

    equipment = []
    connections = []
    presentation = []
    occurrences: dict[tuple[str, str], int] = {}
    for node in draft.nodes:
        occurrence = occurrences.get(("equipment", node.id), 0)
        occurrences[("equipment", node.id)] = occurrence + 1
        model = "heat_exchanger" if node.data.kind == "heat-exchanger" else node.data.kind
        equipment.append(
            EquipmentDto(
                node.id,
                model,
                tuple(
                    ParameterDto(
                        name,
                        QuantityDto(value.quantity.value, value.quantity.unit),
                    )
                    for name, value in node.data.parameters.items()
                ),
            )
        )
        raw = node.model_dump(mode="json", by_alias=True)
        extra = {key: value for key, value in raw.items() if key not in {"id", "position", "data"}}
        transient = {
            key: value
            for key, value in raw["data"].items()
            if key in {"status", "validity", "metrics"}
        }
        presentation.append(
            ObjectPresentationDto(
                node.id,
                node.data.label,
                node.position.x,
                node.position.y,
                tuple(
                    ParameterPresentationDto(name, value.label, value.description)
                    for name, value in node.data.parameters.items()
                ),
                extensions_json=json.dumps(
                    {"node": extra, "runtime": transient}, allow_nan=False, ensure_ascii=False
                ),
                occurrence=occurrence,
            )
        )
    for edge in draft.edges:
        occurrence = occurrences.get(("connection", edge.id), 0)
        occurrences[("connection", edge.id)] = occurrence + 1
        connections.append(
            ConnectionDto(edge.id, edge.source, edge.target, edge.source_handle, edge.target_handle)
        )
        raw = edge.model_dump(mode="json", by_alias=True)
        extra = {
            key: value
            for key, value in raw.items()
            if key not in {"id", "source", "target", "sourceHandle", "targetHandle"}
        }
        presentation.append(
            ObjectPresentationDto(
                edge.id,
                object_kind="connection",
                occurrence=occurrence,
                extensions_json=json.dumps({"edge": extra}, allow_nan=False, ensure_ascii=False),
            )
        )
    return DraftDto(
        draft.draft_id,
        draft.revision,
        draft.base_case_id,
        draft.updated_at.isoformat(),
        tuple(equipment),
        tuple(connections),
        PresentationDto(tuple(presentation)),
    )


def to_browser(draft: DraftDto) -> PfdDraftDto:
    """Reconstruct the retained browser format; unsupported presentation fails closed."""

    if draft.presentation.schema_version != "bh-presentation-v1alpha":
        raise ValueError("unsupported presentation schema")
    by_id = {
        (item.object_kind, item.object_id, item.occurrence): item
        for item in draft.presentation.objects
    }
    if len(by_id) != len(draft.presentation.objects):
        raise ValueError("presentation identity must include a unique occurrence")
    unused = set(by_id)
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    occurrences: dict[tuple[str, str], int] = {}
    for node in draft.equipment:
        occurrence = occurrences.get(("equipment", node.object_id), 0)
        occurrences[("equipment", node.object_id)] = occurrence + 1
        unused.discard(("equipment", node.object_id, occurrence))
        view = by_id.get(
            ("equipment", node.object_id, occurrence), ObjectPresentationDto(node.object_id)
        )
        if view.extension_namespace != "react-flow/v1alpha":
            raise ValueError("unsupported presentation extension namespace")
        extension = json.loads(view.extensions_json)
        extra = extension.get("node", {})
        transient = extension.get("runtime", {"status": "draft", "validity": "UNKNOWN"})
        kind = "heat-exchanger" if node.model_id == "heat_exchanger" else node.model_id
        captions = {item.name: item for item in view.parameters}
        params = {}
        for parameter in node.parameters:
            caption = captions.get(parameter.name)
            params[parameter.name] = {
                "label": caption.label if caption else parameter.name,
                "quantity": {"value": parameter.quantity.value, "unit": parameter.quantity.unit},
                "description": caption.description if caption else None,
            }
        nodes.append(
            {
                **extra,
                "id": node.object_id,
                "position": {
                    "x": view.x if view.x is not None else 0.0,
                    "y": view.y if view.y is not None else 0.0,
                },
                "data": {
                    **transient,
                    "label": view.label if view.label is not None else node.object_id,
                    "kind": kind,
                    "parameters": params,
                },
            }
        )
    for edge in draft.connections:
        occurrence = occurrences.get(("connection", edge.object_id), 0)
        occurrences[("connection", edge.object_id)] = occurrence + 1
        unused.discard(("connection", edge.object_id, occurrence))
        view = by_id.get(
            ("connection", edge.object_id, occurrence), ObjectPresentationDto(edge.object_id)
        )
        if view.extension_namespace != "react-flow/v1alpha":
            raise ValueError("unsupported presentation extension namespace")
        edges.append(
            {
                **json.loads(view.extensions_json).get("edge", {}),
                "id": edge.object_id,
                "source": edge.source_id,
                "target": edge.target_id,
                "sourceHandle": edge.source_port,
                "targetHandle": edge.target_port,
            }
        )
    if unused:
        raise ValueError("presentation refers to an absent draft object occurrence")
    return PfdDraftDto.model_validate(
        {
            "schemaVersion": "v1alpha",
            "draftId": draft.draft_id,
            "revision": draft.revision,
            "baseCaseId": draft.base_case_id,
            "updatedAt": draft.updated_at,
            "nodes": nodes,
            "edges": edges,
        }
    )
