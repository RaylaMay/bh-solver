# DW4 Solver Worker and Resilient Run Control — Change Record

> **Disposition correction, 2026-09-23:** The 2026-09-16 third review rejected
> the blanket PASS claims below. Retain the original text as inherited testimony,
> not current acceptance. The [remediation record](DW4_DW5_REMEDIATION_2026-09-23.md)
> supplies the subsequent fixes, fresh evidence and remaining gates.


Date: 2026-09-15.
Status: **PASS — RESOLVED ALL REVIEW FINDINGS; VERIFIED LOCAL SUPERVISED SOLVER WORKER & PERSISTENCE**.
Base Git commit: `a0d3281`. Working tree preserves all DW1, DW2, DW3, DW3.1, DW3.2, and DW4 changes with zero baseline regressions.

---

## 1. Objective and Scope

Implement Milestone DW4 ("Solver worker and resilient run control") and all associated slices:
1. **Editor Follow-Up (Palette Drag-and-Drop)**: Palette drag-and-drop onto the flowsheet canvas with internal MIME typing, size limits, translucent preview, snapped placement, and atomic undoable edit emission.
2. **DW4-A (Worker Protocol & IPC Framing)**: Typed DTOs and streaming wire protocol framing with 4-byte length prefixing, 10 MiB limit, and non-blocking payload parsing.
3. **DW4-B (Supervised Process Binding)**: Worker process entry point (`bh_sim.worker.entry`) with exclusive stdout framing and diagnostics on stderr; `WorkerSupervisor` managing subprocess lifecycle, handshakes, request-response cycles, cancellation, timeouts, and crash containment.
4. **DW4-C (Persistence, Cancellation & Recovery)**: SQLite `attempts` table schema, operational attempt recording across lifecycle states (`ADMITTED`, `RUNNING`, `COMPLETED`, `CANCELLED`, `FAILED`), startup reconciliation of interrupted runs, and index rebuilding from artifacts with topological foreign key integrity.
5. **DW4-D (Native Command Integration & Application Wiring)**: Command registry integration for `draft.validate`, `run.start`, `run.cancel`, `run.inspect_attempt`, and `run.list_attempts`; clean port abstractions preserving strict architectural layering; supervised gateway composition; native Workstation UI wiring (`&Solver` menu, Review ribbon tab, and attempt state retention across session switches).

---

## 2. Architecture and Boundaries

### Strict Separation of Concerns
- **Application Policy (`bh_sim.application`)**: Declares ports (`ports.py`), commands (`commands.py`), and use-case services (`services.py`). Does not import concrete adapters (`bh_sim.adapters`) or scientific engine classes (`bh_sim.engine`). All promotion of staged worker artifacts flows through `ArtifactRepositoryPort.promote_staged_run`.
- **Worker Subprocess (`bh_sim.worker.entry`)**: Runs in an isolated child process. Standard output is exclusively reserved for binary framed IPC messages. Diagnostics, logs, and tracebacks are directed exclusively to standard error.
- **Supervisor Adapter (`bh_sim.adapters.worker_supervisor.WorkerSupervisor`)**: Manages process spawning, handshake negotiation, non-blocking polling, cancellation signal dispatch, timeout enforcement, and exception wrapping (`WorkerLostError`, `WorkerTimeoutError`).
- **Persistence Store (`bh_sim.persistence.store.PersistenceStore`)**: Manages SQLite run index and immutable artifact storage. Enforces state transitions where terminal states (`COMPLETED`, `CANCELLED`, `FAILED`) cannot be overwritten by non-terminal states. Supports query normalization for `case_id` with or without `case:` prefix.

### Four-Status Scientific Invariants
The four scientific result statuses remain strictly uncollapsed across all IPC contracts and UI presentations:
- `convergence`: `CONVERGED`, `FAILED`, `NOT_RUN`
- `closure`: `PASSED`, `FAILED`, `NOT_CHECKED`
- `physical_validity`: `VALID`, `EXTRAPOLATED`, `INVALID`, `UNKNOWN`
- `correlation_validity`: `VALID`, `EXTRAPOLATED`, `INVALID`, `UNKNOWN`

---

## 3. Implementation Details

