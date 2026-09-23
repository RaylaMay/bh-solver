> User-supplied harness material; claims are not reviewer approval. Local paths normalized.

# Implementation Plan — DW4/DW5 Second Code Review Remediation

Date: 2026-09-16.  
Author: Senior Software Engineer (Chemical Engineering domain context).  
Skill: `engineering-continuity` (BH solver profile).  
Target Disposition: Transition from **FAIL** to **PASS** with full verification.

---

## 1. Executive Summary & Continuity Baseline

### 1.1 Project & Directory Confinement
- **Project Root**: `$SOURCE`
- **Ownership**: Rayla May owns the project. Concept-development status without industrial or safety-critical approval.
- **Strict Boundary**: All edits, tests, and documentation reside strictly within this repository. No external dependencies or binary downloads.
- **Numerical Truth**: The calculation engine / kernel owns numerical truth. Zero synthetic points, zero fake duties/temperatures.
- **Four Status Dimensions**: `convergence`, `closure`, `physical_validity`, `correlation_validity` remain distinct and uncollapsed.
- **Historical Git Objects**: 184 baseline Git objects (338 public links) via `.venv/bin/python3 tools/check_project.py` must remain PASS.

---

## 2. Review Findings & Remediation Inventory

The second code review by Codex resulted in a **FAIL** disposition across 9 substantive findings (4 Standards, 5 Spec) and diff hygiene / documentation alignment items.

### 2.1 Standards Findings (4 items: 4 P1)

#### [Standards 1] (P1 — Rejected updates overwrite authoritative attempt evidence)
- **Target File**: `src/bh_sim/persistence/store.py:236–285, 467–485`
- **Problem**: `store.py:record_attempt()` wrote the attempt manifest to disk (`_write_attempt_manifest`) *before* calling `self.index.index_attempt()`. When `index_attempt()` rejected an update (due to conflicting immutable inputs or late attempt after terminal state was locked in), the disk manifest had already been corrupted by the rejected data. Purging and rebuilding SQLite restored the corrupted data.
- **Remediation**:
  1. Refactor `RunIndex.index_attempt(attempt) -> tuple[RunAttemptRecord, bool]`:
     - Validate immutable inputs (`run_id`, `case_id`, `engineering_hash`, `context_hash`) against SQLite first. If mismatched, raise `ValueError` without writing anything to disk.
     - If existing attempt is already terminal (`COMPLETED`, `FAILED`, `CANCELLED`, `INTERRUPTED`, `TIMED_OUT`):
       - If `attempt.persisted` is changing to True: update `persisted = 1`, return `(winning_record_with_persisted, True)`.
       - Otherwise: reject/ignore late message; return `(existing_authoritative_winner, False)`.
     - If existing attempt is non-terminal (`ADMITTED`, `RUNNING`): update SQLite, return `(attempt, True)`.
     - If new attempt: insert into SQLite, return `(attempt, True)`.
  2. In `PersistenceStore.record_attempt(attempt)`:
     - `winner, updated = self.index.index_attempt(attempt)`
     - Only call `self._write_attempt_manifest(winner)` if `updated` is True.
     - Return `winner`.
  3. In `PersistenceStore.rebuild_index_from_artifacts()`:
     - Log and expose any attempt manifest parse or index conflicts as visible recovery failures rather than silently swallowing with `except Exception: pass`.

#### [Standards 2] (P1 — Empty artifact paths still produce false durable success)
- **Target File**: `src/bh_sim/application/services.py:258–317`
- **Problem**: When a worker completed, if `terminal.staged_path` was empty (`""`) or None, the code fell through `if view is None:` to construct an empty `RunViewDto` and marked `persisted=True`, resulting in a `COMPLETED` attempt with zero stored runs.
- **Remediation**:
  1. In `services.py:start_run()`:
     - If `not terminal.staged_path`: do NOT construct a phantom success view. Transition attempt to `state="FAILED", persisted=False, failure_reason="Worker completed without staged artifact path"`, record attempt, and raise `CommandRejected("PERSISTENCE_FAILED", ...)`.
     - If promotion via `promote_staged_run` fails: transition attempt to `state="FAILED", persisted=False, failure_reason=f"Promotion failed: {error}"`, record attempt, and raise `CommandRejected("PERSISTENCE_FAILED", ...)`.
     - Only mark `state="COMPLETED", persisted=True` when `promote_staged_run` returns a valid, promoted `RunViewDto`.

