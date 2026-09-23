# DW4/DW5 Remediation Handoff — Incoming Code Review Resolution

Date: 2026-09-15.

> 2026-09-23 correction: this historical implementation plan is superseded for
> the six remaining findings by the [third review](DW4_DW5_THIRD_REVIEW_2026-09-16.md)
> and [current remediation record](DW4_DW5_REMEDIATION_2026-09-23.md). JSON publication
> precedes the disposable index. The local root spelling was normalized for portability;
> original bytes are retained in the intake backup. Old link/test counts are historical.
Document: Developer Handoff & Implementation Plan for Fresh Context Window.
Target Scope: Milestones DW4 & DW5 Remediation.
Review Baseline Disposition: **FAIL — do not integrate, commit or push this candidate.**
Remediation Goal: Resolve all 12 review findings (6 Standards, 6 Spec), fix all static analysis deficits (Ruff, Pyright, stderr pipe deadlock), and achieve an auditable, verified **PASS** disposition.

---

## 1. Executive Summary & Repository Environment

### 1.1 Project & Directory Confinement
- **Project Root**: `<checkout>`
- **Strict Boundary**: All edits, tests, scripts, and documentation MUST reside strictly within this repository directory.
- **Zero Unapproved Downloads**: No new packages or external binary downloads are permitted without explicit user approval.
- **Python Virtualenv**: `.venv/bin/python3` (use `BypassSandbox: true` on macOS when running `.venv/bin/python3` commands due to macOS sandbox symlink constraints).
- **Historical Git Objects**: 184 baseline Git objects (338 public links). Verified via `python3 tools/check_project.py` (MUST remain PASS at all times).

### 1.2 Operating Persona: Senior Software Engineer with Chemical Engineering Background
- **Numerical Truth**: The calculation engine / kernel owns numerical truth. Under NO circumstances should the UI, storage adapter, or projection layers fabricate dynamic profiles, synthetic temperatures, or fake duties.
- **Scientific Auditability**: Every line of code, DTO transformation, and unit conversion must be traceable, mathematically sound, and rigorously documented.
- **Four Uncollapsed Status Dimensions**: `convergence`, `closure`, `physical_validity`, `correlation_validity` must remain strictly independent and never collapsed into a single boolean.

---

## 2. Review Findings & Remediation Inventory

The external review by Codex identified 12 specific findings (10 P1, 2 P2) and static check deficits. Below is the comprehensive remediation specification:

### 2.1 Standards Findings (6 items: 5 P1, 1 P2)

#### [Standards 1] (P1 — Fabricated Plot Values)
- **Target File**: `src/bh_sim/adapters/storage.py:580–710`
- **Problem**: `_build_plot()` emitted hardcoded $300 \to 350\text{ K}$ endpoints for heaters when actual calculated inlet/outlet temperatures are $350 \to 355\text{ K}$ (or $360 \to 366\text{ K}$). Fallback branches invented missing duties (`1000.0 W`), missing temperatures (`t_out + 30.0`), and convergence samples (`(1.0, 0.0, "Converged")`).
- **Remediation**:
  1. Retrieve true inlet temperatures from upstream connected port states in `port_values[(source_unit, source_port)]`.
  2. Retrieve true outlet temperatures from evaluated `ev.output_port_values` (`MaterialPortValue`).
  3. Retrieve true heat duties from `ev.metrics` (`metrics_dict.get("duty")`).
  4. If required stream or duty data is missing/unconnected, do NOT guess numbers; raise `ValueError` or return empty series with explicit diagnostics.
  5. In `RESIDUAL_CONVERGENCE`, emit only real iteration or residual records; do not fabricate fake points when data is empty.

