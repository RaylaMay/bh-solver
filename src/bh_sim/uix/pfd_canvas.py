"""Qt presentation of neutral PFD documents; geometry has no engineering authority.

Port gestures emit application-edit requests. Line crossings, proximity and grid
snaps never create a connection. Manual routes are orthogonal presentation points.
"""

from __future__ import annotations

import json

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QDragEnterEvent,
    QDragLeaveEvent,
    QDragMoveEvent,
    QDropEvent,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
)

from bh_sim.boundary import contracts as c

from .accessibility import system_reduced_motion


class EquipmentItem(QGraphicsPathItem):
    """Movable engineering symbol with typed port handles and plain text labels."""

    def __init__(self, identifier: str, model: c.PfdModelDto, tag: str) -> None:
        super().__init__()
        self.identifier = identifier
        path = QPainterPath()
        if model.model_id in {"heater", "heat_exchanger", "radiator"}:
            path.addEllipse(QRectF(0, 0, 90, 60))
            if model.model_id == "heat_exchanger":
                path.moveTo(15, 10)
                path.lineTo(75, 50)
                path.moveTo(15, 50)
                path.lineTo(75, 10)
            elif model.model_id == "radiator":
                for x in (25, 40, 55, 70):
                    path.moveTo(x, 8)
                    path.lineTo(x, 52)
            else:
                path.moveTo(30, 15)
                path.lineTo(30, 45)
                path.moveTo(30, 30)
                path.lineTo(60, 30)
                path.moveTo(60, 15)
                path.lineTo(60, 45)
        else:
            path.moveTo(0, 0)
            path.lineTo(65, 0)
            path.lineTo(90, 30)
            path.lineTo(65, 60)
            path.lineTo(0, 60)
            path.closeSubpath()
        self.setPath(path)
        self.setPen(QPen(QColor("#82D7CC"), 2))
        self.setBrush(QColor("#1A2630"))
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemIsMovable
        )
        self.setToolTip(f"{tag} · {model.title}\n{model.authority}")
        self.tag = QGraphicsSimpleTextItem(tag, self)
        self.tag.setBrush(QColor("#EDF3F5"))
        self.tag.setPos(0, 65)
        self.ports: dict[str, QGraphicsEllipseItem] = {}
        for direction in ("input", "output"):
            ports = [p for p in model.ports if p.direction == direction]
            for index, port in enumerate(ports):
                handle = QGraphicsEllipseItem(-5, -5, 10, 10, self)
                handle.setPos(
                    0 if direction == "input" else 90, 60 * (index + 1) / (len(ports) + 1)
                )
                handle.setBrush(QColor("#82D7CC" if port.kind == "material" else "#F0B673"))
                handle.setData(0, (identifier, port.name, direction))
                handle.setToolTip(f"{tag}: {port.name} · {direction} · {port.kind}")
                handle.setZValue(3)
                self.ports[port.name] = handle