#### [Standards 3] (P1 — Promotion accepts results from the wrong source revision)
- **Target Files**:
  - `src/bh_sim/adapters/storage.py:123–156`
  - `src/bh_sim/application/ports.py:69–77`
  - `src/bh_sim/application/services.py:260–267`
  - `src/bh_sim/adapters/desktop_preview.py:83–91`
  - `tests/test_application.py:424–433`
- **Problem**: `promote_staged_run` checked `expected_run_id` and `expected_case_id`, but never checked `expected_revision_id`. A revision-2 job accepted a correctly hashed revision-1 artifact containing 350 K results when run_id matched.
- **Remediation**:
  1. Update `promote_staged_run` signature in `ports.py`, `storage.py`, `desktop_preview.py`, `test_application.py` to accept `expected_revision_id: str | None = None`.
  2. In `storage.py:promote_staged_run`:
     - If `expected_revision_id is not None`: verify `str(run.revision_id) == str(expected_revision_id)`, raising `ValueError` on mismatch.
     - If `run.revision_id` is present, verify that revision exists in `self.store.load_revision(run.revision_id)`.
  3. In `services.py:start_run()`:
     - Pass `expected_revision_id=str(job.revision_id) if job.revision_id is not None else None` into `promote_staged_run`.

#### [Standards 4] (P1 — Negotiated protocol version is not enforced on events)
- **Target File**: `src/bh_sim/adapters/worker_supervisor.py:320–375`
- **Problem**: `_reader_loop` checked `worker_session_id` and sequence numbers, but never verified `protocol_version`. Events carrying `unsupported-v99` were admitted directly to the active job queue.
- **Remediation**:
  1. Store `self._negotiated_protocol = c.WORKER_PROTOCOL_VERSION` upon successful handshake.
  2. In `_reader_loop`:
     - Extract `proto = getattr(msg, "protocol_version", None)`.
     - If `proto is not None and proto != self._negotiated_protocol`: quarantine the frame, write an explicit warning to `sys.stderr`, and `continue` without routing to `_active_jobs` or `_pending_responses`.

---

### 2.2 Spec Findings (5 items: 4 P1, 1 P2)

#### [Spec 1] (P1 — Cancel and editing still wait for execution)
- **Target Files**:
  - `src/bh_sim/application/commands.py:124–193`
  - `src/bh_sim/application/services.py:165–240, 383–415`
  - `src/bh_sim/uix/window.py:495–535`
- **Problem**:
  1. `CommandRegistry.dispatch()` held `self._lock` throughout `self._invoke(request)`.
  2. `services.py:start_run()` held `self._lock` throughout `self.supervisor.execute_job(job)`.
  3. Concurrent Cancel or edit requests blocked on these locks until the solve completed.
  4. `window.py:_worker` touched Qt UI widgets from a non-GUI background thread.
- **Remediation**:
  1. In `commands.py:dispatch()`:
     - Use `self._lock` only to check deduplication and register the request.
     - Release `self._lock` during `self._invoke(request)`.
     - Re-acquire `self._lock` to store the outcome in `self._completed`.
  2. In `services.py:start_run()`:
     - Phase 1 (under lock): validate receipt, save draft, prepare, record ADMITTED, record RUNNING, set `self._active_run_id = run_id`.
     - Phase 2 (OUTSIDE lock): invoke `self.supervisor.execute_job(job)` or `self.engineering.run(...)`.
     - Phase 3 (under lock): promote staged run, record terminal attempt, clear `self._active_run_id`.
  3. In `services.py:cancel_run()`:
     - With `self._lock` released during Phase 2, `cancel_run` executes immediately, signals `self.supervisor.cancel(target_run_id)`, transitions attempt to `CANCELLED`, and returns.
  4. In `window.py`:
     - Background thread dispatches without touching UI. Outcome is received and processed strictly on the Qt main GUI thread.

