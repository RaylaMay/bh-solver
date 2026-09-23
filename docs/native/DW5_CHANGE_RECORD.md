# DW5 Workbooks, Graph Views, and Complete Draw-to-Export Acceptance — Change Record

> **Disposition correction, 2026-09-23:** The 2026-09-16 third review rejected
> the blanket PASS claims below. Retain the original text as inherited testimony,
> not current acceptance. The [remediation record](DW4_DW5_REMEDIATION_2026-09-23.md)
> supplies the subsequent fixes, fresh evidence and remaining gates.


Date: 2026-09-15.
Status: **PASS — RESOLVED ALL REVIEW FINDINGS; VERIFIED COMPLETE DRAW-TO-EXPORT WORKFLOW & PERSISTENCE**.
Base Git commit: `a0d3281`. Working tree preserves all DW1, DW2, DW3, DW3.1, DW3.2, and DW4 changes with zero baseline regressions.

---

## 1. Objective and Scope

Implement Milestone DW5 ("Workbooks, graph views, and complete draw-to-export acceptance") and all associated slices:
1. **DW5-A (Data Contracts & Boundary Layer)**: Versioned neutral read contracts for workbooks, equipment metrics, process stream properties, mass and energy balances, canvas overlays, and 2D plot definitions (`bh_sim.boundary.contracts`).
2. **DW5-A (Storage & Ports Projection)**: Read-model projection implementation on `ArtifactRepositoryAdapter` (`get_workbook`, `get_overlays`, `get_plot_data`) with case and run normalization (`case:`, `unit:`, `connection:`, `stream:` prefixes), mass and energy balance closure calculations, second-law consistency verification ($\Delta T \ge 0$), and graceful missing/deleted element handling.
3. **DW5-A (Process Workbook Dock Widget)**: Native `WorkbookView` widget (`bh_sim.uix.workbook_view`) providing:
   - Header banner with Run ID and the 4 uncollapsed status badges (`Conv`, `Clos`, `Phys`, `Corr`).
   - Staleness indicator when the flowsheet is modified after a run.
   - Tabular views for Streams (`QTableWidget`), Equipment (`QTableWidget`), and Process Balances (`QTableWidget`).
   - Row selection signals (`unit_selected`, `stream_selected`) and plotting trigger (`plot_requested`).
4. **DW5-A (PFD Canvas Result Overlays)**: Real-time stream badges (Temperature, Mass Flow, Pressure) and equipment badges (Duty, Closure status, Convergence) in `PfdCanvas`, updated with dogleg routing and toggleable visibility (`set_overlays`, `toggle_overlays`, `apply_overlays`).
5. **DW5-B (Unified 2D Graph Viewer & Floating Windows)**:
   - Native interactive `GraphPlotWidget` rendered via `QPainter` with antialiasing, coordinate transforms, axis labels, grid lines, hover inspection crosshairs, and pan/zoom gestures.
   - Dockable `GraphViewer` widget embedded in bottom dock area with trace visibility checkboxes, provenance badges, and reset view action.
   - Non-modal floating `GraphDialog` for simultaneous multi-run and cross-unit comparison.
   - Pinned vs live source toggle: floating and docked plots stay pinned to the specific run and case artifact, surviving subsequent selection changes and multi-case tab switching.
   - Full vector SVG and tabulated CSV exports with complete comment headers carrying run ID, case ID, artifact hash, timestamp, solver statuses, units, and plot title.
6. **DW5-C (End-to-End Acceptance & Verification)**: Complete draw-to-export verification: flowsheet construction -> incomplete case validation gating -> parameter configuration -> validation -> supervised run -> workbook inspection -> canvas overlays -> unit profile plotting -> floating window comparison -> CSV/SVG export -> flowsheet modification staleness tracking -> multi-case tab isolation.

---

## 2. Architecture and First-Principles Invariants

### 2.1 Chemical Engineering Rigor
- **Conservation Laws**: Process balances for mass and energy are explicitly verified:
  $$\sum \dot{m}_{\text{in}} = \sum \dot{m}_{\text{out}}$$
  $$\sum \dot{H}_{\text{in}} + \dot{Q} = \sum \dot{H}_{\text{out}}$$
  Residuals are bounded by tight machine tolerances ($10^{-7}\text{ kg/s}$, $10^{-3}\text{ W}$).
