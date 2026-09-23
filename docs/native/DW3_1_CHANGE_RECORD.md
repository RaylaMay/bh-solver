# DW3.1 UI layers, workspaces and extension foundation

Status: **IMPLEMENTED FOUNDATION; SOLVER-CONNECTED CAPABILITIES REMAIN GATED**.
Date: 2026-09-14. Owner and authorizing project owner: Rayla May.

## Objective and owner instruction

Rayla May instructed this work unit to continue UI development before DW4. The
approved scope adds usable presentation controls and stable future-facing
boundaries without adding control physics, dynamic simulation, propulsion models or
calculated engineering values.

## Requirements, scope and boundaries

This work advances `UIX-PFD-001`, `UIX-PERF-001`, `UIX-A11Y-001`, `PFD-003` and
the workspace/layer direction in Sections 7–8 of the native action plan. It adds:

- a persistent **Layers & Groups** dock and compact visible PFD toolbar;
- overlapping presentation-only visual stream groups, explicit member selection,
  active-group halo, visibility and isolate actions;
- versioned engineering subsystems whose membership changes a separate project
  engineering-content hash;
- base stream styling, labels, diagnostic line patterns, static direction arrows,
  artifact-gated flow markers, scene-relative speed and a source/scale legend;
- a prominent Flowsheet/Dynamics/Controls switcher, with future workspaces disabled
  and their missing milestone/capability stated;
- neutral workspace-manifest, control graph/signal/schedule/event/trajectory,
  visualization-frame and extension contracts;
- explicit extension admission policy, a language-neutral worker schema and a
  precompiled C++ stable C ABI header; and
- a reserved namespaced `domain-package` capability with no propulsion physics.

Qt owns drawing, selection and effective reduced-motion handling. `PfdService`
owns atomic group edits and membership validation. The scientific kernel remains
unchanged. React/FastAPI remain present. The extension service accepts an injected
runner but this work does not implement code discovery, installation, dynamic
library loading, process sandboxing or dependency resolution.

## Assumptions and verified facts

- Visual groups may overlap. Only the active group draws a highlight halo. A group
  click never changes engineering selection; **Select members** does so explicitly.
- Visual groups, active layers and motion settings are presentation state.
  Engineering subsystems are engineering state and participate in
  `bh-pfd-engineering-identity-v1` hashing.
- The existing solver engineering hash retains its established meaning. DW4 must
  combine or map the project-level subsystem identity into validation receipts
  before subsystem-dependent calculations exist.
- Saved `bh-pfd-document-v1` files that predate the new defaulted fields remain
  readable. The neutral codec still rejects unknown fields and missing required
  fields in every contract family.
- Motion requires a `FlowVisualizationFrame` naming a completed-run artifact or
  dynamic-telemetry source. No frame means static arrows and a visible “no run
  artifact selected” legend. Invalid/stale states retain text tooltips and line
  patterns in addition to colour.
- The system reduced-motion preference is read through bounded platform adapters
  on macOS, Windows and GNOME Linux. Manual reduced motion always pauses markers.
- Every extension result remains `UNVERIFIED_EXTENSION`, including successful
  output from a trusted in-process plugin.

## Selected design and material alternatives

The implementation extends the current raster `QGraphicsView`, because DW3 already
selected it from measured pan/zoom/selection/drag/label evidence. Scene items use a
base line, separate group halo and a marker so each precedence layer remains
inspectable. A shader or Qt Quick renderer would add a second rendering system
without evidence of a current bottleneck.

The three workspaces use linked, independently versioned document references.
Dynamics and Controls remain disabled because enabling empty canvases could imply
capabilities that do not exist. The general control graph contract covers typed
signals and common block categories now; M7/M9 will select and verify numerical
engines, algebraic-loop handling and process semantics.

The extension foundation separates admission policy from execution adapters. The
default tier uses language-neutral messages. Performance-sensitive C++ code can
later use a C ABI, which avoids exporting C++ runtime types. Unsupported developer
mode remains visibly attributable and requires explicit enablement.

## Files and contracts changed

- `src/bh_sim/boundary/contracts.py`: visual groups, subsystems, layer/frame,
  workspace, control and plugin contracts plus PFD edits.
- `src/bh_sim/boundary/json_codec.py`: narrow migration support for new defaulted
  PFD envelope fields.
