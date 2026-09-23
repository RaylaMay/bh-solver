# DW3.2 interface and persistent history — change record

Date: 2026-09-14. Rayla May authorized this work through the implementation plan.
Status: **IMPLEMENTED LOCAL WORKSTATION; REMAINING GATES IDENTIFIED BELOW**.
Base Git commit: `a0d3281`. The working tree already contained DW3/DW3.1 changes;
this work preserves those changes and creates no commit or remote publication.

## Objective, instructions and references

Implement Rayla May's approved compact interface, optional ribbon, independent case
tabs, visible dock access, command line, durable undo/recovery, named snapshots,
alternative histories and structural comparison before DW4. Rayla May selected
LAN/VPN simultaneous editing as a separate following milestone. References:
ADR-005/009/010, new ADR-011, PFD-003/005, UIX-CMD-001, UIX-A11Y-001,
UIX-PERF-001 and the new DW3.2 requirements in the verification matrix.

The design uses contextual commands and collapsible navigation informed by
[Fusion's documented interface](https://help.autodesk.com/view/fusion360/ENU/?contextId=LP-STEPS-P13N-SNP-GS-OTH-CRD-1)
and Rayla May's supplied screenshot. BH history tracks engineering edits and
checkpoints; it does not reproduce Fusion's parametric calculation timeline.

## Scope, boundaries, assumptions and evidence

- `WorkstationEditor` reuses the retained PFD editor/canvas. The launcher selects it;
  existing DW2/DW3 editor classes, the kernel and React/FastAPI remain in place.
- Qt owns personal interaction and layout. `HistoryService` owns editing policy,
  head checks, alternatives, undo, snapshots and structural comparisons through
  neutral typed commands. UIX does not import that service or persistence adapters.
- `JsonHistoryRepository` owns atomic immutable JSON checkpoints/events, verifies
  bytes on reads and detects record-chain gaps and publication collisions.
- A continuous local journal records committed edits. Save adds a native revision
  reference and preserves undo. A snapshot records an exact checkpoint. Old documents
  import as one labelled starting point; original files remain unchanged.
- Undo/redo append attributable events. Cross-actor or changed-content reversals
  reject. This establishes a local foundation, not concurrent selective undo.
- Quantities remain submitted inputs with explicit units; no numerical model,
  coefficient, property adapter, scientific approval or calculation authority changes.
- Run, Dynamics, Controls and HAZOP retain their existing capability gates. Result
  references are typed but cannot be populated from the preview's absent run selection.

## Selected design, alternatives and tradeoffs

Use compact native commands, case tabs, a full canvas, searchable browser, contextual
inspector and bottom panel access. Offer ribbon and layout presets through the same
registry. The initial [clickable prototype](prototypes/dw32-layout.html) preceded the
native shell work. Browser automation blocked inspection of that local HTML under
its URL policy; the prototype is not represented as an automated visual acceptance.

Retain immutable checkpoints instead of re-executing old editing/numerical commands.
Keep canonical JSON authoritative instead of introducing an opaque database-only
history. Keep committed-edit recovery separate from explicit version saves. The
cost is additional disk usage, which remains visible and unpruned by policy.

The initial complete-window benchmark passed paint timing but failed edit-to-paint
latency: p95 drag 116.28 ms and labels 119.28 ms. Profiling found repeated immutable
checkpoint decoding. Bounded caches now retain 64 decoded checkpoints and 2,048
records while reads still verify SHA-256 over disk bytes. The
[initial measurements](evidence/dw3-2/workstation-initial.json) remain alongside the
[final benchmark](evidence/dw3-2/workstation-benchmark.json).

## Files and contract changes

- Neutral `HistoryEntry/State`, branch/save/snapshot/result references, history
  targets and structural comparison types; strict tagged serialization remains.
- `application/history.py`, `adapters/history.py`, shared command registration and
  preview composition. No scientific artifact or HTTP schema changes.
- `uix/workstation_editor.py`, `uix/command_line.py`, workspace templates/personal
  identity, a canvas-construction measurement hook and shared rename confirmations.
- Native launcher/design tokens, focused history/widget tests, a fixed history
  fixture, native capture and full-workstation benchmark tools.
- Input commits retain their originating tab and finish before Save, Snapshot or
  navigation. Comparison rows show equipment tags and submitted quantity units.
- Architecture, ADR, contracts, PFD, failure, dependency, requirements, milestone
  and native-plan documentation; [DW3.3 collaboration gate](DW3_3_COLLABORATION.md).

The formatter also normalized seven pre-existing DW3.1 files (codec, accessibility,
canvas, control/extension tests, animation benchmark and DW3.1 capture). Those edits
change formatting only; the overlapping earlier work remains intact.

## Verification

All commands ran from the repository root unless a working directory is stated.
The final native probe used Qt 6.11.2, Cocoa, macOS 26.4.1 and arm64. These results
describe the local development checkout, not an installer or scientific approval.

| Command | Observed result |
|---|---|
| `QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q` | 173 passed in 17.69 s; one existing Starlette/httpx deprecation warning. Includes boundary, history, legacy API, scientific and UI tests. |
| `QT_QPA_PLATFORM=cocoa .venv/bin/pytest -q tests/test_workstation_editor.py` | 13 passed in 7.51 s on the native platform; these tests also belong to the full suite above. |
| `.venv/bin/ruff check src tests tools` | Passed. |
| `.venv/bin/ruff format --check src tests tools` | 97 files already formatted. |
| `.venv/bin/pyright --pythonpath .venv/bin/python` | Zero errors, warnings or information diagnostics. |
| `npm test` in `web` | 5 passed. |
| `npm run lint` in `web` | Passed. |
| `npm run build` in `web` | TypeScript and Vite production build passed. |
| `.venv/bin/python tools/check_project.py` | Passed: 184 baseline Git objects, historical evidence bytes unchanged, public Markdown file links resolve. |
| `git diff --check` | Passed. |
| `uv build --offline` | Built `dist/bh_sim-0.1.0.tar.gz` and `dist/bh_sim-0.1.0-py3-none-any.whl` using existing dependencies. |

History tests exercise Save/restart/undo/redo, named snapshots, retained alternatives,
stale-head and actor rejection, durable request deduplication, an abrupt subprocess
exit, orphan checkpoints, corrupt/missing records, failed writes and interrupted
Save acknowledgement. Legacy import retains original file bytes and introduces
only one starting event. Recovery spies reject calculation or command replay.
Widget tests cover independent tabs, read-only historical views, template rejection,
themes, reduced motion, units, shared actions, confirmations and input/tab ordering.

`QT_QPA_PLATFORM=cocoa .venv/bin/python tools/capture_dw32_window.py --output docs/native/evidence/dw3-2/native-window.png`
captured [Design](evidence/dw3-2/native-window.png),
[ribbon](evidence/dw3-2/ribbon.png) and [Compare](evidence/dw3-2/compare.png) layouts.
Visual inspection checked canvas use, inspector field visibility, dock access and
readable quantity comparisons. The tool waits for native layout before fitting
the scene. It uses isolated incomplete fixtures and performs no calculation.

`QT_QPA_PLATFORM=cocoa .venv/bin/python tools/benchmark_workstation.py --output docs/native/evidence/dw3-2/workstation-benchmark.json`
passed the accepted 50-equipment/45-stream workload. Each workload has 30 samples;
nearest-rank p99 is therefore the maximum sample. Times below are milliseconds.

| Workload | Paint p95 | Paint p99 | Event-to-paint p95 | Event-to-paint p99 |
|---|---:|---:|---:|---:|
| Pan | 7.13 | 7.26 | 12.55 | 16.24 |
| Zoom | 7.83 | 7.98 | 9.09 | 9.36 |
| Selection | 3.82 | 4.49 | 5.44 | 7.46 |
| Durable drag | 2.91 | 3.17 | 37.43 | 45.25 |
| Durable label edit | 2.09 | 2.67 | 43.42 | 44.45 |

Every workload passed p95 paint ≤33 ms and event-to-paint ≤50 ms. Selection identity,
persisted drag/label edits, orthogonal routes and typed-port endpoints passed.
The process used 3.35 CPU seconds over 5.86 elapsed seconds, including initialization
and timer intervals. The viewport measured 862 × 570 Qt logical pixels. The report
retains raw samples; it does not claim physical input-to-display latency.

The [evidence manifest](evidence/dw3-2/manifest.json) records SHA-256 identities for
the directly affected implementation, tests, documentation and capture inputs,
plus the outputs. It is an unsigned work-unit record, not a signature or an
independent approval. GitHub Actions, Windows/Linux native execution, full
VoiceOver interaction and installer acceptance were not run in this work unit.

## Risks, rollback and remaining gates

- OS accessibility automation timed out attaching to the native Python application.
  Native Qt widget/keyboard tests and screenshots do not establish a VoiceOver or
  full assistive-technology walkthrough. Retain that unverified gate explicitly.
- The native benchmark measures synthetic Qt input/commands to CPU paint completion
  on this Mac. It does not measure physical input-to-photon latency, another platform,
  a long-running collaboration session or arbitrary history sizes.
- Committed edits survive process exit; uncommitted field keystrokes do not carry
  that durability claim. Disk failures retain prior committed state and diagnostics.
- Corrupt histories fail explicitly. Hashes detect accidental corruption, not a
  maliciously rewritten whole chain or an unknown deleted tail. There is no signing.
- The UI currently materializes the case's history index; very large histories need
  paging and additional performance evidence. Disk history is not silently pruned.
- Legacy clients do not synchronize with an already-established working history.
  Preserve separate saved revisions and perform explicit import/reconciliation.
- Result links, complete worker/last-valid UI, HAZOP records and numerical workspaces
  remain DW4/DW5/DW6/DW8/M7/M9 work. Live collaboration remains behind DW3.3's
  protocol/failure-review gate; no network listeners or project uploads were added.
- Rollback selects the retained `PfdEditorWindow` in the launcher. Existing native
  saved revisions remain readable. Export/save desired current work first because
  the older editor does not consume the new history journal. Preserve journal files.

No additional dependency, licence, provider, network, audio or telemetry collection
was introduced. The project retains Rayla May's licence and existing Qt LGPLv3 route.