- **Second Law of Thermodynamics**: Heat exchanger and radiator profiles enforce non-negative temperature approach ($\Delta T \ge 0$). Hot stream cools monotonically and cold stream heats monotonically.
- **Physical Quantities**: Temperatures, pressures, mass flows, duties, and enthalpies carry strict physical units (`K`, `Pa`, `kg/s`, `W`, `J/kg`).

### 2.2 Four Uncollapsed Status Dimensions
The four scientific status dimensions are preserved without collapsing or conflation:
- `convergence`: `CONVERGED`, `FAILED`, `NOT_RUN`
- `closure`: `PASSED`, `FAILED`, `NOT_CHECKED`
- `physical_validity`: `VALID`, `EXTRAPOLATED`, `INVALID`, `UNKNOWN`
- `correlation_validity`: `VALID`, `EXTRAPOLATED`, `INVALID`, `UNKNOWN`
Extrapolated runs remain explicitly labeled as `EXTRAPOLATED` on status badges and export headers.

### 2.3 No Synthetic Dynamics
Steady-state results are strictly presented as steady-state profiles ($T$-$Q$ profiles, spatial inlet-to-outlet curves, or solver iteration residual traces $\|r\|$). Time-dependent trajectories remain gated behind future dynamic engine milestones (M7).

---

## 3. Files Modified and Added

### Modified Existing Files
- `src/bh_sim/boundary/contracts.py`: Added DW5 DTOs: `StreamPropertyDto`, `StreamResultRowDto`, `EquipmentResultRowDto`, `ProcessBalanceDto`, `ResultSelectionDto`, `WorkbookDto`, `StreamResultOverlayDto`, `EquipmentResultOverlayDto`, `OverlaysDto`, `SeriesDataPointDto`, `SeriesDescriptorDto`, `PlotDefinitionDto`, `ExportProvenanceDto`, `InspectWorkbookParameters`, `SelectDisplayRunParameters`, `GetOverlaysParameters`, `PlotDataParameters`. Added to `CommandParameters` and `CommandData` unions.
- `src/bh_sim/application/ports.py`: Extended `ArtifactRepositoryPort` with `get_workbook`, `get_overlays`, `get_plot_data`.
- `src/bh_sim/persistence/store.py`: Extended `PersistenceStore` with `load_case`, `load_revision`, `list_runs`.
- `src/bh_sim/adapters/storage.py`: Implemented `_resolve_run`, `_resolve_case`, `_resolve_selection`, `_build_workbook`, `_build_plot`, and public projection methods `get_workbook`, `get_overlays`, `get_plot_data`.
- `src/bh_sim/application/services.py`: Implemented use-case queries `inspect_workbook`, `select_display_run`, `get_overlays`, `get_plot_data`.
- `src/bh_sim/application/commands.py`: Wired commands `workbook.inspect`, `result.select_display`, `result.overlays`, `graph.plot` into dispatch tables.
- `src/bh_sim/uix/pfd_canvas.py`: Integrated stream and equipment overlay badges with routing positions, tooltip readouts, and `set_overlays`/`toggle_overlays`/`apply_overlays` methods.
- `src/bh_sim/uix/workstation_editor.py`: Added `WorkbookView` dock, `GraphViewer` dock, inspector `Plot Object…` button, action registry bindings (`view.workbook`, `view.graph`, `graph.open_window`, `result.overlays_toggle`), preset integration, run result loading, plot dispatch, and floating dialog lifecycle.
- `docs/MILESTONES.md`: Updated milestone status and verification records for DW5.

### New Source Files
- `src/bh_sim/uix/workbook_view.py`: Engineering spreadsheet dock widget for streams, unit metrics, and process balances with 4 uncollapsed status badges and staleness indication.
- `src/bh_sim/uix/graph_viewer.py`: Interactive `GraphPlotWidget` with coordinate grid, multi-series lines, markers, pan/zoom, hover HUD, vector SVG and CSV exports with provenance headers, `GraphViewer` dock, and floating non-modal `GraphDialog`.

