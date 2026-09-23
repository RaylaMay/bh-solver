"""Deterministic UI workload fixture; incomplete test equipment, never a solved case."""

from bh_sim.boundary import contracts as c


def reference_scene(count: int) -> c.PfdDocumentDto:
    """Create rows of explicit source/heater/sink units with unset required inputs."""
    nodes = tuple(
        c.EquipmentDto(
            f"unit:bench-{i}",
            "source" if i % 10 == 0 else "sink" if i % 10 == 9 or i == count - 1 else "heater",
            (),
        )
        for i in range(count)
    )
    streams = tuple(
        c.ConnectionDto(
            f"stream:bench-{i}", nodes[i - 1].object_id, nodes[i].object_id, "out-0", "in-0"
        )
        for i in range(count)
        if i % 10
    )
    objects = tuple(
        c.PfdObjectDto(
            n.object_id,
            f"U-{i + 1:03}",
            c.CanvasPointDto(float(i % 10 * 180), float(i // 10 * 150)),
            expanded=True,
        )
        for i, n in enumerate(nodes)
    ) + tuple(c.PfdObjectDto(s.object_id, f"S-{i + 1:03}") for i, s in enumerate(streams))
    presentation = c.PresentationDto(
        tuple(
            c.ObjectPresentationDto(
                o.object_id,
                o.tag,
                o.position.x,
                o.position.y,
                object_kind="equipment" if i < count else "connection",
            )
            for i, o in enumerate(objects)
        )
    )
    return c.PfdDocumentDto(
        c.DraftDto("Renderer reference fixture", 1, None, "", nodes, streams, presentation),
        objects,
        next_stream_number=len(streams) + 1,
    )
