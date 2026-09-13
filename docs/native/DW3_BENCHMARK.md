# DW3 renderer measurements and P-02 disposition

Date: 2026-09-13. Status: **INITIAL P-02 TARGETS ACCEPTED; RASTER SELECTED FOR LOCAL EDITOR**.

Rayla May accepted 50 equipment as the reference scene, p95 paint ≤33 ms and p95
synthetic event-to-paint ≤50 ms on this Mac. These are UI targets, independent of
solver speed. Ten equipment is the small scene; 100 is headroom exploration, not
a promised supported size or a hard product cap. No 500-equipment, 4K/144-Hz or
10,000-item claim is made.

## Method and evidence

`tools/benchmark_pfd.py` first compared an identical geometry probe with raster
BoundingRectViewportUpdate, QOpenGLWidget FullViewportUpdate and QOpenGLWidget
BoundingRectViewportUpdate. `--editor` then measured the actual PfdCanvas and
application editing commands. Native runs use macOS 26.4.1 arm64, Qt 6.11.2,
Cocoa on Apple M5 with 16 GiB RAM, a 1280×800 logical viewport and 2× device pixel ratio. The JSON records the
reported screen refresh rate, counts, raw samples, CPU seconds and peak RSS.
No other renderer benchmark process ran concurrently.

Each run excludes 20 warm-up events and records 80 samples each of pan, zoom,
selection, dragging and label changes. Production drag and label events include
the neutral command/codec round trip and scene rebuild. Live routes are recomputed;
endpoint, orthogonality and selection assertions accompany the measurements.
Reference equipment is intentionally incomplete test-fixture content, with input
and unavailable-status details. It contains no calculated overlays.

The 50-equipment production fixture contains 90 ports, 45 streams, 145 text items
and 330 graphics items. The viewport displays a changing subset while panning and
zooming; 50 is the total document count, not a claim that every label is on screen
at once. Expanding details exposes label overlap at this dense spacing. The fixture
is repeatable, not a claim that its synthetic placement is an ideal engineering PFD.

CPU paintEvent duration is not GPU completion. Synthetic Qt event-to-paint is not
physical input-to-photon latency. GPU utilization, compositor presentation, physical
dropped frames, printing/export, VoiceOver and other OS/GPU classes were **not
measured**. CPU seconds/RSS are process measurements, not a system-load survey.
Production percentiles use nearest-rank; the earlier geometry probe used the
floor-index method recorded in its source. Compare the production runs for the
editor decision. Raw data remains available rather than presenting averages alone.

## Production results

Entries below are the worst workload's percentile for each metric, in milliseconds,
not pooled percentiles. Each file contains individual workload median/p95/p99/max.

| Renderer / document | Paint p95 | Paint p99 | Event-to-paint p95 | Event-to-paint p99 |
|---|---:|---:|---:|---:|
| [raster, 10 equipment](evidence/dw3/editor-raster-10-final.json) | 3.83 | 6.09 | 9.67 | 16.58 |
| [raster, 50 equipment](evidence/dw3/editor-raster-50-final.json) | 6.10 | 6.85 | 31.00 | 40.37 |
| [raster, 100 equipment](evidence/dw3/editor-raster-100.json) | 5.34 | 7.52 | 54.49 | 66.50 |
| [opengl-full, 10 equipment](evidence/dw3/editor-opengl-full-10-final.json) | 3.02 | 3.36 | 9.21 | 19.72 |
| [opengl-full, 50 equipment](evidence/dw3/editor-opengl-full-50.json) | 4.11 | 161.38 | 32.44 | 161.47 |
| [opengl-full, 100 equipment](evidence/dw3/editor-opengl-full-100-final.json) | 4.79 | 7.90 | 52.30 | 62.53 |
| [opengl-bounding, 50 equipment](evidence/dw3/editor-opengl-bounding-50-final.json) | 4.42 | 5.16 | 26.62 | 43.84 |
| [opengl-bounding, 100 equipment](evidence/dw3/editor-opengl-bounding-100-final.json) | 4.35 | 4.98 | 56.80 | 71.90 |

The final 50-equipment raster run passes both approved timing targets. At 100,
command/rebuild latency exceeds the 50 ms target in some workloads for every
measured renderer; no 100-equipment responsiveness acceptance is claimed.
The raw JSON also retains earlier runs, so repeat variability is visible.

## Visual result and decision

Raster captures contain the expected symbols, ports, tags, input-required text and
routes. The separate native app walkthrough confirmed readable rendering and
pointer interaction on this Mac. OpenGL reported a valid context and returned CPU
timings, but both QWidget.grab and explicit framebuffer capture produced white
images. The standalone Python probe could not be located by native UI automation
before it timed out. Therefore OpenGL **does not pass visual acceptance** here.
Its lower CPU timings alone do not establish a usable or faster end-user renderer;
the cause may be composition/capture behavior and is unresolved.

Select raster for the initial editor: it is the simplest measured implementation
that passes the reference targets and has inspected visual output. Keep OpenGL as
an unselected experimental benchmark option. No production OpenGL dependency,
Qt Quick or Metal adoption follows from these measurements. Repeat measurements
when realistic routing, overlays or rendering changes materially alter workload.

Qt documents the viewport/update-mode choices in its
[QGraphicsView reference](https://doc.qt.io/qt-6/qgraphicsview.html) and the
[QOpenGLWidget reference](https://doc.qt.io/qt-6/qopenglwidget.html).
These primary sources explain the compared mechanisms; the measurements above
are local evidence, not Qt performance guarantees.

## Reproduce

Run from the checkout with its installed desktop extra and a native display:

```sh
.venv/bin/python tools/benchmark_pfd.py --editor --renderer raster --units 50 --output /tmp/bh-raster-50.json
.venv/bin/python tools/benchmark_pfd.py --editor --renderer opengl-full --units 50 --output /tmp/bh-gl-full-50.json
.venv/bin/python tools/benchmark_pfd.py --editor --renderer opengl-bounding --units 50 --output /tmp/bh-gl-bounding-50.json
```

Use `--units 10` or `100` for the other scenes. Omit `--editor` for the initial
geometry-only probe. Do not run native benchmarks on the CI offscreen plugin and
label them display evidence. `--hold` deliberately keeps the test window alive
for inspection; that attempted run wrote its complete 400-sample report and then
exited 2 at the inspection timeout. Other recorded production runs exited 0.

See [native witness](DW3_NATIVE_VERIFICATION.md), [change record](DW3_CHANGE_RECORD.md)
and [implementation guide](DW3_PFD.md) for behavior and outstanding parity gates.