#### [Standards 2] (P1 — Failed Persistence Reported as Durable Success)
- **Target File**: `src/bh_sim/application/services.py:238–267`
- **Problem**: In `start_run()`, exceptions from `promote_staged_run` were swallowed in a `try...except`, constructing an empty result view with `persisted=True` and `unit_results=()`.
- **Remediation**:
  1. Remove exception suppression around `promote_staged_run`.
  2. If promotion fails, mark the attempt as `FAILED` (`persisted=False`), set `failure_reason=f"Promotion failed: {error}"`, record the attempt, and raise `CommandRejected("PERSISTENCE_FAILED", ...)`.

#### [Standards 3] (P1 — Admission and Artifact Have Different Run Identities)
- **Target Files**:
  - `src/bh_sim/engine/runner.py:52–65`
  - `src/bh_sim/adapters/engineering.py:206–222`
  - `src/bh_sim/application/ports.py:43–49`
  - `src/bh_sim/worker/entry.py:205–215`
  - `src/bh_sim/application/services.py:297–309`
- **Problem**: The pre-allocated admitted run ID (`job.run_id` / `attempt.run_id`) was not forwarded to the engine runner, causing `runner.py` to generate a fresh random UUID (`attempt.run_id != result.run_id`).
- **Remediation**:
  1. Update `SteadyRunner.run()` to accept `run_id: StableId | None = None` and adopt it: `run_id = run_id or new_stable_id("run")`.
  2. Update `KernelExecutionPort.run()` and `EngineeringAdapter.run()` to accept `run_id: str | None = None`.
  3. In `worker/entry.py`, pass `run_id=msg.run_id` into `adapter.run(...)`.
  4. In `services.py`, pass `run_id=attempt.run_id` when invoking `self.engineering.run(..., run_id=attempt.run_id)`.

#### [Standards 4] (P1 — Promotion Does Not Verify the Admitted Artifact)
- **Target Files**:
  - `src/bh_sim/adapters/storage.py:114–125`
  - `src/bh_sim/application/services.py:238–243`
- **Problem**: `promote_staged_run` read staged JSON without verifying that `run_id`, `case_id`, revision, and digest matched the admitted job.
- **Remediation**:
  1. In `storage.py`, update `promote_staged_run(staged_path, *, expected_run_id=None, expected_case_id=None, expected_hash=None)`.
  2. Verify that the staged file exists, its content sha256 matches `expected_hash`, and the parsed `RunResult.run_id` and `RunResult.case_id` match `expected_run_id` and `expected_case_id`.
  3. In `services.py`, pass `expected_run_id=job.run_id, expected_case_id=job.case_id, expected_hash=terminal.artifact_hash`.

#### [Standards 5] (P2 — Attempt Audit Exists Only in Disposable SQLite Index)
- **Target File**: `src/bh_sim/persistence/store.py:234–285, 447–488`
- **Problem**: Attempt records were only written to SQLite table `attempts`. Rebuilding the index from raw files lost attempt history.
- **Remediation**:
  1. Add an `attempts` directory under `PersistenceStore`: `self.attempts_dir = root_path / "attempts"`.
  2. In `record_attempt(attempt)`, write an immutable JSON attempt manifest (`attempts/{attempt.attempt_id}.json`) atomically to disk alongside SQLite indexing.
  3. In `rebuild_index_from_artifacts()`, scan `self.attempts_dir.glob("*.json")`, parse each attempt JSON, and re-populate the SQLite `attempts` table.

#### [Standards 6] (P1 — Worker Protocol Metadata Not Enforced)
- **Target File**: `src/bh_sim/adapters/worker_supervisor.py:95–122, 260–295`
- **Problem**: Supervisor accepted unsupported protocol versions; did not verify worker session ID and monotonic sequence numbers; missing stderr drain caused OS pipe buffering deadlocks.
- **Remediation**:
  1. In `WorkerSupervisor.start()`, verify `c.WORKER_PROTOCOL_VERSION in hello.supported_protocols`. If not supported, send `WorkerReady(selected_protocol="", accepted=False, message="Unsupported protocol")` and raise `SupervisorError`.
  2. Add dedicated `_stderr_drain_loop` thread reading `self._process.stderr` continuously until EOF.
  3. In `_reader_loop`, verify `msg.worker_session_id == self._session_id` and enforce strictly monotonic sequence numbers (`msg.sequence > self._last_sequence[run_id]`). Quarantine or reject invalid frames.