class PfdCanvas(QGraphicsView):
    """Raster canvas with pan/zoom, selection, port gestures and orthogonal route editing."""

    edit_requested = Signal(object)
    selection_changed = Signal(object)
    legend_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("native-pfd-canvas")
        self.scene_data = QGraphicsScene(self)
        self.setScene(self.scene_data)
        self.setAccessibleName(
            "PFD canvas; use equipment list and Connect command for keyboard editing"
        )
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setAcceptDrops(True)
        self.catalogue: c.PfdCatalogueDto = c.PfdCatalogueDto(())
        self.placement_preview: QGraphicsRectItem | None = None
        self.document: c.PfdDocumentDto | None = None
        self.nodes: dict[str, EquipmentItem] = {}
        self.streams: dict[str, QGraphicsPathItem] = {}
        self.stream_halos: dict[str, QGraphicsPathItem] = {}
        self.stream_labels: dict[str, QGraphicsSimpleTextItem] = {}
        self.stream_status_icons: dict[str, QGraphicsSimpleTextItem] = {}
        self.stream_overlay_badges: dict[str, QGraphicsSimpleTextItem] = {}
        self.equipment_overlay_badges: dict[str, QGraphicsSimpleTextItem] = {}
        self.overlays: c.OverlaysDto | None = None
        self.show_overlays: bool = True
        self.flow_markers: dict[str, QGraphicsEllipseItem] = {}
        self.routes: dict[str, list[QPointF]] = {}
        self.visualization_frame: c.FlowVisualizationFrame | None = None
        self.animation_phase = 0.0
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.advance_animation)
        self.gesture: tuple[str, str, str] | None = None
        self.route_drag: str | None = None
        self.pan_origin: QPointF | None = None
        self.loading = False
        self.scene_data.selectionChanged.connect(self._selected)

    def selected_ids(self) -> tuple[str, ...]:
        """Return stable identities, never visual item addresses."""
        return tuple(
            item.identifier if isinstance(item, EquipmentItem) else str(item.data(1))
            for item in self.scene_data.selectedItems()
            if isinstance(item, EquipmentItem) or item.data(1)
        )

    def select_ids(self, identifiers: tuple[str, ...]) -> None:
        """Set engineering selection explicitly; group highlighting does not call this."""

        selected = set(identifiers)
        self.loading = True
        self.scene_data.clearSelection()
        for identifier in selected:
            item = self.nodes.get(identifier)
            if item is None:
                item = self.streams.get(identifier)
            if item is not None:
                item.setSelected(True)
        self.loading = False
        self.selection_changed.emit(self.selected_ids())

    def _selected(self) -> None:
        if not self.loading:
            self.selection_changed.emit(self.selected_ids())

    def set_document(self, document: c.PfdDocumentDto, catalogue: c.PfdCatalogueDto) -> None:
        """Render a detached snapshot; preserve current selection and pan during edits."""
        self.catalogue = catalogue
        selected = self.selected_ids()
        fresh = self.document is None or self.document.draft.draft_id != document.draft.draft_id
        if fresh:
            self.visualization_frame = None
        self.loading = True
        self.document = document
        self.scene_data.clear()
        self.nodes.clear()
        self.streams.clear()
        self.stream_halos.clear()
        self.stream_labels.clear()
        self.stream_status_icons.clear()
        self.stream_overlay_badges.clear()
        self.equipment_overlay_badges.clear()
        self.flow_markers.clear()
        objects = {o.object_id: o for o in document.objects}
        models = {m.model_id: m for m in catalogue.models}
        self.setBackgroundBrush(QColor(document.settings.background_colour))
        for node in document.draft.equipment:
            obj = objects[node.object_id]
            model = models.get(node.model_id, c.PfdModelDto(node.model_id, node.model_id, (), ()))
            item = EquipmentItem(node.object_id, model, obj.tag)
            self.scene_data.addItem(item)
            item.setPos(obj.position.x, obj.position.y)
            item.setSelected(node.object_id in selected)
            size = document.settings.handle_size
            for handle in item.ports.values():
                handle.setRect(-size, -size, size * 2, size * 2)
            self.nodes[node.object_id] = item
            equip_badge = QGraphicsSimpleTextItem("", item)
            equip_badge.setBrush(QColor("#38BDF8"))
            equip_badge.setPos(0, -20)
            equip_badge.setZValue(3)
            equip_badge.hide()
            self.equipment_overlay_badges[node.object_id] = equip_badge
            if obj.expanded or obj.pinned:
                rows = []
                if "inputs" in document.settings.detail_fields or any(
                    p.name in document.settings.detail_fields for p in model.parameters
                ):
                    rows = [
                        f"{p.name}: {p.quantity.value:g} {p.quantity.unit}"
                        for p in node.parameters
                        if "inputs" in document.settings.detail_fields
                        or p.name in document.settings.detail_fields
                    ]
                    rows += [
                        f"{p.title}: Input required"
                        for p in model.parameters
                        if p.name not in {v.name for v in node.parameters}
                        and (
                            "inputs" in document.settings.detail_fields
                            or p.name in document.settings.detail_fields
                        )
                    ]
                if "status" in document.settings.detail_fields:
                    rows.append("Not validated · Not run")
                detail = QGraphicsSimpleTextItem("\n".join(rows), item)
                detail.setBrush(QColor(document.settings.missing_colour))
                detail.setPos(0, 88)
        for stream in document.draft.connections:
            halo = QGraphicsPathItem()
            halo.setZValue(-2)
            self.scene_data.addItem(halo)
            self.stream_halos[stream.object_id] = halo
            line = QGraphicsPathItem()
            line.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
            line.setData(1, stream.object_id)
            line.setZValue(-1)
            line.setToolTip(objects[stream.object_id].tag + " · Material stream · Not run")
            self.scene_data.addItem(line)
            self.streams[stream.object_id] = line
            line.setSelected(stream.object_id in selected)
            label = QGraphicsSimpleTextItem(objects[stream.object_id].tag)
            label.setBrush(QColor(document.settings.stream_colour))
            self.scene_data.addItem(label)
            self.stream_labels[stream.object_id] = label
            status_icon = QGraphicsSimpleTextItem("")
            status_icon.setBrush(QColor("#F8FAFC"))
            status_icon.setZValue(3)
            status_icon.hide()
            self.scene_data.addItem(status_icon)
            self.stream_status_icons[stream.object_id] = status_icon
            overlay_badge = QGraphicsSimpleTextItem("")
            overlay_badge.setBrush(QColor("#38BDF8"))
            overlay_badge.setZValue(3)
            overlay_badge.hide()
            self.scene_data.addItem(overlay_badge)
            self.stream_overlay_badges[stream.object_id] = overlay_badge
            marker = QGraphicsEllipseItem(-3.5, -3.5, 7, 7)
            marker.setBrush(QColor("#F8FAFC"))
            marker.setPen(QPen(QColor("#14212A"), 1))
            marker.setZValue(4)
            marker.hide()
            self.scene_data.addItem(marker)
            self.flow_markers[stream.object_id] = marker
        self.update_routes()
        self.apply_stream_styles()
        self.apply_overlays()
        self.setSceneRect(self.scene_data.itemsBoundingRect().adjusted(-500, -500, 500, 500))
        if fresh:
            self.resetTransform()
            self.scale(document.viewport_scale, document.viewport_scale)
            self.centerOn(document.viewport_centre.x, document.viewport_centre.y)
        self.loading = False

    def update_routes(self) -> None:
        """Construct presentation-only doglegs; vertical crossings use the chosen convention."""
        if self.document is None:
            return
        objects = {o.object_id: o for o in self.document.objects}
        self.routes = {}
        for stream in self.document.draft.connections:
            source, target = self.nodes.get(stream.source_id), self.nodes.get(stream.target_id)
            if source is None or target is None:
                continue
            a = source.ports.get(stream.source_port or "out-0")
            b = target.ports.get(stream.target_port or "in-0")
            if a is None or b is None:
                continue
            start, end = a.scenePos(), b.scenePos()
            manual = objects[stream.object_id].route
            if manual:
                points = [
                    start,
                    QPointF(manual[0].x, start.y()),
                    *[QPointF(p.x, p.y) for p in manual],
                    QPointF(manual[-1].x, end.y()),
                    end,
                ]
            else:
                middle = (start.x() + end.x()) / 2
                if end.x() <= start.x() + 30:
                    # A conservative return route keeps the first/last stubs outside symbols.
                    lane = min(source.y(), target.y()) - 45
                    points = [
                        start,
                        start + QPointF(30, 0),
                        QPointF(start.x() + 30, lane),
                        QPointF(end.x() - 30, lane),
                        end - QPointF(30, 0),
                        end,
                    ]
                else:
                    points = [start, QPointF(middle, start.y()), QPointF(middle, end.y()), end]
            self.routes[stream.object_id] = points
        horizontals = [
            (key, a, b)
            for key, pts in self.routes.items()
            for a, b in zip(pts, pts[1:], strict=False)
            if a.y() == b.y() and a.x() != b.x()
        ]
        for key, points in self.routes.items():
            path = QPainterPath(points[0])
            for a, b in zip(points, points[1:], strict=False):
                crossings = []
                if a.x() == b.x() and a.y() != b.y():
                    crossings = sorted(
                        {
                            x.y()
                            for other, x, y in horizontals
                            if other != key
                            and min(x.x(), y.x()) < a.x() < max(x.x(), y.x())
                            and min(a.y(), b.y()) + 7 < x.y() < max(a.y(), b.y()) - 7
                        },
                        reverse=b.y() < a.y(),
                    )
                sign = 1 if b.y() > a.y() else -1
                for crossing in crossings:
                    path.lineTo(a.x(), crossing - sign * 5)
                    if self.document.settings.crossing == "bridge":
                        path.cubicTo(
                            a.x() + 8,
                            crossing - sign * 5,
                            a.x() + 8,
                            crossing + sign * 5,
                            a.x(),
                            crossing + sign * 5,
                        )
                    else:
                        path.moveTo(a.x(), crossing + sign * 5)
                path.lineTo(b)
            end = points[-1]
            path.moveTo(end - QPointF(8, 4))
            path.lineTo(end)
            path.lineTo(end - QPointF(8, -4))
            self.streams[key].setPath(path)
            self.stream_halos[key].setPath(path)
            self.stream_labels[key].setPos(points[1] + QPointF(4, -22))
            self.stream_status_icons[key].setPos(points[1] + QPointF(4, -40))
            if key in self.stream_overlay_badges:
                self.stream_overlay_badges[key].setPos(points[1] + QPointF(4, 6))

    def set_overlays(self, overlays: c.OverlaysDto | None) -> None:
        """Set or clear the active canvas result overlays."""
        self.overlays = overlays
        self.apply_overlays()

    def toggle_overlays(self, visible: bool | None = None) -> bool:
        """Toggle or explicitly set visibility of canvas result overlays."""
        if visible is None:
            self.show_overlays = not self.show_overlays
        else:
            self.show_overlays = visible
        self.apply_overlays()
        return self.show_overlays

    def apply_overlays(self) -> None:
        """Apply current overlays to stream and equipment badges."""
        if not self.show_overlays or self.overlays is None:
            for badge in self.stream_overlay_badges.values():
                badge.setText("")
                badge.hide()
            for badge in self.equipment_overlay_badges.values():
                badge.setText("")
                badge.hide()
            return

        stale_prefix = "Stale · " if self.overlays.selection.is_stale else ""
        stream_map = {ov.stream_id.removeprefix("connection:"): ov for ov in self.overlays.streams}
        for conn_id, badge in self.stream_overlay_badges.items():
            raw_id = conn_id.removeprefix("connection:")
            ov = stream_map.get(raw_id) or stream_map.get(conn_id)
            if ov is not None:
                summary = []
                if ov.temperature_k is not None:
                    summary.append(f"{ov.temperature_k:.1f} K")
                if ov.mass_flow_kg_s is not None:
                    summary.append(f"{ov.mass_flow_kg_s:.2f} kg/s")
                badge.setText(stale_prefix + (" · ".join(summary) if summary else "No quantities"))
                t_str = f"{ov.temperature_k:.2f} K" if ov.temperature_k is not None else "-"
                p_str = f"{ov.pressure_pa:.1f} Pa" if ov.pressure_pa is not None else "-"
                m_str = f"{ov.mass_flow_kg_s:.4f} kg/s" if ov.mass_flow_kg_s is not None else "-"
                badge.setToolTip(f"{ov.tag}\nT = {t_str}\nP = {p_str}\nm = {m_str}")
                badge.show()
            else:
                badge.setText("")
                badge.hide()

        equip_map = {ov.unit_id.removeprefix("unit:"): ov for ov in self.overlays.equipment}
        for node_id, badge in self.equipment_overlay_badges.items():
            raw_id = node_id.removeprefix("unit:")
            ov = equip_map.get(raw_id) or equip_map.get(node_id)
            if ov is not None:
                duty_str = f"Q: {ov.duty_w:.2f} W" if ov.duty_w is not None else f"{ov.closure}"
                badge.setText(f"{stale_prefix}{duty_str} ({ov.closure})")
                badge.setToolTip(
                    f"Unit: {ov.unit_id}\n"
                    f"Duty: {f'{ov.duty_w:.2f} W' if ov.duty_w is not None else '-'}\n"
                    f"Closure: {ov.closure}\n"
                    f"Convergence: {ov.convergence}\n"
                    f"Physical: {ov.physical_validity}\n"
                    f"Correlation: {ov.correlation_validity}"
                )
                badge.show()
            else:
                badge.setText("")
                badge.hide()

    def set_visualization_frame(self, frame: c.FlowVisualizationFrame | None) -> None:
        """Accept only attributable visualization data; absent data stays static."""

        if frame is not None and self.document is not None:
            known = {stream.object_id for stream in self.document.draft.connections}
            if not {stream.stream_id for stream in frame.streams} <= known:
                raise ValueError("visualization frame references a stream outside this document")
        self.visualization_frame = frame
        self.animation_phase = 0.0
        self.apply_stream_styles()

    def apply_stream_styles(self) -> None:
        """Apply documented base, group, result, diagnostic, selection and motion order."""

        if self.document is None:
            return
        preferences = self.document.layer_preferences
        groups = {group.group_id: group for group in self.document.visual_groups}
        active = groups.get(preferences.active_visual_group_id or "")
        memberships: dict[str, list[c.VisualStreamGroup]] = {}
        for group in self.document.visual_groups:
            for identifier in group.member_stream_ids:
                memberships.setdefault(identifier, []).append(group)
        values = (
            {item.stream_id: item for item in self.visualization_frame.streams}
            if self.visualization_frame
            else {}
        )
        maximum = max(
            (abs(item.signed_flow) for item in values.values() if item.signed_flow is not None),
            default=0.0,
        )
        pen_styles = {
            "solid": Qt.PenStyle.SolidLine,
            "dash": Qt.PenStyle.DashLine,
            "dot": Qt.PenStyle.DotLine,
        }
        status_symbols = {
            "INVALID": "⛔ Invalid",
            "FAILED": "× Failed",
            "EXTRAPOLATED": "△ Extrapolated",
            "UNCONVERGED": "↻ Unconverged",
            "STALE": "⌛ Stale",
            "UNAVAILABLE": "? Unavailable",
        }
        for identifier, line in self.streams.items():
            member_groups = memberships.get(identifier, [])
            visible = not member_groups or any(group.visible for group in member_groups)
            line.setVisible(visible)
            self.stream_labels[identifier].setVisible(visible and preferences.show_labels)
            self.stream_halos[identifier].setVisible(
                visible and active is not None and identifier in active.member_stream_ids
            )
            marker = self.flow_markers[identifier]
            marker.setVisible(False)
            status_icon = self.stream_status_icons[identifier]
            status_icon.hide()
            colour = QColor(preferences.base_stream_colour)
            width = preferences.line_width
            value = values.get(identifier)
            if value and preferences.active_result_layer == "mass-flow" and maximum:
                ratio = min(1.0, abs(value.signed_flow or 0.0) / maximum)
                colour = QColor.fromHsvF(0.60 - 0.60 * ratio, 0.72, 0.94)
            style = pen_styles[preferences.line_style]
            tooltip_status = "Not run"
            if value:
                tooltip_status = value.status
                status_icon.setText(status_symbols.get(value.status, ""))
                status_icon.setToolTip(f"Stream status: {value.status}")
                status_icon.setVisible(visible and value.status != "VALID")
                if value.status in {"INVALID", "FAILED"}:
                    style = Qt.PenStyle.DashDotLine
                elif value.status in {"EXTRAPOLATED", "UNCONVERGED", "STALE"}:
                    style = Qt.PenStyle.DashLine
            line.setPen(QPen(colour, width, style))
            self.stream_labels[identifier].setBrush(colour)
            if active and identifier in active.member_stream_ids:
                self.stream_halos[identifier].setPen(
                    QPen(QColor(active.highlight_colour), width + 7, Qt.PenStyle.SolidLine)
                )
            line.setToolTip(
                f"{self.stream_labels[identifier].text()} · Material stream · {tooltip_status}"
            )
        motion_allowed = bool(
            self.visualization_frame
            and preferences.animation_fps
            and not preferences.reduced_motion
            and not (preferences.follow_system_reduced_motion and system_reduced_motion())
        )
        if motion_allowed:
            self.animation_timer.start(round(1000 / preferences.animation_fps))
            self.advance_animation()
        else:
            self.animation_timer.stop()
        if self.visualization_frame and maximum:
            self.legend_changed.emit(
                f"Relative flow animation · scene maximum {maximum:g} "
                f"{next(iter(values.values())).unit} · source "
                f"{self.visualization_frame.source_artifact_id}"
            )
        else:
            self.legend_changed.emit("Static direction arrows · no run artifact selected")

    def advance_animation(self) -> None:
        """Move one marker per finite nonzero stream using scene-normalized relative speed."""

        if self.document is None or self.visualization_frame is None:
            return
        values = {item.stream_id: item for item in self.visualization_frame.streams}
        finite = [abs(item.signed_flow) for item in values.values() if item.signed_flow is not None]
        maximum = max(finite, default=0.0)
        self.animation_phase = (
            self.animation_phase + 0.018 * self.document.layer_preferences.animation_speed_scale
        ) % 1.0
        for identifier, marker in self.flow_markers.items():
            value = values.get(identifier)
            path = self.streams[identifier].path()
            display = bool(
                value
                and value.signed_flow is not None
                and value.status not in {"UNAVAILABLE", "FAILED"}
                and not path.isEmpty()
                and self.streams[identifier].isVisible()
            )
            marker.setVisible(display)
            if not display or value is None or value.signed_flow is None:
                continue
            if value.signed_flow == 0:
                marker.setPos(path.pointAtPercent(0.5))
                continue
            if not maximum:
                continue
            normalized = abs(value.signed_flow) / maximum
            phase = (self.animation_phase * max(0.15, normalized)) % 1.0
            if value.signed_flow < 0:
                phase = 1.0 - phase
            marker.setPos(path.pointAtPercent(phase))

    def _port_at(self, point: QPointF) -> tuple[str, str, str] | None:
        radius = (
            self.document.settings.snap_radius
            if self.document and self.document.settings.snap_ports
            else 5
        )
        for node in self.nodes.values():
            for port in node.ports.values():
                distance = self.mapFromScene(port.scenePos()).toPointF() - point
                if abs(distance.x()) <= radius and abs(distance.y()) <= radius:
                    return port.data(0)
        return None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Begin an explicit port/stream gesture, pan, or normal selection."""
        if event.button() == Qt.MouseButton.MiddleButton:
            self.pan_origin = event.position()
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self.gesture = self._port_at(event.position())
            item = self.itemAt(event.position().toPoint())
            if self.gesture:
                event.accept()
                return
            if item and item.data(1):
                if event.modifiers() & Qt.KeyboardModifier.AltModifier:
                    self.route_drag = str(item.data(1))
                    event.accept()
                    return
                self.gesture = (str(item.data(1)), "", "stream")
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.pan_origin is not None:
            delta = event.position() - self.pan_origin
            self.pan_origin = event.position()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(delta.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(delta.y()))
            event.accept()
            return
        if self.gesture and self.gesture[2] != "stream":
            event.accept()
            return
        super().mouseMoveEvent(event)
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.update_routes()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self.pan_origin is not None:
            self.pan_origin = None
            event.accept()
            return
        if self.route_drag:
            identifier, self.route_drag = self.route_drag, None
            points = self.routes.get(identifier, [])
            if points:
                x = self.mapToScene(event.position().toPoint()).x()
                self.edit_requested.emit(
                    c.RouteStreamEdit(
                        identifier,
                        (c.CanvasPointDto(x, points[0].y()), c.CanvasPointDto(x, points[-1].y())),
                    )
                )
            event.accept()
            return
        if self.gesture:
            gesture, self.gesture = self.gesture, None
            target = self._port_at(event.position())
            if target and target[2] == "input":
                if gesture[2] == "output":
                    self.edit_requested.emit(
                        c.ConnectPortsEdit(gesture[0], gesture[1], target[0], target[1])
                    )
                elif gesture[2] == "stream":
                    points = self.routes.get(gesture[0], [])
                    position = points[len(points) // 2] if points else QPointF()
                    self.edit_requested.emit(
                        c.SplitStreamEdit(
                            gesture[0],
                            c.CanvasPointDto(position.x(), position.y()),
                            target[0],
                            target[1],
                        )
                    )
                event.accept()
                return
        super().mouseReleaseEvent(event)
        if self.document:
            positions = []
            objects = {o.object_id: o for o in self.document.objects}
            for identifier, node in self.nodes.items():
                old = objects[identifier].position
                if (node.x(), node.y()) == (old.x, old.y):
                    continue
                x, y = node.x(), node.y()
                settings = self.document.settings
                tolerance = settings.snap_radius / self.transform().m11()
                if settings.snap_grid:
                    gx, gy = (
                        round(x / settings.grid_spacing) * settings.grid_spacing,
                        round(y / settings.grid_spacing) * settings.grid_spacing,
                    )
                    if abs(x - gx) <= tolerance:
                        x = gx
                    if abs(y - gy) <= tolerance:
                        y = gy
                if settings.snap_alignment:
                    for other in self.nodes.values():
                        if other is not node:
                            if abs(x - other.x()) <= tolerance:
                                x = other.x()
                            if abs(y - other.y()) <= tolerance:
                                y = other.y()
                positions.append((identifier, c.CanvasPointDto(x, y)))
            if positions:
                self.edit_requested.emit(c.MoveObjectsEdit(tuple(positions)))

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Zoom bounded to the versioned document's supported presentation range."""
        # Trackpads and accessibility tools emit wheel phase/horizontal events
        # with no vertical angle. They must not change scale (native witness defect).
        if event.angleDelta().y() == 0:
            event.ignore()
            return
        current = self.transform().m11()
        target = max(0.1, min(4.0, current * (1.15 if event.angleDelta().y() > 0 else 1 / 1.15)))
        self.scale(target / current, target / current)
        event.accept()

    def _snapped_scene_pos(self, view_point: QPoint) -> QPointF:
        scene_pos = self.mapToScene(view_point)
        x, y = scene_pos.x(), scene_pos.y()
        if self.document and self.document.settings.snap_grid:
            grid = self.document.settings.grid_spacing
            x = round(x / grid) * grid
            y = round(y / grid) * grid
        return QPointF(x, y)

    def _ensure_placement_preview(self, model_id: str) -> None:
        if self.placement_preview is None:
            self.placement_preview = QGraphicsRectItem(0, 0, 90, 60)
            self.placement_preview.setPen(QPen(QColor("#82D7CC"), 2, Qt.PenStyle.DashLine))
            self.placement_preview.setBrush(QColor(130, 215, 204, 75))
            self.placement_preview.setZValue(10)
            self.scene_data.addItem(self.placement_preview)

    def _update_placement_preview(self, view_point: QPoint) -> None:
        if self.placement_preview is not None:
            pos = self._snapped_scene_pos(view_point)
            self.placement_preview.setPos(pos)

    def _remove_placement_preview(self) -> None:
        if self.placement_preview is not None:
            self.scene_data.removeItem(self.placement_preview)
            self.placement_preview = None

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if not self.document or not event.mimeData().hasFormat(
            "application/vnd.bh.equipment-model+json"
        ):
            event.ignore()
            return
        raw_bytes = bytes(event.mimeData().data("application/vnd.bh.equipment-model+json").data())
        if len(raw_bytes) > 65536:
            event.ignore()
            return
        try:
            payload = json.loads(raw_bytes.decode("utf-8"))
        except Exception:
            event.ignore()
            return
        if not isinstance(payload, dict):
            event.ignore()
            return
        model_id = payload.get("model_id")
        if not model_id or not any(m.model_id == model_id for m in self.catalogue.models):
            event.ignore()
            return
        event.acceptProposedAction()
        self._ensure_placement_preview(model_id)
        self._update_placement_preview(event.position().toPoint())

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if self.placement_preview is not None:
            event.acceptProposedAction()
            self._update_placement_preview(event.position().toPoint())
        else:
            event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        self._remove_placement_preview()
        event.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        if self.placement_preview is None:
            event.ignore()
            return
        raw_bytes = bytes(event.mimeData().data("application/vnd.bh.equipment-model+json").data())
        self._remove_placement_preview()
        try:
            payload = json.loads(raw_bytes.decode("utf-8"))
            model_id = payload["model_id"]
        except Exception:
            event.ignore()
            return
        if not any(m.model_id == model_id for m in self.catalogue.models):
            event.ignore()
            return
        pos = self._snapped_scene_pos(event.position().toPoint())
        self.edit_requested.emit(c.AddEquipmentEdit(model_id, c.CanvasPointDto(pos.x(), pos.y())))
        event.acceptProposedAction()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self._remove_placement_preview()
        super().keyPressEvent(event)
