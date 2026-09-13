# DW3 implementation and verification record

Date: 2026-09-13. Status: **EDITOR IMPLEMENTED; REVIEWABLE LOCAL CHANGES**.
Author: Rayla May. No independent scientific verification or model approval is claimed.

## Objective and instruction from Rayla May

Complete the public rename transition baseline, measure raster/OpenGL alternatives,
build the native editor and add GitHub Actions. Incorporate the PFD settings,
units, naming, copy/paste and template decisions. Rayla May explicitly accepted
P-02: 50 equipment as the initial reference, p95 paint ≤33 ms and p95 synthetic
event-to-paint ≤50 ms on this Mac; report p99 and correctness as well. Rayla May
accepted these initial targets.

References: ADR-010, DW3, PFD-001/003, UIX-PFD-001, UIX-DOC-001, CORE-002,
[public transition](PUBLIC_BASELINE_TRANSITION.md), [PFD behavior](DW3_PFD.md),
[benchmark record](DW3_BENCHMARK.md), and Appendix A of the native action plan.

## Scope, assumptions and selected design

The solver remains scientific authority. The UI and solver remain replaceable
peers through immutable neutral DTOs and shared application commands. Seven
existing reference-fixture descriptors are mirrored explicitly without promoting
their evidence status or introducing defaults, equations or coefficients.

The raster QGraphicsView canvas is selected for the initial Mac editor because it
passes the agreed reference workload and renders inspectable symbols/text. OpenGL
CPU timings are recorded, but white composited captures prevent a complete visual
comparison. No Qt Quick/Metal escalation is justified by a passing raster reference.
See the benchmark record for exact scope and limits.

A separate versioned native JSON envelope was chosen to preserve routes, viewport,
original notation and preferences without changing scientific canonical artifacts
or silently rewriting the retained browser format. A filesystem adapter implements
append-only native revisions behind a declared application port. This adds an
explicit native format to maintain; it avoids making opaque browser extensions
or miscellaneous sidecar files authoritative for native state.

Editing policy performs local compatibility checks; graph compilation stays in
the kernel. Undo/redo stores document snapshots in this session. This is simple and
reviewable at the approved scene size, with memory cost proportional to history.
History is not a durable audit journal and is cleared when opening another draft.
Command IDs identify attributable requests; no durable worker replay semantics are
introduced. No retries or automatic Runs are added.

A measured 50-equipment command took 190.875 ms before caching repeated static
contract type-hint reflection. With that bounded schema cache, three local timings
were 22.701, 22.030 and 21.379 ms. These are diagnostic samples, not acceptance
percentiles. Every payload still undergoes deep validation, including malformed
DTO tests. The final renderer benchmark includes command dispatch for drag and
label workloads. No cached payload or validation outcome bypass was introduced.

## Files and contracts

- `boundary/contracts.py`: additive native document, preferences, descriptors,
  editing and quantity-display DTOs; cached static schema reflection.
- `boundary/json_codec.py`: reuse the schema cache; strict tagged framing retained.
- `application/pfd.py`: port declarations and atomic editing/persistence policy.
- `application/commands.py`: advertise native commands only when the PFD service
  is injected; existing command names and golden payloads remain unchanged.
- `adapters/pfd.py`: existing-unit conversion, reference descriptors and native store.
- `adapters/desktop_preview.py`: native service composition; scientific ports unavailable.
- `uix/pfd_canvas.py`, `pfd_editor.py`, `pfd_settings.py`: canvas, editor and preference
  preview; retained DW2 shell used as the window foundation.
- `desktop_launcher.py`: select the editor window; no browser/server startup.
- `uix/window.py`: overridable shortcut-restoration hook for the extended registry;
  existing shell behavior and tests retained.
- `tools/benchmark_pfd.py`, `benchmark_editor.py`, `pfd_scene.py`: reproducible native
  renderer workloads; `check_project.py`: baseline and public-link checks.
- `tests/test_pfd.py`, `test_pfd_editor.py`: application, persistence and widget evidence.
- `.github/workflows/checks.yml`: Python checks on macOS/Windows/Linux; browser checks
  on Linux; bounded job time, read-only repository token, no deployment step.

## Impact and alternatives

No numerical code, scientific coefficient, property backend, model card, root licence,
dependency lock or existing golden fixture changes. QtOpenGL/QtOpenGLWidgets are
used only by the benchmark from the already installed PySide6 Essentials wheel.
The production renderer uses QtWidgets. Qt's licensing obligations and unbuilt
release packaging gates remain recorded in the dependency/adoption documents.

All persistence, clipboard and templates are local. No audio, case upload, AI,
telemetry service, new provider, secret or network runtime dependency is added.
The CI file is prepared locally; remote success is not claimed until pushed and run.
Ubuntu/Windows CI tests would establish automated compatibility only, not witnessed
platform performance or installer support.

## Verification, risks and rollback

Final results: **124 Python tests and 5 browser tests passed**. Ruff lint/format,
Pyright, public baseline/link checks, browser lint/build and Python source/wheel
build passed. The Python suite retains one upstream Starlette deprecation warning.
Exact commands/results are recorded in [DW3 verification evidence](evidence/dw3/verification.txt).
The full native witness is deliberately scoped; CI has not run remotely. The dated
public baseline independently retains its original 100-test and 5-browser-test
results. Historical evidence is preserved byte-for-byte as found and explicitly
qualified as sanitized; old hashes are not rewritten.

Open work includes iterative routing/label friction, native accessibility and
printing/export, complete browser migration, full result/worker parity, cross-platform
hardware tests and release packaging. No new scientific authority is granted.
Routing does not promise global obstacle avoidance. Session snapshot history and
request caches consume memory with long editing sessions and require a later
bounded-history policy before long-session release acceptance.

Rollback: restore only the files in this reviewed change set after preserving any
newer edits by Rayla May; retain all native and legacy draft directories. The retained
DW2 window and browser remain available. Old browser readers do not understand the
native envelope; never substitute native files into their directory. Do not use
`git clean`, broad reset, delete drafts or rewrite the public root history.

No further decision by Rayla May is needed to review this implementation. P-02 is accepted
for this initial workload. Full DW3/workstation release acceptance remains distinct
from the implemented editor and its local test evidence.
