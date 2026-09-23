"""Measure DW3.1 flow-marker rendering on the 50-equipment reference scene.

The frame values are synthetic presentation fixtures. They are not solver results
and carry no scientific authority. Timing ends at CPU paint completion; compositor
and physical input-to-photon timing remain outside this probe.
"""

from __future__ import annotations

import argparse
import json
import math
import platform
import resource
import statistics
import time
from pathlib import Path

from pfd_scene import reference_scene
from PySide6.QtCore import QTimer, qVersion
from PySide6.QtWidgets import QApplication

from bh_sim.adapters.pfd import reference_catalogue
from bh_sim.boundary import contracts as c
from bh_sim.uix.pfd_canvas import PfdCanvas


def percentile(values: list[float], proportion: float) -> float:
    """Return a nearest-rank percentile for a nonempty bounded sample."""

    return sorted(values)[math.ceil(len(values) * proportion) - 1]


class AnimationProbe(PfdCanvas):
    """Record continuous timer-driven marker paints on the production canvas."""

    def __init__(self, output: Path, frames: int) -> None:
        super().__init__()
        self.output, self.frame_limit = output, frames
        self.samples: list[dict[str, float]] = []
        self.paint_pending = False
        self.last_tick = 0.0
        self.legend_value = ""
        self.legend_changed.connect(self._capture_legend)
        self.cpu_started = time.process_time()
        self.wall_started = time.perf_counter()
        document = reference_scene(50)
        document = c.PfdDocumentDto(
            document.draft,
            document.objects,
            document.settings,
            document.viewport_centre,
            document.viewport_scale,
            document.next_stream_number,
            document.visual_groups,
            document.engineering_subsystems,
            c.PfdLayerPreferences(active_result_layer="mass-flow", animation_fps=30),
        )
        self.set_document(document, reference_catalogue())
        streams = tuple(document.draft.connections)
        values = tuple(
            c.FlowStreamVisualization(
                stream.object_id,
                0.0 if index == 0 else (-1.0 if index == 1 else float(index + 1)),
                "stationary" if index == 0 else "reverse" if index == 1 else "forward",
                "relative-fixture",
                "STALE" if index == 2 else "VALID",
            )
            for index, stream in enumerate(streams)
        )
        self.set_visualization_frame(
            c.FlowVisualizationFrame("benchmark:synthetic", 0.0, values, "dynamic-telemetry")
        )
        self.resize(1280, 800)
        self.setWindowTitle("BH DW3.1 animation benchmark · synthetic values")
        self.probe_timer = QTimer(self)
        self.probe_timer.setInterval(33)
        self.probe_timer.timeout.connect(self.tick)

    def tick(self) -> None:
        if self.paint_pending:
            return
        now = time.perf_counter()
        if len(self.samples) >= self.frame_limit:
            self.finish()
            return
        self.paint_pending = True
        self.last_tick = now
        self.advance_animation()
        self.viewport().update()

    def paintEvent(self, event) -> None:
        started = time.perf_counter()
        super().paintEvent(event)
        ended = time.perf_counter()
        if self.paint_pending:
            previous = self.samples[-1]["paint_completed_at"] if self.samples else self.wall_started
            self.samples.append(
                {
                    "paint_ms": (ended - started) * 1000,
                    "tick_to_paint_ms": (ended - self.last_tick) * 1000,
                    "frame_interval_ms": (ended - previous) * 1000,
                    "paint_completed_at": ended,
                }
            )
            self.paint_pending = False

    def finish(self) -> None:
        self.probe_timer.stop()
        paint = [sample["paint_ms"] for sample in self.samples]
        latency = [sample["tick_to_paint_ms"] for sample in self.samples]
        intervals = [sample["frame_interval_ms"] for sample in self.samples[1:]]
        dropped = sum(interval > 50.0 for interval in intervals)
        assert self.document is not None and self.visualization_frame is not None
        values = {value.stream_id: value for value in self.visualization_frame.streams}
        first_three = tuple(self.document.draft.connections[:3])
        correctness = {
            "source_artifact_visible": "benchmark:synthetic" in self.legend_value,
            "zero_flow_stationary": values[first_three[0].object_id].signed_flow == 0.0,
            "reverse_direction_retained": values[first_three[1].object_id].direction == "reverse",
            "stale_pattern_retained": values[first_three[2].object_id].status == "STALE",
            "markers_bounded_to_paths": all(
                self.streams[key]
                .path()
                .boundingRect()
                .adjusted(-5, -5, 5, 5)
                .contains(marker.pos())
                for key, marker in self.flow_markers.items()
                if marker.isVisible()
            ),
        }
        report = {
            "schema": "bh-animation-benchmark-v1",
            "authority": "synthetic presentation workload; not solver or scientific evidence",
            "os": platform.mac_ver()[0],
            "architecture": platform.machine(),
            "qt": qVersion(),
            "platform_plugin": QApplication.platformName(),
            "equipment": len(self.document.draft.equipment),
            "streams": len(self.document.draft.connections),
            "target_fps": 30,
            "target_p95_paint_ms": 33.0,
            "frames": len(self.samples),
            "paint_ms": {
                "median": statistics.median(paint),
                "p95": percentile(paint, 0.95),
                "p99": percentile(paint, 0.99),
                "maximum": max(paint),
            },
            "tick_to_paint_ms": {
                "median": statistics.median(latency),
                "p95": percentile(latency, 0.95),
                "p99": percentile(latency, 0.99),
                "maximum": max(latency),
            },
            "dropped_frames_over_50ms": dropped,
            "cpu_seconds": time.process_time() - self.cpu_started,
            "elapsed_seconds": time.perf_counter() - self.wall_started,
            "peak_resident_bytes_macos": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "acceptance": percentile(paint, 0.95) <= 33.0 and all(correctness.values()),
            "correctness": correctness,
            "raw_samples": self.samples,
            "limitations": (
                "Timer to CPU paint completion on one macOS/arm64 workstation. "
                "No compositor, GPU-load, energy, or physical input-to-photon claim."
            ),
        }
        self.output.parent.mkdir(parents=True, exist_ok=True)
        self.output.write_text(json.dumps(report, indent=2) + "\n")
        self.grab().save(str(self.output.with_suffix(".png")))
        summary = {
            key: report[key] for key in ("paint_ms", "dropped_frames_over_50ms", "acceptance")
        }
        print(json.dumps(summary, indent=2))
        QApplication.quit()

    def _capture_legend(self, text: str) -> None:
        self.legend_value = text


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frames", type=int, default=300)
    args = parser.parse_args()
    app = QApplication([])
    view = AnimationProbe(args.output, args.frames)
    view.show()
    QTimer.singleShot(500, view.probe_timer.start)
    QTimer.singleShot(30000, lambda: app.exit(2))
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