#### [Spec 2] (P1 — Route completion to the originating case)
- **Target File**: `src/bh_sim/uix/workstation_editor.py:1454–1470`
- **Problem**: On run completion, `run_current()` updated `self.session` (whichever session was active after event pumping). Starting Case A and switching tabs to Case B during execution caused Case A's run, workbook, and overlays to be attached to Case B!
- **Remediation**:
  1. At solve dispatch in `run_current()`, capture `originating_id = self.active_id` and `target_session = self.sessions.get(originating_id)`.
  2. On completion, route `RunViewDto`, workbook, and overlays specifically to `target_session`:
     - `target_session.last_run_view = last_run_view`
     - Query workbook and overlays for `originating_id` and store them in `target_session.workbook` and `target_session.overlays`.
  3. If `self.active_id == originating_id`: refresh the active canvas and workbook view.
  4. If `self.active_id != originating_id` (tab switch occurred): do NOT touch the active canvas or workbook of the other case. The background session is updated cleanly and will display its results when switched back.

#### [Spec 3] (P1 — Preserve last-valid display after scientific failure)
- **Target File**: `src/bh_sim/uix/workstation_editor.py:1454–1491`
- **Problem**: When a run failed scientifically (e.g. `convergence == "FAILED"`, `closure == "FAILED"`, or `physical_validity == "INVALID"`), `workstation_editor.py` loaded the failed overlays onto the canvas and replaced the workbook. The acceptance predicate also omitted closure and correlation checks.
- **Remediation**:
  1. Define full four-status validity predicate:
     - `convergence == "CONVERGED"`
     - `closure == "PASSED"`
     - `physical_validity == "VALID"`
     - `correlation_validity in ("VALID", "EXTRAPOLATED")`
  2. On run completion:
     - If all 4 statuses pass: update `session.last_valid_run_view`, `session.last_valid_workbook`, `session.last_valid_overlays`.
     - If any status fails: retain previous `session.last_valid_overlays` on the canvas. Update `session.last_run_view` and display a clear scientific failure banner in the status bar/banner, but do NOT replace canvas overlays with the failed state.
  3. Allow inspecting the failed run's workbook diagnostics while keeping the last-valid physical state visible on canvas.

#### [Spec 4] (P2 — Invalidate workstation receipt after engineering edits)
- **Target Files**:
  - `src/bh_sim/uix/window.py:619–635`
  - `src/bh_sim/uix/workstation_editor.py:480–515, 560–605`
- **Problem**: `window.py:refresh()` checked `has_valid_receipt` without comparing current engineering identity. Workstation history `_adopt()` restored `session.last_receipt`. Changing duty in the inspector or undoing/redoing left Run enabled.
- **Remediation**:
  1. In `CaseSession`: track `validated_engineering_hash: str | None`. When a receipt is stored, record `session.validated_engineering_hash = receipt.engineering_hash`.
  2. In `workstation_editor.py`:
     - In `_adopt(state)`: if the head history entry is classified as `"engineering"` or its `after_engineering_hash != session.validated_engineering_hash`: clear `session.last_receipt = None` and `self.last_receipt = None`.
     - In `schedule_input_edit()` and inspector parameter change handlers: immediately clear `session.last_receipt = None` and `self.last_receipt = None`.
     - In `undo()` and `redo()`: if the affected entry is an engineering edit, invalidate `last_receipt`.
  3. In `window.py:has_valid_receipt`:
     - Check `self.last_receipt is not None`, `self.last_receipt.draft_id == self.current.draft_id`, and `self.last_receipt.validation.valid`.
     - If in workstation editor, verify that the current session's head engineering hash matches `self.last_receipt.engineering_hash`. If mismatched, `has_valid_receipt = False` and `run.start` is disabled.