---

### 2.2 Spec Findings (6 items: 5 P1, 1 P2)

#### [Spec 1] (P1 — Wire Worker into Native Launch)
- **Target File**: `src/bh_sim/desktop_launcher.py`
- **Problem**: `desktop_launcher.py` used `create_preview_gateway` with `run.start` disabled; no supervisor was instantiated.
- **Remediation**:
  1. Instantiate `WorkerSupervisor()` in `desktop_launcher.py`.
  2. Start the worker supervisor process: `supervisor.start()`.
  3. Supply supervisor to `create_supervised_gateway(root, supervisor=supervisor)`.
  4. Connect `app.aboutToQuit.connect(supervisor.stop)` to ensure graceful cleanup.

#### [Spec 2] (P1 — Make Run Asynchronous and Cancellable)
- **Target Files**:
  - `src/bh_sim/uix/window.py:467–518`
  - `src/bh_sim/application/services.py:326–343`
- **Problem**: `window.py` synchronously blocked on the Qt UI thread while waiting for solver execution; UI froze; Cancel used placeholder `"run:in-flight"`.
- **Remediation**:
  1. Run solver asynchronously off the GUI thread (via background thread / QThread) so the Qt event loop stays responsive.
  2. While running, enable Cancel button.
  3. In `services.py:cancel_run()`, if `run_id` is empty or `"run:in-flight"`, look up active admitted/running attempts for the case and cancel the real admitted run ID.

#### [Spec 3] (P1 — Bind Validation to Actual Worker Context)
- **Target File**: `src/bh_sim/application/services.py:134–158`
- **Problem**: Discarded `resp.context_hash` returned by `supervisor.validate()`, causing "execution context changed before snapshot" error when running with the real child worker.
- **Remediation**:
  1. Preserve and adopt `context = resp.context_hash` when worker validation succeeds so the validation receipt matches the worker's execution context.

#### [Spec 4] (P1 — Flush Inspector Edits Before Validate/Run)
- **Target Files**:
  - `src/bh_sim/uix/window.py:450–480`
  - `src/bh_sim/uix/workstation_editor.py`
- **Problem**: Pending inspector edits (e.g. typing 125,000 W in duty parameter) were not flushed before Validate or Run clicked, causing changes to be lost.
- **Remediation**:
  1. Call `self.flush_input_edits()` at the very beginning of both `validate_current()` and `run_current()`.

#### [Spec 5] (P2 — Require Explicit Validation Before Enabling Run)
- **Target File**: `src/bh_sim/uix/window.py:467–477`
- **Problem**: Auto-validated when Run was clicked without receipt; Run stayed enabled after engineering edits.
- **Remediation**:
  1. Any flowsheet edit must invalidate `self.last_receipt = None` and disable `run.start`.
  2. In `run_current()`, if `self.last_receipt is None or self.last_receipt.draft_id != self.current.draft_id`, do NOT auto-validate. Reject with explicit note: `"Validation required before running flowsheet."`.

#### [Spec 6] (P1 — Preserve Last-Valid Overlays After Scientific Failure)
- **Target File**: `src/bh_sim/uix/workstation_editor.py:1425–1448`
- **Problem**: Replaced active workbook and overlays unconditionally on every completed run, wiping out valid results when a subsequent solve failed or diverged.
- **Remediation**:
  1. In `CaseSession`, track `last_valid_run_view`, `last_valid_workbook`, `last_valid_overlays` separately from `last_run_view`.
  2. Only update `last_valid_*` if run converged and is physically valid.
  3. On solve failure / invalidity, update `last_run_view` and status banner diagnostics, but retain previous `last_valid_overlays` on canvas. Provide explicit selector to view active vs last-valid results.

---

### 2.3 Static Analysis Deficits