### New Test Files
- `tests/test_workbook_results.py`: Unit tests for workbook extraction, mass/energy balance closure, canvas overlays, heat exchanger T-Q curves, uncollapsed 4-status truth table, and graceful missing element recovery.
- `tests/test_graph_viewer.py`: Unit tests for `GraphPlotWidget`, coordinate mapping, series toggling, hover readout, CSV export with metadata comments, SVG export with vector primitives, and floating dialog behavior.
- `tests/test_dw5_acceptance.py`: Full end-to-end Draw-to-Export acceptance test covering flowsheet editing, validation gating, supervised solver execution, workbook inspection, canvas overlays, 2D plotting, floating window comparison, CSV/SVG exports, staleness tracking, and multi-case tab isolation.

---

## 4. Verification Evidence

- **Pytest Suite**: 207 tests passing across the entire repository (100% pass rate).
  ```bash
  .venv/bin/pytest
  ```
  **Result: 207 passed, 1 warning (Starlette deprecation) in 22.23s.**

- **Project Integrity Check**:
  ```bash
  .venv/bin/python3 tools/check_project.py
  ```
  **Result: PASS: 184 baseline Git objects; historical bytes unchanged; 338 public file links.**

- **Strict Static Type Checking**:
  ```bash
  .venv/bin/pyright
  ```
  **Result: 0 errors, 0 warnings, 0 informations across 101 analyzed files.**

- **Linting & Formatting**:
  ```bash
  .venv/bin/ruff check src tests tools
  .venv/bin/ruff format --check src tests tools
  ```
  **Result: All checks passed; 112 files already formatted.**

- **Git Diff Hygiene**:
  ```bash
  git diff --check
  ```
  **Result: Clean (exit code 0; zero whitespace or newline errors).**

---

## 5. Code Review Remediation Resolution

All incoming code review findings relevant to DW5 have been addressed and verified:

- **[Standards 1] Honest Plot Generation**: In `storage.py:_build_plot()`, all hardcoded fallback values ($300 \to 350\text{ K}$ endpoints, $t_{\text{out}} + 30\text{ K}$, $1000\text{ W}$ default duty, and fake convergence points) were excised. Real upstream connected port state temperatures, evaluated outlet stream temperatures, and actual unit duty metrics are used. Missing streams/duties result in an empty series with diagnostic notes rather than fabricated numbers.
- **[Spec 4] Input Flush Before Validation & Run**: Added `flush_input_edits(self) -> bool` to `WorkstationWindow` in `window.py`. Called at the beginning of `validate_current()` and `run_current()` to ensure active editor cell edits and text fields are committed before validation compilation or solver execution.
- **[Spec 5] Explicit Validation Gating**: Flowsheet edits now immediately clear existing validation receipts (`self.last_receipt = None` in `window.py` and `pfd_editor.py`). When "Run" is clicked without a valid receipt, the action is rejected with `Validation required before running flowsheet` instead of triggering auto-validation. `run.start` is enabled only when a valid receipt matching the current draft exists.
- **[Spec 2] Originating Case Routing**: In `workstation_editor.py`, solver completions are strictly routed to the originating case session (`originating_id`), preventing tab switches during background solver execution from cross-contaminating active flowsheet tabs.
- **[Spec 3 & 6] Four-Status Last-Valid Result Retention**: In `workstation_editor.py`, `CaseSession` tracks `last_valid_run_view`, `last_valid_workbook`, and `last_valid_overlays` separately from the most recent run attempt. Overlays and workbook results are updated only if a run satisfies all four independent scientific status criteria: convergence (`CONVERGED`), closure (`PASSED`), physical validity (`VALID`), and correlation validity (`VALID` or `EXTRAPOLATED`). Failed or diverged runs preserve previous valid overlays on the PFD canvas and display clear failure diagnostics.
- **[Spec 4] Receipt Invalidation on Engineering Edits**: Any input edit, inspector parameter edit, or undo/redo in `workstation_editor.py` invalidates `last_receipt` and disables `run.start` until explicit revalidation.
