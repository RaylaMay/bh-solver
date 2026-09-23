"""Native DW3.2 timing includes durable editing, the inspector and the project browser."""

from __future__ import annotations

import argparse
import json
import math
import platform
import tempfile
import time
from pathlib import Path

from pfd_scene import reference_scene
from PySide6.QtCore import Qt, QTimer, qVersion
from PySide6.QtGui import QTransform
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from bh_sim.adapters.desktop_preview import create_preview_gateway
from bh_sim.boundary import contracts as c
from bh_sim.uix.pfd_canvas import PfdCanvas
from bh_sim.uix.workspace import WorkspaceSettings
from bh_sim.uix.workstation_editor import WorkstationEditor


class ProbeCanvas(PfdCanvas):
    """Measure CPU paint completion, explicitly excluding compositor/input-device latency."""

    def __init__(self) -> None:
        super().__init__()
        self.pending = 0.0
        self.mode = "warmup"
        self.samples: dict[str, list[dict[str, float]]] = {}

    def paintEvent(self, event) -> None:
        start = time.perf_counter()
        super().paintEvent(event)
        end = time.perf_counter()
        if self.pending:
            self.samples.setdefault(self.mode, []).append(
                {
                    "paint_ms": (end - start) * 1000,
                    "event_to_paint_ms": (end - self.pending) * 1000,
                }
            )
            self.pending = 0.0


class ProbeWindow(WorkstationEditor):
    def create_canvas(self) -> ProbeCanvas:
        return ProbeCanvas()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    app = QApplication([])
    app.setStyle("Fusion")
    root = Path(tempfile.mkdtemp(prefix="bh-dw32-benchmark-"))
    window = ProbeWindow(create_preview_gateway(root), WorkspaceSettings(root / "ui.ini"))
    window.resize(1440, 900)
    outcome = window.execute("history.start", c.PfdDocumentParameters(reference_scene(50)))
    assert isinstance(outcome.data, c.HistoryState)
    window._adopt(outcome.data, new=True)
    window.show()
    window.fit_flowsheet()
    canvas = window.canvas
    assert isinstance(canvas, ProbeCanvas)
    modes = ("pan", "zoom", "selection", "drag", "labels")
    index = -5
    cpu_start, started = time.process_time(), time.perf_counter()
    timer = QTimer()
    timer.setInterval(30)
    correctness = {
        "selection_identity": True,
        "durable_drag": True,
        "durable_labels": True,
        "orthogonal_routes": True,
        "port_endpoints": True,
    }

    def step() -> None:
        nonlocal index
        if canvas.pending:
            return
        if index >= 150:
            finish()
            return
        mode = modes[max(index, 0) // 30]
        canvas.mode = mode if index >= 0 else "warmup"
        canvas.pending = time.perf_counter()
        assert window.document is not None
        identifier = window.document.draft.equipment[max(index, 0) % 50].object_id
        if mode == "pan":
            canvas.horizontalScrollBar().setValue(index % 10 * 8)
        elif mode == "zoom":
            scale = 0.55 + index % 10 * 0.025
            canvas.setTransform(QTransform.fromScale(scale, scale))
        elif mode == "selection":
            canvas.select_ids((identifier,))
            correctness["selection_identity"] &= canvas.selected_ids() == (identifier,)
        elif mode == "drag":
            item = canvas.nodes[identifier]
            canvas.centerOn(item)
            before = item.pos()
            start = canvas.mapFromScene(item.sceneBoundingRect().center())
            end = start + canvas.mapFromScene(40, 40) - canvas.mapFromScene(0, 0)
            QTest.mousePress(canvas.viewport(), Qt.MouseButton.LeftButton, pos=start)
            QTest.mouseMove(canvas.viewport(), end)
            QTest.mouseRelease(canvas.viewport(), Qt.MouseButton.LeftButton, pos=end)
            assert window.session
            actual = next(
                o.position
                for o in window.session.state.document.objects
                if o.object_id == identifier
            )
            correctness["durable_drag"] &= (actual.x, actual.y) != (before.x(), before.y())
        else:
            tag = f"U-Edited-{index}"
            window.run_command(f"rename {identifier} {tag}")
            assert window.session
            correctness["durable_labels"] &= any(
                o.tag == tag for o in window.session.state.document.objects
            )
        canvas.viewport().update()
        index += 1

    def finish() -> None:
        timer.stop()
        assert window.document
        for stream in window.document.draft.connections:
            route = canvas.routes[stream.object_id]
            correctness["orthogonal_routes"] &= all(
                a.x() == b.x() or a.y() == b.y() for a, b in zip(route, route[1:], strict=False)
            )
            correctness["port_endpoints"] &= (
                route[0]
                == canvas.nodes[stream.source_id].ports[stream.source_port or "out-0"].scenePos()
            )
            correctness["port_endpoints"] &= (
                route[-1]
                == canvas.nodes[stream.target_id].ports[stream.target_port or "in-0"].scenePos()
            )
        summary = {}
        for mode in modes:
            summary[mode] = {}
            for metric in ("paint_ms", "event_to_paint_ms"):
                values = sorted(row[metric] for row in canvas.samples[mode])
                summary[mode][metric] = {
                    "p95": values[math.ceil(len(values) * 0.95) - 1],
                    "p99": values[math.ceil(len(values) * 0.99) - 1],
                }
        accepted = all(
            v["paint_ms"]["p95"] <= 33 and v["event_to_paint_ms"]["p95"] <= 50
            for v in summary.values()
        ) and all(correctness.values())
        report = {
            "schema": "bh-workstation-benchmark-v1",
            "qt": qVersion(),
            "platform_plugin": QApplication.platformName(),
            "architecture": platform.machine(),
            "os": platform.mac_ver()[0],
            "equipment": 50,
            "streams": 45,
            "cpu_seconds": time.process_time() - cpu_start,
            "elapsed_seconds": time.perf_counter() - started,
            "viewport_pixels": [canvas.viewport().width(), canvas.viewport().height()],
            "samples_per_workload": 30,
            "percentile_method": "nearest-rank",
            "summary": summary,
            "raw_samples": canvas.samples,
            "correctness": correctness,
            "accepted": accepted,
            "limitations": (
                "Synthetic Qt event to CPU paint completion. Includes history commit and "
                "native window refresh for drag/label edits; excludes compositor, physical "
                "input and network collaboration."
            ),
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
        canvas.grab().save(str(args.output.with_suffix(".png")))
        window.close()
        print(
            json.dumps({"accepted": accepted, "summary": summary, "correctness": correctness}),
            flush=True,
        )
        app.quit()

    timer.timeout.connect(step)
    QTimer.singleShot(500, timer.start)
    QTimer.singleShot(60000, lambda: app.exit(2))
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