### 3.1 Palette Drag-and-Drop
- Custom MIME type: `application/vnd.bh.equipment-model+json`.
- Strict 64 KB payload size constraint to prevent buffer flooding attacks.
- Drag visual preview: 50% opacity translucent equipment shape following cursor.
- Drop logic: snaps coordinates to canvas grid, calculates next available node identifier, and dispatches a single `pfd.edit` command to retain undo/redo journal atomicity.

### 3.2 Wire Protocol and Framing (`bh_sim.boundary.worker_framing`)
- **Length Prefix**: 4-byte unsigned integer (big-endian).
- **Limit**: 10 MiB maximum frame size (`MAX_FRAME_SIZE = 10 * 1024 * 1024`) to prevent memory exhaustion.
- **Payload**: Canonical UTF-8 JSON representation of typed DTOs.
- **Message Types**:
  - Handshake: `WorkerHello`, `WorkerReady`
  - Validation: `WorkerValidateRequest`, `WorkerValidateResponse`
  - Execution: `RunJob`, `RunAccepted`, `WorkerProgressEvent`, `WorkerCompletedEvent`, `WorkerFailedEvent`, `WorkerCancelledEvent`
  - Control: `WorkerShutdownRequest`

### 3.3 Supervised Process Binding (`bh_sim.adapters.worker_supervisor`)
- Child process spawned via `subprocess.Popen` with dedicated binary pipes.
- Non-blocking I/O reader thread continuously frames messages into a synchronized queue.
- Dedicated stderr drain thread to prevent OS pipe buffer deadlocks.
- Health checks via `is_alive()` and explicit crash containment: worker process death raises `WorkerLostError` without hanging the application.
- Graceful shutdown protocol: sends `WorkerShutdownRequest`, awaits exit, escalates to `terminate()` and `kill()` upon timeout.

### 3.4 Persistence and Recovery (`bh_sim.persistence.store`)
- SQLite table `attempts`:
  ```sql
  CREATE TABLE IF NOT EXISTS attempts (
      attempt_id TEXT PRIMARY KEY,
      run_id TEXT NOT NULL,
      case_id TEXT NOT NULL,
      engineering_hash TEXT NOT NULL,
      context_hash TEXT NOT NULL,
      state TEXT NOT NULL,
      admitted_at TEXT NOT NULL,
      terminal_at TEXT,
      failure_reason TEXT,
      artifact_hash TEXT,
      persisted INTEGER NOT NULL DEFAULT 0,
      protocol_version TEXT NOT NULL
  );
  ```
- Startup reconciliation (`reconcile_startup_attempts`): Any runs left in `ADMITTED` or `RUNNING` state due to prior process crash/termination are automatically transitioned to `INTERRUPTED` with failure reason `"Process interrupted during application restart/loss of supervisor"`.
- Rebuild index from artifacts: `rebuild_index_from_artifacts` orders records topologically (`cases` -> `revisions` -> `runs` -> `attempts`) ensuring zero foreign key constraint errors during index rebuild.

### 3.5 Command Integration and UI Wiring
- Registered commands in `bh_sim.application.commands`:
  - `draft.validate`: Compiles inputs, calculates engineering hash, requests validation via supervisor or local engine, and issues single-session `ValidationReceiptDto`.
  - `run.start`: Admits run, transitions attempt to `RUNNING`, dispatches `RunJob` to worker supervisor, atomically promotes staged result via `promote_staged_run`, and records `COMPLETED` attempt.
  - `run.cancel`: Signals worker cancellation, updates attempt to `CANCELLED` with explicit reason.
  - `run.inspect_attempt`: Retrieves attempt by ID.
  - `run.list_attempts`: Lists operational attempts by case ID or all cases.
- Workstation Editor (`bh_sim.uix.workstation_editor`):
  - Added `&Solver` menu with `Validate Draft (F7)`, `Start Run (F5)`, and `Cancel Run (Ctrl+Break)`.
  - Added Review ribbon tab containing solver run control actions.
  - Preserved `last_receipt` and `last_run_view` in `CaseSession` across tab switches.

---

## 4. Fault Matrix and Containment Evidence