- `src/bh_sim/application/pfd.py`: grouping policy, recovery and project content hash.
- `src/bh_sim/application/extensions.py`: extension admission and failure records.
- `src/bh_sim/application/control.py`: replaceable future plant, control,
  coordinator, ODE/DAE and root-finding ports without implementations.
- `src/bh_sim/uix/pfd_editor.py`, `pfd_canvas.py`, `accessibility.py`: dock, toolbar,
  workspace switch, styling, markers, legends and reduced motion.
- `sdk/cpp/bh_plugin.h` and `docs/extensions/worker-protocol-v1.schema.json`: proposed
  SDK ABI and isolated framing foundation.
- `tests/fixtures/dw3_1/`: fixed control-diagram and plugin-manifest fixtures.
- `tools/benchmark_animation.py`: production-canvas 30 fps probe.

## Schema, migration, dependency and scientific impact

The PFD envelope gains defaulted additive fields. The codec permits their absence
only for `PfdDocumentDto`; it does not loosen unknown-field rejection. Existing
native files remain immutable and are not rewritten on read. New control and plugin
contracts have independent schema identifiers. No canonical scientific artifact,
HTTP schema or worker protocol changes.

The work adds no Python or web dependency and no commercially licensed library.
The C SDK header currently inherits the repository licence; Rayla May should choose
a dedicated SDK licence before treating it as a broadly redistributable third-party
development kit. No security sandbox claim follows from the worker JSON schema.

The implementation changes no equation, coefficient, correlation, property data,
phase behavior or model authority. Synthetic benchmark flow values serve rendering
only and cannot be submitted to the solver.

## Verification and observed results

Focused checks on 2026-09-14:

- `.venv/bin/python -m pytest tests/test_pfd.py tests/test_pfd_editor.py tests/test_extensions.py tests/test_control_contracts.py -q` — **43 passed**.
- `.venv/bin/ruff check src/bh_sim ...` over changed source/tests/tools — **passed**.
- `.venv/bin/pyright --pythonpath .venv/bin/python` — **passed** after the focused
  implementation slice.
- `.venv/bin/python -m pytest -q` — **143 passed**, with one existing Starlette
  deprecation warning.
- `npm test -- --run`, `npm run lint`, `npm run build` in `web/` — **5 passed**;
  lint and production build passed.
- `.venv/bin/python tools/check_project.py` — **passed** with 184 historical Git
  objects unchanged and 274 public links checked.
- `clang -fsyntax-only -x c sdk/cpp/bh_plugin.h` — **passed**.
- Native Cocoa probe:
  `.venv/bin/python tools/benchmark_animation.py --output docs/native/evidence/dw3-1/animation-raster-50.json --frames 300` — **accepted**.

The native probe used 50 equipment, 45 streams and 300 timer-driven frames. It
recorded p95 CPU paint time **4.00 ms**, p99 **4.81 ms**, maximum **6.40 ms**,
p95 timer-to-paint **6.43 ms**, no frame interval above 50 ms, 3.12 CPU seconds over
10.24 elapsed seconds, and all source/zero/reverse/stale/path correctness checks.
See the [raw report](evidence/dw3-1/animation-raster-50.json) and
[captured scene](evidence/dw3-1/animation-raster-50.png). A separate
[native full-window capture](evidence/dw3-1/native-window.png) verifies the visible
two-row PFD toolbar, workspace switcher, dock categories and active-group halo.
These results satisfy the
approved p95 33 ms target on this Mac. They do not measure compositor/GPU completion,
energy, physical input-to-photon delay or other supported platform classes.

## Risks, rollback, limitations and remaining decisions

Removing the new PFD fields restores the prior editor; old saved files still decode.
The current scene rebuilds on each immutable document edit, and isolate currently
creates one undoable visibility edit per changed group. Actual user sessions should
inform batching and manual-routing changes.

DW4/DW5 must supply attributable run frames, bounded telemetry and status/legend
content. M7/M9 must implement and independently verify dynamic/control numerics.
Future extension work must define loader hardening, process limits, permission
enforcement, platform sandboxing, package signatures, dependency policy and a C++
SDK licence. A propulsion programme must pass its own evidence/model lifecycle.

Packaging, Windows/x86_64, Linux, VoiceOver and clean-machine checks remain future
evidence. This work unit does not close those gates.
