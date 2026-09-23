"""Native draft editing policy over immutable neutral documents and declared ports.

Local port compatibility is an editing constraint, never graph compilation or
scientific validation. Every edit is atomic; rejected edits retain the input DTO.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol
from uuid import uuid4

from bh_sim.boundary import contracts as c

from .ports import DraftRepositoryPort
from .services import CommandRejected


class PfdRepositoryPort(Protocol):
    """Append-only native document revisions, separate from calculation artifacts."""

    def save(self, document: c.PfdDocumentDto) -> c.PfdDocumentDto: ...
    def latest(self, draft_id: str) -> c.PfdDocumentDto: ...
    def summaries(self) -> tuple[c.DraftSummaryDto, ...]: ...


class QuantityPort(Protocol):
    """Convert explicit finite scalar units using the established quantity adapter."""

    def convert(self, quantity: c.QuantityDto, target_unit: str) -> c.QuantityDto: ...


pfd_engineering_content_hash = c.pfd_engineering_content_hash


class PfdService:
    """Application commands for catalogue, edits, restoration and explicit persistence."""

    def __init__(
        self,
        catalogue: c.PfdCatalogueDto,
        repository: PfdRepositoryPort,
        legacy: DraftRepositoryPort,
        quantities: QuantityPort,
    ) -> None:
        self.catalogue, self.repository = catalogue, repository
        self.legacy, self.quantities = legacy, quantities
        self.models = {m.model_id: m for m in catalogue.models}

    def import_draft(self, draft: c.DraftDto) -> c.PfdDocumentDto:
        """Add native presentation without modifying the original browser snapshot."""
        objects = []
        presentations = {p.object_id: p for p in draft.presentation.objects}
        for index, item in enumerate((*draft.equipment, *draft.connections)):
            p = presentations.get(item.object_id)
            tag = (
                p.label
                if p and p.label
                else (
                    f"S-{index - len(draft.equipment) + 1:03}"
                    if isinstance(item, c.ConnectionDto)
                    else f"{item.model_id.upper()}-{index + 1:03}"
                )
            )
            objects.append(
                c.PfdObjectDto(
                    item.object_id,
                    tag,
                    c.CanvasPointDto(p.x or 0.0, p.y or 0.0)
                    if p
                    else c.CanvasPointDto(float(index % 5 * 200), float(index // 5 * 140)),
                )
            )
        document = c.PfdDocumentDto(
            draft, tuple(objects), next_stream_number=len(draft.connections) + 1
        )
        self.check(document)
        return document

    @staticmethod
    def recover_presentation(document: c.PfdDocumentDto) -> c.PfdDocumentDto:
        """Remove stale visual membership while retaining each recoverable named group."""

        stream_ids = {stream.object_id for stream in document.draft.connections}
        groups = tuple(
            replace(
                group,
                member_stream_ids=tuple(
                    identifier for identifier in group.member_stream_ids if identifier in stream_ids
                ),
            )
            for group in document.visual_groups
        )
        group_ids = {group.group_id for group in groups}
        preferences = document.layer_preferences
        if preferences.active_visual_group_id not in group_ids:
            preferences = replace(preferences, active_visual_group_id=None)
        return replace(document, visual_groups=groups, layer_preferences=preferences)

    def open(self, draft_id: str) -> c.PfdDocumentDto:
        """Prefer native snapshots; import legacy only when no native revision exists."""
        try:
            document = self.repository.latest(draft_id)
        except KeyError:
            document = self.import_draft(self.legacy.latest(draft_id))
        document = self.recover_presentation(document)
        self.check(document)
        return document

    def listing(self) -> c.DraftListDto:
        """Merge navigation identities, with native revision summaries taking precedence."""
        summaries = {s.draft_id: s for s in self.legacy.summaries()}
        summaries.update({s.draft_id: s for s in self.repository.summaries()})
        return c.DraftListDto(tuple(summaries[k] for k in sorted(summaries)))

    def check(self, document: c.PfdDocumentDto) -> None:
        """Check identity and presentation framing; allow incomplete inputs."""
        draft = document.draft
        ids = [o.object_id for o in (*draft.equipment, *draft.connections)]
        if len(ids) != len(set(ids)) or any(not i for i in ids):
            raise CommandRejected("DUPLICATE_ID", "Object identities must be unique")
        if len(document.objects) != len(ids) or {o.object_id for o in document.objects} != set(ids):
            raise CommandRejected(
                "PRESENTATION_MISMATCH", "Presentation must identify each object once"
            )
        stream_ids = {s.object_id for s in draft.connections}
        tags = []
        for obj in document.objects:
            if (
                not obj.tag.strip()
                or obj.tag != obj.tag.strip()
                or len(obj.tag) > 64
                or any(ord(char) < 32 for char in obj.tag)
            ):
                raise CommandRejected(
                    "INVALID_TAG", "Use 1–64 printable characters without outer spaces"
                )
            if obj.object_id in stream_ids:
                tags.append(obj.tag.casefold())
            if len(obj.route) > 64 or any(
                a.x != b.x and a.y != b.y for a, b in zip(obj.route, obj.route[1:], strict=False)
            ):
                raise CommandRejected(
                    "INVALID_ROUTE", "Routes require at most 64 orthogonal points"
                )
            if len({n.name for n in obj.notation}) != len(obj.notation):
                raise CommandRejected("INVALID_NOTATION", "Duplicate input notation")
        if len(tags) != len(set(tags)):
            raise CommandRejected("TAG_CONFLICT", "Stream tags must be unique within this case")
        group_ids = [group.group_id for group in document.visual_groups]
        if len(group_ids) != len(set(group_ids)):
            raise CommandRejected("GROUP_CONFLICT", "Visual group identities must be unique")
        if document.layer_preferences.active_visual_group_id not in {None, *group_ids}:
            raise CommandRejected("MISSING_GROUP", "Active visual group is not present")
        for group in document.visual_groups:
            if not set(group.member_stream_ids) <= stream_ids:
                raise CommandRejected(
                    "MISSING_GROUP_MEMBER", "Visual group references a missing stream"
                )
        subsystem_ids = [item.subsystem_id for item in document.engineering_subsystems]
        if len(subsystem_ids) != len(set(subsystem_ids)):
            raise CommandRejected(
                "SUBSYSTEM_CONFLICT", "Engineering subsystem identities must be unique"
            )
        object_ids = set(ids)
        for subsystem in document.engineering_subsystems:
            if not set(subsystem.member_object_ids) <= object_ids:
                raise CommandRejected(
                    "MISSING_SUBSYSTEM_MEMBER", "Engineering subsystem references a missing object"
                )
        # Imported incomplete/unsupported models remain visible; new connections are
        # checked against the catalogue when created, not silently repaired on open.
        for equipment in draft.equipment:
            if len({p.name for p in equipment.parameters}) != len(equipment.parameters):
                raise CommandRejected("INVALID_INPUT", "Duplicate parameter names")
            obj = next(o for o in document.objects if o.object_id == equipment.object_id)
            params = {p.name: p.quantity for p in equipment.parameters}
            for notation in obj.notation:
                q = params.get(notation.name)
                if q is None or q.unit != notation.unit or q.value != float(notation.text):
                    raise CommandRejected(
                        "INVALID_NOTATION", "Input notation differs from submitted value"
                    )

    def save(self, document: c.PfdDocumentDto) -> c.PfdDocumentDto:
        """Validate document framing then acknowledge the actually persisted revision."""
        document = self.recover_presentation(document)
        self.check(document)
        return self.repository.save(document)

    def _next_tag(self, document: c.PfdDocumentDto) -> tuple[str, int]:
        used = {o.tag.casefold() for o in document.objects}
        number = max(document.next_stream_number, document.settings.stream_start)
        while True:
            tag = f"{document.settings.stream_prefix}{number:0{document.settings.stream_padding}}"
            number += 1
            if tag.casefold() not in used:
                return tag, number

    def _port(
        self, document: c.PfdDocumentDto, identifier: str, name: str, direction: str
    ) -> c.PfdPortDto:
        node = next(n for n in document.draft.equipment if n.object_id == identifier)
        port = next(
            (
                p
                for p in self.models[node.model_id].ports
                if p.name == name and p.direction == direction
            ),
            None,
        )
        if port is None:
            raise CommandRejected("PORT_DIRECTION", "Choose an output and a compatible input")
        occupied = sum(
            (s.source_id == identifier and (s.source_port or "out-0") == name)
            or (s.target_id == identifier and (s.target_port or "in-0") == name)
            for s in document.draft.connections
        )
        if occupied >= port.maximum_connections:
            raise CommandRejected(
                "PORT_OCCUPIED", "Port already connected; insert an explicit splitter"
            )
        return port

    def edit(self, document: c.PfdDocumentDto, edit: c.PfdEdit) -> c.PfdDocumentDto:
        """Apply one atomic command; presentation-only operations preserve engineering fields."""
        document = self.recover_presentation(document)
        self.check(document)
        nodes, streams = list(document.draft.equipment), list(document.draft.connections)
        objects = {o.object_id: o for o in document.objects}
        result = document
        if isinstance(edit, c.AddEquipmentEdit):
            model = self.models[edit.model_id]
            identifier = "unit:" + uuid4().hex
            nodes.append(c.EquipmentDto(identifier, model.model_id, ()))
            used = {o.tag.casefold() for o in objects.values()}
            number = 1
            while f"{model.title}-{number:03}".casefold() in used:
                number += 1
            objects[identifier] = c.PfdObjectDto(
                identifier, f"{model.title}-{number:03}", edit.position
            )
        elif isinstance(edit, c.ConnectPortsEdit):
            if edit.source_id == edit.target_id:
                raise CommandRejected("SELF_CONNECTION", "Connect distinct equipment")
            output = self._port(document, edit.source_id, edit.source_port, "output")
            incoming = self._port(document, edit.target_id, edit.target_port, "input")
            if output.kind != incoming.kind:
                raise CommandRejected("PORT_KIND", "Material and energy ports cannot be joined")
            identifier = "stream:" + uuid4().hex
            streams.append(
                c.ConnectionDto(
                    identifier, edit.source_id, edit.target_id, edit.source_port, edit.target_port
                )
            )
            tag, number = self._next_tag(document)
            objects[identifier] = c.PfdObjectDto(identifier, tag)
            result = replace(result, next_stream_number=number)
        elif isinstance(edit, c.RemoveObjectsEdit):
            selected = set(edit.object_ids)
            if not selected <= set(objects):
                raise KeyError("missing selected object")
            attached = {
                s.object_id for s in streams if s.source_id in selected or s.target_id in selected
            }
            if attached and not edit.confirmed_connected:
                raise CommandRejected(
                    "CONNECTED_DELETE", "Confirm removal of equipment and its connected streams"
                )
            selected |= attached
            nodes = [n for n in nodes if n.object_id not in selected]
            streams = [s for s in streams if s.object_id not in selected]
            objects = {
                k: replace(o, parent_stream_id=None, branch_suffix=None)
                if o.parent_stream_id in selected
                else o
                for k, o in objects.items()
                if k not in selected
            }
            result = replace(
                result,
                visual_groups=tuple(
                    replace(
                        group,
                        member_stream_ids=tuple(
                            identifier
                            for identifier in group.member_stream_ids
                            if identifier not in selected
                        ),
                    )
                    for group in result.visual_groups
                ),
                engineering_subsystems=tuple(
                    replace(
                        subsystem,
                        member_object_ids=tuple(
                            identifier
                            for identifier in subsystem.member_object_ids
                            if identifier not in selected
                        ),
                    )
                    for subsystem in result.engineering_subsystems
                ),
            )
        elif isinstance(edit, c.MoveObjectsEdit):
            for identifier, point in edit.positions:
                objects[identifier] = replace(objects[identifier], position=point)
        elif isinstance(edit, c.ConfigureInputEdit):
            node = next(n for n in nodes if n.object_id == edit.object_id)
            parameter = next(
                p for p in self.models[node.model_id].parameters if p.name == edit.name
            )
            params = [p for p in node.parameters if p.name != edit.name]
            obj = objects[edit.object_id]
            notation = [n for n in obj.notation if n.name != edit.name]
            if edit.text.strip():
                quantity = c.QuantityDto(float(edit.text), edit.unit)
                self.quantities.convert(quantity, parameter.canonical_unit)
                params.append(c.ParameterDto(edit.name, quantity))
                old = next((n for n in obj.notation if n.name == edit.name), None)
                notation.append(
                    c.InputNotationDto(
                        edit.name, edit.text, edit.unit, old.display_unit if old else None
                    )
                )
            nodes[nodes.index(node)] = replace(node, parameters=tuple(params))
            objects[obj.object_id] = replace(obj, notation=tuple(notation))
        elif isinstance(edit, c.DisplayUnitEdit):
            node = next(n for n in nodes if n.object_id == edit.object_id)
            quantity = next(p.quantity for p in node.parameters if p.name == edit.name)
            if edit.unit:
                self.quantities.convert(quantity, edit.unit)
            obj = objects[edit.object_id]
            notation = [n for n in obj.notation if n.name != edit.name]
            old = next(
                (n for n in obj.notation if n.name == edit.name),
                c.InputNotationDto(edit.name, str(quantity.value), quantity.unit),
            )
            objects[obj.object_id] = replace(
                obj, notation=(*notation, replace(old, display_unit=edit.unit))
            )
        elif isinstance(edit, c.RenameObjectEdit):
            old = objects[edit.object_id]
            stream_ids = {s.object_id for s in streams}
            conflict = next(
                (
                    o
                    for o in objects.values()
                    if o.object_id != old.object_id
                    and o.object_id in stream_ids
                    and o.tag.casefold() == edit.tag.casefold()
                ),
                None,
            )
            if old.object_id in stream_ids and conflict:
                if edit.swap:
                    objects[conflict.object_id] = replace(
                        conflict, tag=old.tag, parent_stream_id=None, branch_suffix=None
                    )
                elif document.settings.collision == "next-available":
                    tag, number = self._next_tag(document)
                    edit = replace(edit, tag=tag)
                    result = replace(result, next_stream_number=number)
                else:
                    raise CommandRejected(
                        "TAG_CONFLICT",
                        f"{edit.tag} belongs to stream {conflict.object_id}; "
                        "choose another tag or explicitly swap",
                    )
            objects[old.object_id] = replace(
                old, tag=edit.tag, parent_stream_id=None, branch_suffix=None
            )
            if edit.rename_family:
                for key, obj in list(objects.items()):
                    if obj.parent_stream_id == old.object_id and obj.branch_suffix:
                        objects[key] = replace(obj, tag=edit.tag + obj.branch_suffix)
        elif isinstance(edit, c.RouteStreamEdit):
            if edit.object_id not in {s.object_id for s in streams}:
                raise KeyError("stream")
            objects[edit.object_id] = replace(objects[edit.object_id], route=edit.points)
        elif isinstance(edit, c.DetailsEdit):
            objects[edit.object_id] = replace(
                objects[edit.object_id], expanded=edit.expanded, pinned=edit.pinned
            )
        elif isinstance(edit, c.SettingsEdit):
            for unit in edit.settings.units:
                self.quantities.convert(c.QuantityDto(1.0, unit.canonical_unit), unit.display_unit)
            result = replace(
                result,
                settings=edit.settings,
                layer_preferences=replace(
                    result.layer_preferences, base_stream_colour=edit.settings.stream_colour
                ),
            )
        elif isinstance(edit, c.ViewportEdit):
            result = replace(result, viewport_centre=edit.centre, viewport_scale=edit.scale)
        elif isinstance(edit, c.UpsertVisualStreamGroupEdit):
            group = edit.group
            visual_groups = [
                item for item in result.visual_groups if item.group_id != group.group_id
            ]
            visual_groups.append(group)
            result = replace(
                result, visual_groups=tuple(sorted(visual_groups, key=lambda item: item.order))
            )
        elif isinstance(edit, c.RemoveVisualStreamGroupEdit):
            if edit.group_id not in {item.group_id for item in result.visual_groups}:
                raise KeyError("visual group")
            result = replace(
                result,
                visual_groups=tuple(
                    item for item in result.visual_groups if item.group_id != edit.group_id
                ),
                layer_preferences=replace(
                    result.layer_preferences,
                    active_visual_group_id=None
                    if result.layer_preferences.active_visual_group_id == edit.group_id
                    else result.layer_preferences.active_visual_group_id,
                ),
            )
        elif isinstance(edit, c.SetPfdLayerPreferencesEdit):
            result = replace(
                result,
                layer_preferences=edit.preferences,
                settings=replace(
                    result.settings, stream_colour=edit.preferences.base_stream_colour
                ),
            )
        elif isinstance(edit, c.UpsertEngineeringSubsystemEdit):
            subsystem = edit.subsystem
            subsystems = [
                item
                for item in result.engineering_subsystems
                if item.subsystem_id != subsystem.subsystem_id
            ]
            result = replace(result, engineering_subsystems=(*subsystems, subsystem))
        elif isinstance(edit, c.RemoveEngineeringSubsystemEdit):
            if edit.subsystem_id not in {
                item.subsystem_id for item in result.engineering_subsystems
            }:
                raise KeyError("engineering subsystem")
            result = replace(
                result,
                engineering_subsystems=tuple(
                    item
                    for item in result.engineering_subsystems
                    if item.subsystem_id != edit.subsystem_id
                ),
            )
        elif isinstance(edit, c.SplitStreamEdit):
            return self._split(document, edit)
        elif isinstance(edit, c.PasteEquipmentEdit):
            return self._paste(document, edit)
        else:
            raise ValueError("unsupported PFD edit")
        # Retain browser extension bytes while synchronizing shared labels/positions.
        presentations = {p.object_id: p for p in document.draft.presentation.objects}
        node_ids = {n.object_id for n in nodes}
        presentation = c.PresentationDto(
            tuple(
                replace(
                    presentations.get(
                        o.object_id,
                        c.ObjectPresentationDto(
                            o.object_id,
                            object_kind="equipment" if o.object_id in node_ids else "connection",
                        ),
                    ),
                    label=o.tag,
                    x=o.position.x,
                    y=o.position.y,
                )
                for o in objects.values()
            )
        )
        result = replace(
            result,
            draft=replace(
                document.draft,
                equipment=tuple(nodes),
                connections=tuple(streams),
                presentation=presentation,
            ),
            objects=tuple(objects.values()),
        )
        self.check(result)
        return result

    def _split(self, document: c.PfdDocumentDto, edit: c.SplitStreamEdit) -> c.PfdDocumentDto:
        """Insert an explicit splitter with unset fraction; names do not assert composition."""
        stream = next(s for s in document.draft.connections if s.object_id == edit.stream_id)
        parent = next(o for o in document.objects if o.object_id == edit.stream_id)
        work = self.edit(document, c.RemoveObjectsEdit((stream.object_id,), True))
        work = self.edit(work, c.AddEquipmentEdit("splitter", edit.position))
        splitter = work.draft.equipment[-1].object_id
        work = self.edit(
            work,
            c.ConnectPortsEdit(stream.source_id, stream.source_port or "out-0", splitter, "in-0"),
        )
        new_parent = work.draft.connections[-1].object_id
        work = self.edit(work, c.RenameObjectEdit(new_parent, parent.tag))
        # Preserve the original stream's permanent identity at the upstream segment.
        work = replace(
            work,
            draft=replace(
                work.draft,
                connections=tuple(
                    replace(s, object_id=stream.object_id) if s.object_id == new_parent else s
                    for s in work.draft.connections
                ),
            ),
            objects=tuple(
                replace(o, object_id=stream.object_id) if o.object_id == new_parent else o
                for o in work.objects
            ),
        )
        for suffix, target, port, output in (
            ("(a)", stream.target_id, stream.target_port or "in-0", "out-0"),
            ("(b)", edit.target_id, edit.target_port, "out-1"),
        ):
            work = self.edit(work, c.ConnectPortsEdit(splitter, output, target, port))
            branch = work.draft.connections[-1].object_id
            if document.settings.branch_names == "suffix":
                work = self.edit(work, c.RenameObjectEdit(branch, parent.tag + suffix))
                work = replace(
                    work,
                    objects=tuple(
                        replace(o, parent_stream_id=parent.object_id, branch_suffix=suffix)
                        if o.object_id == branch
                        else o
                        for o in work.objects
                    ),
                )
        self.check(work)
        return work

    def _paste(self, document: c.PfdDocumentDto, edit: c.PasteEquipmentEdit) -> c.PfdDocumentDto:
        """Assign new identities and tags; include only explicitly selected internal connections."""
        self.check(edit.source)
        work = document
        mapping = {}
        for node in edit.source.draft.equipment:
            if node.object_id not in edit.object_ids:
                continue
            obj = next(o for o in edit.source.objects if o.object_id == node.object_id)
            work = self.edit(
                work,
                c.AddEquipmentEdit(
                    node.model_id,
                    c.CanvasPointDto(
                        obj.position.x + edit.offset.x, obj.position.y + edit.offset.y
                    ),
                ),
            )
            identifier = work.draft.equipment[-1].object_id
            mapping[node.object_id] = identifier
            if not edit.reset_inputs:
                for p in node.parameters:
                    raw = next(
                        (n.text for n in obj.notation if n.name == p.name), str(p.quantity.value)
                    )
                    work = self.edit(
                        work, c.ConfigureInputEdit(identifier, p.name, raw, p.quantity.unit)
                    )
        if edit.connections:
            for stream in edit.source.draft.connections:
                if stream.source_id in mapping and stream.target_id in mapping:
                    work = self.edit(
                        work,
                        c.ConnectPortsEdit(
                            mapping[stream.source_id],
                            stream.source_port or "out-0",
                            mapping[stream.target_id],
                            stream.target_port or "in-0",
                        ),
                    )
        return work