#### [Spec 5] (P1 — Bind receipts to the current worker session)
- **Target Files**:
  - `src/bh_sim/boundary/contracts.py:255–268`
  - `src/bh_sim/application/services.py:130–185`
- **Problem**: `services.py:173–176` reused `receipt.execution_context_hash` without checking the issuing worker session ID. When a worker process restarted, the new worker session had a different session ID, but `start_run()` accepted the old receipt from the dead worker.
- **Remediation**:
  1. Add `worker_session_id: str | None = None` to `ValidationReceiptDto`.
  2. In `services.py:validate_draft()`: when supervised, record `worker_session_id = getattr(self.supervisor, "session_id", None)` in the receipt.
  3. In `services.py:start_run()`: when `is_supervised`, verify `receipt.worker_session_id == getattr(self.supervisor, "session_id", None)`. If mismatched (worker restarted), reject with `CommandRejected("STALE_VALIDATION", "Worker session expired; revalidation required")`.

---

### 2.3 Documentation & Diff Hygiene
1. Remove extra blank lines at EOF in `docs/native/DW4_CHANGE_RECORD.md` and `docs/native/DW5_CHANGE_RECORD.md` so `git diff --check` passes cleanly.
2. In `docs/native/DW4_CHANGE_RECORD.md`:
   - Correct wire protocol description: 4-byte length prefix, 10 MiB frame limit, no CRC.
   - Correct startup reconciliation description: transitions orphan attempts to `INTERRUPTED`.
   - Update verification records to reflect accurate, attributable test evidence.
3. In `docs/native/DW5_CHANGE_RECORD.md`:
   - Update change record to describe four-status last-valid overlay retention and multi-tab session routing.

---

## 3. Proposed Changes Grouped by Component

### Core Boundary & Protocol (`bh_sim.boundary`)
#### [MODIFY] [contracts.py](src/bh_sim/boundary/contracts.py)
- Add `worker_session_id: str | None = None` to `ValidationReceiptDto`.

### Persistence & Storage (`bh_sim.persistence`, `bh_sim.adapters.storage`)
#### [MODIFY] [store.py](src/bh_sim/persistence/store.py)
- Refactor `RunIndex.index_attempt()` to validate immutable inputs, preserve terminal winning disposition, and return `(authoritative_record, was_updated)`.
- In `PersistenceStore.record_attempt()`, write manifest to disk ONLY if `was_updated` is True.
- Make recovery failures visible in `rebuild_index_from_artifacts()`.
#### [MODIFY] [storage.py](src/bh_sim/adapters/storage.py)
- In `promote_staged_run()`, accept and verify `expected_revision_id`. Verify revision exists in store.
#### [MODIFY] [ports.py](src/bh_sim/application/ports.py)
- Update `ArtifactRepositoryPort.promote_staged_run` signature with `expected_revision_id: str | None = None`.
#### [MODIFY] [desktop_preview.py](src/bh_sim/adapters/desktop_preview.py)
- Update `promote_staged_run` signature.

### Application Services & Commands (`bh_sim.application`)
#### [MODIFY] [services.py](src/bh_sim/application/services.py)
- Bind `ValidationReceiptDto` to `worker_session_id`. Enforce session check in `start_run()`.
- Release `self._lock` during solver execution (`execute_job` / `engineering.run`).
- In `cancel_run()`, cancel immediately without blocking on running solve.
- Treat empty `staged_path` as `PERSISTENCE_FAILED` (mark attempt FAILED, `persisted=False`).
- Pass `expected_revision_id` to `promote_staged_run`.
#### [MODIFY] [commands.py](src/bh_sim/application/commands.py)
- Release `self._lock` during `self._invoke(request)` in `CommandRegistry.dispatch()`.