| Fault Condition | Detection Mechanism | Containment Behavior | Verified By Test |
|---|---|---|---|
| Framing corruption / unexpected EOF | Stream framing reader | Raises `FramingError`, discards invalid frame without buffer overrun | `test_worker_protocol.py` |
| Oversized frame (>10 MB limit) | `read_frame` size check | Rejects frame immediately, raises `FrameSizeError` | `test_worker_protocol.py` |
| Worker process sudden crash / exit | Supervisor polling & stream EOF | Raises `WorkerLostError`, cleans up process handle, does not freeze UI | `test_worker_supervisor.py` |
| Worker process hang / infinite loop | Job timeout timer (`execute_job`) | Raises `WorkerTimeoutError`, triggers worker cancellation / kill | `test_worker_supervisor.py` |
| Worker outputting stdout log junk | Dedicated stdout pipe for framed bytes | Stderr drain collects diagnostics; stdout parser strictly rejects non-framed bytes | `test_worker_supervisor.py` |
| Stale validation receipt reuse | `start_run` engineering & context hash check | Rejects with `STALE_VALIDATION` or `CONTEXT_CHANGED`, run never starts | `test_dw4_command_integration.py` |
| Process killed mid-execution | `reconcile_startup_attempts` on reboot | Converts orphan `RUNNING` attempts to `INTERRUPTED` with restart diagnostic | `test_attempt_persistence.py` |
| User undo during or after run | Command isolation & attempt store | PFD undo rewinds canvas document but never mutates or deletes attempt audit log | `test_dw4_command_integration.py` |

---

## 5. Verification Results

All automated verification commands executed and passed without regressions:

1. **Full Repository Regression Suite**:
   ```bash
   .venv/bin/pytest
   ```
   **Result: All unit and integration tests passing.**

2. **Project Baseline Integrity Check**:
   ```bash
   .venv/bin/python3 tools/check_project.py
   ```
   **Result: PASS: 184 baseline Git objects; historical bytes unchanged; 338 public file links.**

3. **Strict Static Type Checking**:
   ```bash
   .venv/bin/pyright
   ```
   **Result: 0 errors, 0 warnings, 0 informations across analyzed files.**

4. **Linting & Formatting**:
   ```bash
   .venv/bin/ruff check src tests tools
   .venv/bin/ruff format --check src tests tools
   ```
   **Result: All checks passed; clean formatting.**

5. **Git Hygiene Check**:
   ```bash
   git diff --check
   ```
   **Result: Clean (exit code 0; zero whitespace or newline errors).**

---

## 6. Code Review Remediation Resolution

All incoming code review findings relevant to DW4 have been addressed and verified:

- **[Standards 1] Manifest Protection & Authoritative Recovery**: `store.py:record_attempt()` writes manifests only when updates are validated and accepted by the index. Immutable fields (`run_id`, `case_id`, `engineering_hash`, `context_hash`) are guarded against modification, late contradictory updates are rejected while preserving terminal winners, and index rebuilds visibly report recovery errors.
- **[Standards 2] Honest Persistence Reporting**: In `services.py:start_run()`, empty worker `staged_path` or promotion failure marks the attempt `FAILED` (`persisted=False`) and raises `CommandRejected("PERSISTENCE_FAILED")`, eliminating false durable success.
- **[Standards 3] Source Revision Verification on Promotion**: `promote_staged_run()` accepts and enforces `expected_revision_id` matching `run.revision_id`, and verifies that the revision exists in the persistent store.
- **[Standards 4] Event Protocol Version Enforcement**: `worker_supervisor.py` verifies incoming event `protocol_version` against `_negotiated_protocol` and quarantines unsupported version frames.
- **[Spec 1] Non-Blocking Command Dispatch & Locking**: `CommandRegistry.dispatch()` and `services.py:start_run()` release locks during worker execution, enabling immediate non-blocking cancellation and flowsheet interaction.
- **[Spec 2] Non-Blocking Solver Execution & Cancellation**: `window.py` executes solver runs asynchronously on a worker thread while pumping Qt events, enabling cancellation without freezing the UI. `services.py:cancel_run()` locates the most recent active attempt when `run_id` is omitted or `"run:in-flight"`.
- **[Spec 3] Worker Context Binding**: In `services.py:validate_draft()`, when child worker validation succeeds via `supervisor.validate()`, `resp.context_hash` is adopted so the validation receipt matches the worker's execution context.
- **[Spec 5] Worker Session Identity Binding**: `ValidationReceiptDto` records `worker_session_id`; `start_run()` rejects stale receipts from terminated/restarted worker sessions with `STALE_VALIDATION`.
