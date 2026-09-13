"""Reference-draft conversion at the scientific adapter boundary.

This is the unchanged v1alpha mapping, now consuming neutral draft values.
Reference coefficients, equations and canonical artifact meanings are retained.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from bh_sim.boundary.contracts import DiagnosticDto, DraftDto
from bh_sim.core import (
    AiProfile,
    CaseDefinition,
    ConnectionDefinition,
    Diagnostic,
    DraftRevision,
    MaterialReference,
    PropertyPackageReference,
    Quantity,
    StableId,
    UnitDefinition,
)
from bh_sim.engine.models import (
    COLD_IN,
    COLD_OUT,
    HOT_IN,
    HOT_OUT,
    INLET,
    INLET_A,
    INLET_B,
    OUTLET,
    OUTLET_A,
    OUTLET_B,
)
from bh_sim.engine.properties import PolynomialLiquidPackage, ReferenceLiquid

REFERENCE_PACKAGE_ID = StableId("properties:reference-liquid-v1alpha")
REFERENCE_MATERIAL_ID = StableId("material:reference-coolant")


def _stable(prefix: str, raw: str) -> StableId:
    cleaned = re.sub(r"[^A-Za-z0-9_.:-]", "-", raw).strip("-.")
    if not cleaned:
        cleaned = "unnamed"
    return StableId(f"{prefix}:{cleaned}"[:128])


_PARAMETERS = {
    "source": {"massFlow": "mass_flow", "temperature": "temperature", "pressure": "pressure"},
    "heater": {"duty": "duty"},
    "radiator": {"targetTemperature": "outlet_temperature", "emissivity": "emissivity"},
    "splitter": {"splitFraction": "split_fraction"},
    "heat_exchanger": {"effectiveness": "effectiveness"},
}
_INPUT_PORTS = {
    "sink": (INLET,),
    "heater": (INLET,),
    "radiator": (INLET,),
    "mixer": (INLET_A, INLET_B),
    "splitter": (INLET,),
    "heat_exchanger": (HOT_IN, COLD_IN),
}
_OUTPUT_PORTS = {
    "source": (OUTLET,),
    "heater": (OUTLET,),
    "radiator": (OUTLET,),
    "mixer": (OUTLET,),
    "splitter": (OUTLET_A, OUTLET_B),
    "heat_exchanger": (HOT_OUT, COLD_OUT),
}


@dataclass(frozen=True)
class AdaptedDraft:
    revision: DraftRevision
    node_ids: dict[StableId, str]
    edge_ids: dict[StableId, str]


def reference_property_package() -> PolynomialLiquidPackage:
    """Return the transparent illustrative backend used by the first slice."""

    return PolynomialLiquidPackage(
        REFERENCE_PACKAGE_ID,
        (
            ReferenceLiquid(
                REFERENCE_MATERIAL_ID,
                "Illustrative constant-cp coolant",
                density_kg_m3=1000.0,
                cp_a_j_kg_k=1000.0,
                evidence_minimum_temperature_k=250.0,
                evidence_maximum_temperature_k=1200.0,
                hard_minimum_temperature_k=100.0,
                hard_maximum_temperature_k=2500.0,
                evidence_reference="MODEL-CARD-REFERENCE-LIQUID-V1ALPHA",
            ),
        ),
    )


def _handle_index(handle: str | None, prefix: str) -> int:
    if handle is None:
        return 0
    match = re.fullmatch(rf"{prefix}-(\d+)", handle)
    if match is None:
        raise ValueError(f"invalid {prefix} handle: {handle!r}")
    return int(match.group(1))


def draft_to_contract(draft: DraftDto) -> AdaptedDraft:
    labels = {
        item.object_id: item.label
        for item in draft.presentation.objects
        if item.label is not None and item.object_kind == "equipment"
    }
    unit_ids = {node.object_id: _stable("unit", node.object_id) for node in draft.equipment}
    edge_ids = {edge.object_id: _stable("connection", edge.object_id) for edge in draft.connections}
    nodes_by_id = {node.object_id: node for node in draft.equipment}
    if len(nodes_by_id) != len(draft.equipment):
        raise ValueError("PFD node IDs must be unique")
    if len(edge_ids) != len(draft.connections):
        raise ValueError("PFD edge IDs must be unique")

    units = []
    for node in draft.equipment:
        mapping = _PARAMETERS.get(node.model_id, {})
        parameters = []
        for external_name, parameter in ((item.name, item) for item in node.parameters):
            if external_name not in mapping:
                external_kind = (
                    "heat-exchanger" if node.model_id == "heat_exchanger" else node.model_id
                )
                raise ValueError(
                    f"unsupported parameter {external_name!r} on {external_kind} {node.object_id}"
                )
            unit = "1" if parameter.quantity.unit == "fraction" else parameter.quantity.unit
            parameters.append((mapping[external_name], Quantity(parameter.quantity.value, unit)))
        metadata = (
            (("material_id", str(REFERENCE_MATERIAL_ID)),) if node.model_id == "source" else ()
        )
        units.append(
            UnitDefinition(
                unit_ids[node.object_id],
                node.model_id,
                labels.get(node.object_id, node.object_id),
                tuple(sorted(parameters)),
                metadata,
            )
        )

    connections = []
    for edge in draft.connections:
        try:
            source_node = nodes_by_id[edge.source_id]
            target_node = nodes_by_id[edge.target_id]
        except KeyError as error:
            raise ValueError(f"edge {edge.object_id} references an unknown node") from error
        output_ports = _OUTPUT_PORTS.get(source_node.model_id, ())
        input_ports = _INPUT_PORTS.get(target_node.model_id, ())
        output_index = _handle_index(edge.source_port, "out")
        input_index = _handle_index(edge.target_port, "in")
        try:
            source_port = output_ports[output_index]
            target_port = input_ports[input_index]
        except IndexError as error:
            raise ValueError(
                f"edge {edge.object_id} references a nonexistent equipment port"
            ) from error
        connections.append(
            ConnectionDefinition(
                edge_ids[edge.object_id],
                unit_ids[edge.source_id],
                source_port,
                unit_ids[edge.target_id],
                target_port,
            )
        )

    case_id = _stable("case", draft.base_case_id or draft.draft_id)
    case = CaseDefinition(
        case_id=case_id,
        title=draft.draft_id,
        materials=(
            MaterialReference(
                REFERENCE_MATERIAL_ID,
                "Illustrative reference coolant",
                REFERENCE_PACKAGE_ID,
                "MODEL-CARD-REFERENCE-LIQUID-V1ALPHA",
            ),
        ),
        property_packages=(
            PropertyPackageReference(
                REFERENCE_PACKAGE_ID,
                "polynomial-liquid",
                "v1alpha",
                "reference-coolant-v1",
            ),
        ),
        units=tuple(units),
        connections=tuple(connections),
        specifications=(),
        ai_profile=AiProfile.REVIEW,
    )
    revision_id = _stable("revision", f"{draft.draft_id}:{draft.revision}")
    return AdaptedDraft(
        DraftRevision(
            revision_id,
            case_id,
            draft.revision,
            case,
            (),
            draft.updated_at,
        ),
        {value: key for key, value in unit_ids.items()},
        {value: key for key, value in edge_ids.items()},
    )


def diagnostic_to_dto(
    diagnostic: Diagnostic,
    node_ids: dict[StableId, str],
    edge_ids: dict[StableId, str],
) -> DiagnosticDto:
    if diagnostic.severity == "error":
        severity = "error"
    elif diagnostic.severity == "warning":
        severity = "warning"
    else:
        severity = "info"
    subject = None
    if diagnostic.subject_id is not None:
        subject = node_ids.get(diagnostic.subject_id) or edge_ids.get(diagnostic.subject_id)
    return DiagnosticDto(
        severity=severity,
        code=diagnostic.code.upper().replace("-", "_"),
        message=diagnostic.message,
        subject_id=subject,
    )