### Worker Supervisor (`bh_sim.adapters.worker_supervisor`)
#### [MODIFY] [worker_supervisor.py](src/bh_sim/adapters/worker_supervisor.py)
- Record `_negotiated_protocol` during handshake.
- In `_reader_loop`, enforce that any event carrying `protocol_version` matches `_negotiated_protocol`; quarantine on mismatch.

### Native Workstation UI (`bh_sim.uix`)
#### [MODIFY] [window.py](src/bh_sim/uix/window.py)
- Ensure background solver thread does not touch Qt UI widgets.
- In `has_valid_receipt`, verify current engineering identity against `last_receipt.engineering_hash`.
#### [MODIFY] [workstation_editor.py](src/bh_sim/uix/workstation_editor.py)
- Capture `originating_id` at solve dispatch; route completion strictly to `target_session`.
- Enforce four-status validity predicate (`convergence`, `closure`, `physical_validity`, `correlation_validity`).
- On scientific failure, retain `last_valid_overlays` on canvas and display diagnostic failure banner.
- Invalidate `session.last_receipt` on any engineering edit, inspector edit, or undo/redo.

### Documentation & Change Records
#### [MODIFY] [DW4_CHANGE_RECORD.md](docs/native/DW4_CHANGE_RECORD.md)
- Remove EOF blank line. Correct wire protocol and startup reconciliation descriptions.
#### [MODIFY] [DW5_CHANGE_RECORD.md](docs/native/DW5_CHANGE_RECORD.md)
- Remove EOF blank line. Align with four-status last-valid policy and multi-case session routing.

### Tests
#### [MODIFY] [test_attempt_persistence.py](tests/test_attempt_persistence.py)
- Add tests for manifest protection against rejected updates and authoritative terminal index rebuilding.
#### [MODIFY] [test_worker_supervisor.py](tests/test_worker_supervisor.py)
- Add test for quarantining frames with mismatched `protocol_version`.
#### [MODIFY] [test_application.py](tests/test_application.py)
- Add tests for empty `staged_path` persistence failure, revision mismatch in promotion, and worker session invalidation.
#### [MODIFY] [test_workstation_editor.py](tests/test_workstation_editor.py)
- Add tests for tab switching during execution, last-valid preservation on scientific failure, and receipt invalidation on duty changes/history edits.

---

## 4. Verification Plan

### Automated Tests
1. **Full Pytest Suite**:
   ```bash
   PYTHONPATH=src .venv/bin/python3 -m pytest -q
   ```
2. **Static Lint & Format**:
   ```bash
   .venv/bin/ruff check src tests tools
   .venv/bin/ruff format --check src tests tools
   ```
3. **Static Type Checking**:
   ```bash
   PYTHONPATH=src .venv/bin/pyright --pythonpath .venv/bin/python
   ```
4. **Historical Baseline Integrity**:
   ```bash
   .venv/bin/python3 tools/check_project.py
   git diff --check
   ```
5. **Specific Probe Scenarios**:
   - Manifest protection against late FAILED and changed run_id.
   - Index wipe and rebuild: restores winning COMPLETED state.
   - Worker completion with empty `staged_path` rejected with `PERSISTENCE_FAILED`.
   - Promotion with mismatched revision rejected.
   - Protocol frame with `unsupported-v99` quarantined.
   - Cancel during execution dispatches immediately and cancels attempt.
   - Solve started on Tab A, switch to Tab B: results route to Tab A, Tab B remains untouched.
   - Valid solve followed by scientific failure: canvas preserves last-valid overlays.
   - Changing duty or undo/redo invalidates receipt and disables Run.
   - Worker restart invalidates prior receipt (`STALE_VALIDATION`).

### Acceptance Criteria
- All 9 review findings resolved.
- 0 Ruff errors, 0 Pyright errors across 101+ files.
- All unit & acceptance tests passing.
- `tools/check_project.py` PASS (184 Git objects, historical bytes unchanged, 338 public links).
- `git diff --check` passes with 0 whitespace warnings.
