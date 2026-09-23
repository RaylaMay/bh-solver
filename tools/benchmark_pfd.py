"""Native Qt renderer probe for DW3; synthetic UI workload, never solver evidence.

Run each renderer/count in its own process on the actual macOS platform plugin.
Paint duration measures CPU-side paintEvent wall time, not GPU completion.
Event-to-paint measures a synthetic Qt event through paint completion, not physical
input-to-photon latency. Scene counts and raw samples accompany every report.
"""

from __future__ import annotations

import argparse
import json
import platform
import resource
import statistics
import time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, qVersion
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QApplication, QGraphicsScene, QGraphicsView


class ProbeView(QGraphicsView):
    """Measure identical explicit update workloads with each viewport backend."""

    def __init__(self, renderer: str, units: int, output: Path) -> None:
        super().__init__()
        self.output = output
        self.renderer = renderer
        self.units = units
        self.pending = 0.0
        self.samples: dict[str, list[dict[str, float]]] = {}
        self.workloads = ("pan", "zoom", "selection", "drag", "labels")
        self.index = -20  # Warm-up frames excluded from samples.
        self.cpu_start = time.process_time()
        self.started = time.perf_counter()
        self.scene_data = QGraphicsScene(self)
        self.setScene(self.scene_data)
        self.setWindowTitle(f"BH renderer probe — {renderer} — {units} equipment")
        self.resize(1280, 800)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setBackgroundBrush(QColor("#121B22"))
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate)
        if renderer.startswith("opengl"):
            from PySide6.QtOpenGLWidgets import QOpenGLWidget

            self.setViewport(QOpenGLWidget())
            if renderer == "opengl-full":
                self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.nodes = []
        self.labels = []
        self.routes = []
        for index in range(units):
            x, y = (index % 10) * 180, (index // 10) * 150
            node = self.scene_data.addEllipse(
                0, 0, 84, 56, QPen(QColor("#82D7CC"), 2), QBrush(QColor("#1A2630"))
            )
            node.setPos(x, y)
            self.nodes.append(node)
            for px in (-8, 84):
                port = self.scene_data.addEllipse(
                    0, 0, 8, 8, QPen(Qt.PenStyle.NoPen), QBrush(QColor("#82D7CC"))
                )
                port.setParentItem(node)
                port.setPos(px, 24)
            tag = self.scene_data.addSimpleText(f"HX-{index + 1:03}")
            tag.setBrush(QColor("#EDF3F5"))
            tag.setParentItem(node)
            tag.setPos(0, 60)
            self.labels.append(tag)
            detail = self.scene_data.addSimpleText("Input required · Not run")
            detail.setBrush(QColor("#B0C0CB"))
            detail.setParentItem(node)
            detail.setPos(0, 80)
            if index and index % 10:
                path = QPainterPath()
                path.moveTo(x - 88, y + 28)
                path.lineTo(x - 48, y + 28)
                path.lineTo(x - 48, y + 12)
                path.lineTo(x, y + 12)
                self.routes.append(self.scene_data.addPath(path, QPen(QColor("#A4C7CE"), 2)))
                stream_tag = self.scene_data.addSimpleText(f"S-{index:03}")
                stream_tag.setBrush(QColor("#B0C0CB"))
                stream_tag.setPos(x - 75, y - 12)
        self.setSceneRect(self.scene_data.itemsBoundingRect().adjusted(-50, -50, 50, 50))
        self.timer = QTimer(self)
        self.timer.setInterval(20)
        self.timer.timeout.connect(self.step)

    def step(self) -> None:
        """Generate one bounded interaction then request a visible paint."""
        if self.pending:
            return  # No sample is replaced or silently dropped while awaiting paint.
        if self.index >= 400:
            self.finish()
            return
        self.pending = time.perf_counter()
        workload = self.workloads[max(self.index, 0) // 80]
        node = self.nodes[max(self.index, 0) % self.units]
        if workload == "pan":
            self.horizontalScrollBar().setValue((self.index % 40) * 8)
        elif workload == "zoom":
            self.resetTransform()
            self.scale(0.65 + (self.index % 30) / 50, 0.65 + (self.index % 30) / 50)
        elif workload == "selection":
            for candidate in self.nodes:
                candidate.setPen(QPen(QColor("#82D7CC"), 2))
            node.setPen(QPen(QColor("#FFFF00"), 4))
            assert self.scene_data.itemAt(node.sceneBoundingRect().center(), self.transform())
        elif workload == "drag":
            node.setPos(node.x() + (2 if self.index % 2 else -2), node.y())
        else:
            for index, label in enumerate(self.labels):
                label.setText(f"HX-{index + 1:03} · {self.index % 2}")
        self.viewport().update()

    def paintEvent(self, event) -> None:  # Qt supplies QPaintEvent.
        begin = time.perf_counter()
        super().paintEvent(event)
        ended = time.perf_counter()
        if self.pending:
            if self.index >= 0:
                workload = self.workloads[self.index // 80]
                self.samples.setdefault(workload, []).append(
                    {
                        "paint_ms": (ended - begin) * 1000,
                        "event_to_paint_ms": (ended - self.pending) * 1000,
                    }
                )
            self.index += 1
            self.pending = 0.0

    def finish(self) -> None:
        """Write exact samples and scoped measurements; absence is explicit."""
        self.timer.stop()
        screen = self.screen()
        report = {
            "schema": "bh-renderer-probe-v1",
            "renderer": self.renderer,
            "os": platform.mac_ver()[0],
            "architecture": platform.machine(),
            "qt": qVersion(),
            "platform_plugin": QApplication.platformName(),
            "viewport_logical_pixels": [self.viewport().width(), self.viewport().height()],
            "device_pixel_ratio": self.devicePixelRatioF(),
            "screen_refresh_hz": screen.refreshRate(),
            "equipment": self.units,
            "ports": self.units * 2,
            "streams": len(self.routes),
            "segments": len(self.routes) * 3,
            "labels": self.units * 2 + len(self.routes),
            "status_labels": self.units,
            "items": len(self.scene_data.items()),
            "raw_samples": self.samples,
            "cpu_seconds": time.process_time() - self.cpu_start,
            "elapsed_seconds": time.perf_counter() - self.started,
            "peak_resident_bytes_macos": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "gpu_load": None,
            "physical_input_to_photon_ms": None,
            "limitations": (
                "Synthetic events and CPU-side paint timings; no GPU load, compositor "
                "presentation time or physical dropped-frame measurement. "
                "Geometry probe; final editor needs a separate check."
            ),
        }
        if self.renderer.startswith("opengl"):
            report["opengl_context_valid"] = self.viewport().isValid()
        report["summary"] = {}
        for workload, samples in self.samples.items():
            report["summary"][workload] = {}
            for metric in ("paint_ms", "event_to_paint_ms"):
                values = sorted(sample[metric] for sample in samples)
                report["summary"][workload][metric] = {
                    "median": statistics.median(values),
                    "p95": values[int((len(values) - 1) * 0.95)],
                    "p99": values[int((len(values) - 1) * 0.99)],
                    "maximum": max(values),
                }
        self.output.parent.mkdir(parents=True, exist_ok=True)
        # QWidget.grab does not reliably capture a composited OpenGL viewport.
        # Read its framebuffer explicitly; keep the distinction in the report.
        if self.renderer.startswith("opengl"):
            capture = self.viewport().grabFramebuffer()
            report["capture_method"] = "QOpenGLWidget.grabFramebuffer"
        else:
            capture = self.grab()
            report["capture_method"] = "QWidget.grab"
        capture.save(str(self.output.with_suffix(".png")))
        self.output.write_text(json.dumps(report, indent=2) + "\n")
        print(f"Recorded {self.renderer}: {self.units} equipment, 400 samples", flush=True)
        QApplication.quit()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--renderer", choices=("raster", "opengl-full", "opengl-bounding"), required=True
    )
    parser.add_argument("--units", type=int, choices=(10, 50, 100), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--editor", action="store_true", help="Measure the production canvas and commands"
    )
    parser.add_argument(
        "--hold", action="store_true", help="Keep the editor probe visible for inspection"
    )
    args = parser.parse_args()
    if args.editor:
        from benchmark_editor import run_editor

        run_editor(args.renderer, args.units, args.output, args.hold)
        return
    app = QApplication([])
    view = ProbeView(args.renderer, args.units, args.output)
    view.show()
    QTimer.singleShot(300, view.timer.start)
    QTimer.singleShot(30000, lambda: app.exit(2))
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
