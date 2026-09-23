"""Measure the production PFD canvas and command round trip on the native display."""

from __future__ import annotations

import json
import math
import platform
import resource
import statistics
import tempfile
import time
from pathlib import Path
from uuid import uuid4

from pfd_scene import reference_scene
from PySide6.QtCore import QTimer, qVersion
from PySide6.QtWidgets import QApplication, QGraphicsSimpleTextItem

from bh_sim.adapters.desktop_preview import create_preview_gateway
from bh_sim.adapters.pfd import reference_catalogue
from bh_sim.boundary import contracts as c
from bh_sim.uix.pfd_canvas import PfdCanvas


class EditorProbe(PfdCanvas):
    """Synthetic event-to-paint samples include actual application dispatch for drag/labels."""

    def __init__(self, renderer: str, count: int, output: Path, hold: bool) -> None:
        super().__init__()
        self.renderer, self.output, self.hold = renderer, output, hold
        self.count = count
        self.gateway = create_preview_gateway(Path(tempfile.mkdtemp(prefix="bh-editor-probe-")))
        self.set_document(reference_scene(count), reference_catalogue())
        self.resize(1280, 800)
        self.setWindowTitle(f"BH native editor benchmark · {renderer} · {count}")
        if renderer.startswith("opengl"):
            from PySide6.QtOpenGLWidgets import QOpenGLWidget

            self.setViewport(QOpenGLWidget())
            if renderer == "opengl-full":
                self.setViewportUpdateMode(self.ViewportUpdateMode.FullViewportUpdate)
        self.workloads = ("pan", "zoom", "selection", "drag", "labels")
        self.index = -20
        self.pending = 0.0
        self.samples: dict[str, list[dict[str, float]]] = {}
        self.cpu_start, self.start = time.process_time(), time.perf_counter()
        self.timer = QTimer(self)
        self.timer.setInterval(20)
        self.timer.timeout.connect(self.step)

    def step(self) -> None:
        if self.pending:
            return
        if self.index >= 400:
            self.finish()
            return
        self.pending = time.perf_counter()
        mode = self.workloads[max(self.index, 0) // 80]
        assert self.document is not None
        identifier = self.document.draft.equipment[max(self.index, 0) % self.count].object_id
        node = self.nodes[identifier]
        if mode == "pan":
            self.horizontalScrollBar().setValue(self.index % 40 * 8)
        elif mode == "zoom":
            self.resetTransform()
            self.scale(0.65 + self.index % 30 / 50, 0.65 + self.index % 30 / 50)
        elif mode == "selection":
            self.scene_data.clearSelection()
            node.setSelected(True)
            assert identifier in self.selected_ids()
        else:
            edit = (
                c.MoveObjectsEdit(
                    (
                        (
                            identifier,
                            c.CanvasPointDto(node.x() + (2 if self.index % 2 else -2), node.y()),
                        ),
                    )
                )
                if mode == "drag"
                else c.RenameObjectEdit(identifier, f"U-{self.index:03}")
            )
            outcome = self.gateway.dispatch(
                c.CommandRequest(
                    "pfd.edit", uuid4().hex, "benchmark", c.PfdEditParameters(self.document, edit)
                )
            )
            assert outcome.disposition == "COMPLETED" and isinstance(outcome.data, c.PfdDocumentDto)
            self.set_document(outcome.data, reference_catalogue())
        self.viewport().update()

    def paintEvent(self, event) -> None:
        start = time.perf_counter()
        super().paintEvent(event)
        ended = time.perf_counter()
        if self.pending:
            if self.index >= 0:
                self.samples.setdefault(self.workloads[self.index // 80], []).append(
                    {
                        "paint_ms": (ended - start) * 1000,
                        "event_to_paint_ms": (ended - self.pending) * 1000,
                    }
                )
            self.index += 1
            self.pending = 0.0

    def finish(self) -> None:
        """Record raw timing, correctness assertions, environment and capture limitations."""
        self.timer.stop()
        assert self.document is not None
        for stream in self.document.draft.connections:
            route = self.routes[stream.object_id]
            assert (
                route[0]
                == self.nodes[stream.source_id].ports[stream.source_port or "out-0"].scenePos()
            )
            assert (
                route[-1]
                == self.nodes[stream.target_id].ports[stream.target_port or "in-0"].scenePos()
            )
            assert all(
                a.x() == b.x() or a.y() == b.y() for a, b in zip(route, route[1:], strict=False)
            )
        summary = {}
        for workload, samples in self.samples.items():
            summary[workload] = {}
            for metric in ("paint_ms", "event_to_paint_ms"):
                values = sorted(s[metric] for s in samples)
                summary[workload][metric] = {
                    "median": statistics.median(values),
                    "p95": values[math.ceil(len(values) * 0.95) - 1],
                    "p99": values[math.ceil(len(values) * 0.99) - 1],
                    "maximum": max(values),
                }
        report = {
            "schema": "bh-editor-benchmark-v1",
            "renderer": self.renderer,
            "os": platform.mac_ver()[0],
            "architecture": platform.machine(),
            "qt": qVersion(),
            "platform_plugin": QApplication.platformName(),
            "equipment": self.count,
            "streams": len(self.document.draft.connections),
            "ports": sum(len(n.ports) for n in self.nodes.values()),
            "segments": sum(len(p) - 1 for p in self.routes.values()),
            "items": len(self.scene_data.items()),
            "labels": sum(isinstance(i, QGraphicsSimpleTextItem) for i in self.scene_data.items()),
            "viewport_logical_pixels": [self.viewport().width(), self.viewport().height()],
            "device_pixel_ratio": self.devicePixelRatioF(),
            "screen_refresh_hz": self.screen().refreshRate(),
            "cpu_seconds": time.process_time() - self.cpu_start,
            "elapsed_seconds": time.perf_counter() - self.start,
            "peak_resident_bytes_macos": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "raw_samples": self.samples,
            "summary": summary,
            "percentile_method": "nearest-rank",
            "correctness": {
                "orthogonal_routes": True,
                "port_endpoints": True,
                "selection_identity": True,
            },
            "gpu_load": None,
            "physical_input_to_photon_ms": None,
            "limitations": (
                "Synthetic Qt event to CPU paint completion; no compositor/GPU completion claim. "
                "Drag and label samples include command dispatch and scene rebuild. "
                "Native screenshot still requires visual inspection."
            ),
        }
        if self.renderer.startswith("opengl"):
            report["opengl_context_valid"] = self.viewport().isValid()
        # Scene rendering is independent of the viewport capture, useful to separate
        # missing scene content from a composited OpenGL capture failure.
        self.output.parent.mkdir(parents=True, exist_ok=True)
        self.grab().save(str(self.output.with_suffix(".png")))
        self.output.write_text(json.dumps(report, indent=2) + "\n")
        print(f"Recorded production canvas: {self.renderer}, {self.count} equipment", flush=True)
        if not self.hold:
            QApplication.quit()


def run_editor(renderer: str, count: int, output: Path, hold: bool) -> None:
    app = QApplication([])
    view = EditorProbe(renderer, count, output, hold)
    view.show()
    QTimer.singleShot(300, view.timer.start)
    QTimer.singleShot(90000 if hold else 60000, lambda: app.exit(2))
    raise SystemExit(app.exec())
