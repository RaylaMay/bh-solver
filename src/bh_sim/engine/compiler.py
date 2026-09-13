"""Topology, port, specification, and degrees-of-freedom compilation."""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from bh_sim.core import (
    CaseDefinition,
    CompiledFlowsheet,
    Diagnostic,
    PortDirection,
    StableId,
    VariableDefinition,
    ports_are_compatible,
)
from bh_sim.core.json_codec import contract_digest

from .catalog import ModelCatalog


@dataclass(frozen=True)
class ValidationReport:
    valid: bool
    degrees_of_freedom: int
    diagnostics: tuple[Diagnostic, ...]
    compiled: CompiledFlowsheet


class FlowsheetCompiler:
    def __init__(self, catalog: ModelCatalog) -> None:
        self.catalog = catalog

    def compile(
        self,
        case: CaseDefinition,
        *,
        revision_id: StableId | None = None,
    ) -> ValidationReport:
        diagnostics: list[Diagnostic] = []
        graph = nx.DiGraph()
        definitions = {unit.unit_id: unit for unit in case.units}
        graph.add_nodes_from(definitions)
        descriptors = {}
        missing = 0

        for unit in case.units:
            try:
                descriptor = self.catalog.descriptor(unit.model_id)
                descriptors[unit.unit_id] = descriptor
            except KeyError:
                diagnostics.append(
                    Diagnostic(
                        "unknown-model", f"Unknown model {unit.model_id}", "error", unit.unit_id
                    )
                )
                continue
            parameters = dict(unit.parameters)
            metadata = dict(unit.metadata)
            for name in descriptor.required_parameters:
                if name not in parameters:
                    missing += 1
                    diagnostics.append(
                        Diagnostic(
                            "missing-parameter",
                            f"{unit.name} requires parameter {name}",
                            "error",
                            unit.unit_id,
                        )
                    )
            for name in descriptor.required_metadata:
                if name not in metadata:
                    missing += 1
                    diagnostics.append(
                        Diagnostic(
                            "missing-metadata",
                            f"{unit.name} requires metadata {name}",
                            "error",
                            unit.unit_id,
                        )
                    )

        incoming: dict[tuple[StableId, StableId], int] = {}
        outgoing: dict[tuple[StableId, StableId], int] = {}
        for connection in case.connections:
            source_definition = definitions.get(connection.source_unit_id)
            target_definition = definitions.get(connection.target_unit_id)
            if source_definition is None or target_definition is None:
                diagnostics.append(
                    Diagnostic(
                        "unknown-unit",
                        "Connection references an unknown unit",
                        "error",
                        connection.connection_id,
                    )
                )
                continue
            source_descriptor = descriptors.get(source_definition.unit_id)
            target_descriptor = descriptors.get(target_definition.unit_id)
            if source_descriptor is None or target_descriptor is None:
                continue
            source_port = next(
                (
                    port
                    for port in source_descriptor.ports
                    if port.port_id == connection.source_port_id
                ),
                None,
            )
            target_port = next(
                (
                    port
                    for port in target_descriptor.ports
                    if port.port_id == connection.target_port_id
                ),
                None,
            )
            if source_port is None or target_port is None:
                diagnostics.append(
                    Diagnostic(
                        "unknown-port",
                        "Connection references an unknown port",
                        "error",
                        connection.connection_id,
                    )
                )
                continue
            if not ports_are_compatible(source_port, target_port):
                diagnostics.append(
                    Diagnostic(
                        "incompatible-port",
                        "Connection ports are incompatible",
                        "error",
                        connection.connection_id,
                    )
                )
                continue
            source_key = (connection.source_unit_id, connection.source_port_id)
            target_key = (connection.target_unit_id, connection.target_port_id)
            outgoing[source_key] = outgoing.get(source_key, 0) + 1
            incoming[target_key] = incoming.get(target_key, 0) + 1
            if outgoing[source_key] > 1:
                diagnostics.append(
                    Diagnostic(
                        "material-fanout",
                        "Use a splitter instead of connecting one outlet twice",
                        "error",
                        connection.source_unit_id,
                    )
                )
            if incoming[target_key] > 1:
                diagnostics.append(
                    Diagnostic(
                        "multiple-feeds",
                        "An input port accepts only one stream",
                        "error",
                        connection.target_unit_id,
                    )
                )
            graph.add_edge(connection.source_unit_id, connection.target_unit_id)

        for unit_id, descriptor in descriptors.items():
            for port in descriptor.ports:
                if (
                    port.required
                    and port.direction is PortDirection.INPUT
                    and incoming.get((unit_id, port.port_id), 0) == 0
                ):
                    missing += 1
                    diagnostics.append(
                        Diagnostic(
                            "unconnected-input",
                            f"{definitions[unit_id].name} input {port.name} is not connected",
                            "error",
                            unit_id,
                        )
                    )

        recycle_groups = tuple(
            tuple(sorted(component))
            for component in nx.strongly_connected_components(graph)
            if len(component) > 1 or any(graph.has_edge(node, node) for node in component)
        )
        if recycle_groups:
            diagnostics.append(
                Diagnostic(
                    "recycle-not-supported",
                    "Recycle groups are detected but require the next solver milestone",
                    "error",
                )
            )

        if nx.is_directed_acyclic_graph(graph):
            execution_order = tuple(nx.lexicographical_topological_sort(graph, key=str))
        else:
            condensation = nx.condensation(graph)
            execution: list[StableId] = []
            for component_index in nx.topological_sort(condensation):
                members = condensation.nodes[component_index]["members"]
                execution.extend(sorted(members))
            execution_order = tuple(execution)

        variables: list[VariableDefinition] = []
        for unit in case.units:
            descriptor = descriptors.get(unit.unit_id)
            if descriptor is None:
                continue
            specified = set(dict(unit.parameters))
            for name in descriptor.required_parameters:
                variables.append(
                    VariableDefinition(
                        name=f"{unit.unit_id}.{name}",
                        owner_id=unit.unit_id,
                        dimension="declared-by-model",
                        scale=1.0,
                        specified=name in specified,
                    )
                )

        source_hash = contract_digest(case)
        compiled = CompiledFlowsheet(
            compiled_id=StableId(f"compiled:{source_hash[:24]}"),
            source_case_id=case.case_id,
            source_revision_id=revision_id,
            source_hash=source_hash,
            execution_order=execution_order,
            variables=tuple(variables),
            degrees_of_freedom=missing,
            recycle_groups=recycle_groups,
            diagnostics=tuple(diagnostics),
        )
        valid = missing == 0 and not any(item.severity == "error" for item in diagnostics)
        return ValidationReport(valid, missing, tuple(diagnostics), compiled)