1. **Pyright Type Checking**:
   - Add `venvPath = "."` and `venv = ".venv"` in `pyproject.toml` under `[tool.pyright]`.
   - Fix `QByteArray` typing in `pfd_canvas.py` (`bytes(mime.data(...))` instead of passing `QByteArray` directly where buffer protocol is expected).
   - Fix literal typing for 4-status strings in `src/bh_sim/worker/entry.py`.
   - Fix optional member access in `workstation_editor.py`.
2. **Ruff Lint & Format**:
   - Fix all 111 line-length (E501) and unused imports (F401) across `src/`, `tests/`, and `tools/`.
   - Run `.venv/bin/ruff format src tests tools`.
3. **Supervisor Stderr Drain**:
   - Add dedicated background thread `_stderr_drain_loop` in `WorkerSupervisor` to prevent pipe deadlocks.

---

## 3. Sequential Implementation Plan

The remediation execution is divided into 3 ordered phases:

```
┌──────────────────────────────────────────────────────────────┐
│ Phase 1: Core Solver, Protocol & Persistence Remediation     │
│ - Standards 1 (no fake plot values/duties)                   │
│ - Standards 2 (no swallowed persistence failure)             │
│ - Standards 3 (admitted run_id propagation)                  │
│ - Standards 4 (verify staged artifact on promotion)          │
│ - Standards 5 (durable attempt manifests on disk)            │
│ - Standards 6 (protocol checks, session/seq, stderr drain)   │
│ - Spec 3 (bind validation to worker context hash)            │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Phase 2: UIX Execution, Validation & Overlays Remediation    │
│ - Spec 1 (wire worker into native launcher)                  │
│ - Spec 2 (asynchronous, non-blocking cancellable solve)      │
│ - Spec 4 (flush inspector edits before validate/run)         │
│ - Spec 5 (explicit validation gating, disable run on edit)   │
│ - Spec 6 (retain last-valid overlays on solver failure)      │
│ - Fix canvas QByteArray typing                               │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│ Phase 3: Static Verification, Acceptance & Audit Docs        │
│ - Pyright 0 errors across src & tests                        │
│ - Ruff 0 errors, formatted cleanly                           │
│ - Pytest 207+ passing (workbook, viewer, acceptance tests)   │
│ - tools/check_project.py PASS (184 Git objects unchanged)    │
│ - Update DW4 and DW5 Change Records                          │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. Verification & Validation Commands

All commands must be run from the repository root:

1. **Test Suite**:
   ```bash
   .venv/bin/python3 -m pytest -q
   ```
2. **Static Linting**:
   ```bash
   .venv/bin/ruff check src tests tools
   .venv/bin/ruff format --check src tests tools
   ```
3. **Type Checking**:
   ```bash
   .venv/bin/pyright
   ```
4. **Historical Baseline Integrity**:
   ```bash
   .venv/bin/python3 tools/check_project.py
   git diff --check
   ```

---

## 5. Next Immediate Action for the Next Context Window

The new context window should proceed directly with **Phase 1 execution**:
1. Edit `src/bh_sim/engine/runner.py`, `src/bh_sim/adapters/engineering.py`, `src/bh_sim/application/ports.py`, and `src/bh_sim/worker/entry.py` to propagate admitted `run_id` (Standards 3).
2. Edit `src/bh_sim/adapters/storage.py` to remove fabricated plot values (Standards 1) and verify staged artifacts on promotion (Standards 4).
3. Edit `src/bh_sim/application/services.py` to report persistence errors honestly (Standards 2), preserve worker context hash (Spec 3), and support cancelling active in-flight runs (Spec 2).
4. Edit `src/bh_sim/persistence/store.py` to persist attempt manifests to `attempts/{attempt_id}.json` and reload during index rebuild (Standards 5).
5. Edit `src/bh_sim/adapters/worker_supervisor.py` to enforce protocol metadata, session/sequence checks, and add stderr drain thread (Standards 6).
