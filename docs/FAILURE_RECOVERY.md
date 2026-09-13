# Failure Containment and Recovery

Failures are converted to typed diagnostics at the nearest declared boundary. A
run coordinator allocates the run ID before evaluation so all post-allocation
failures can be recorded. No recovery path may invent engineering values.

| Failure | Boundary and action | Preserved state | Retry policy |
|---|---|---|---|
| Malformed schema or incompatible units | API validation rejects before revision creation | Submitted payload in client; prior revision | User correction only |
| Incomplete flowsheet, port conflict, or nonzero DOF | Graph compiler returns blocking diagnostics; no solver call | Draft and previous results | Revalidate after edit |
| Property backend missing | Thermo adapter returns capability error and affected unit stops | Case, inputs, prior results, failed run | Retry after same backend/version restored; never silently substitute |
| Property request out of domain | Unit returns domain diagnostic; stop unless card and case both permit extrapolation | All inputs and diagnostics | Explicit opt-in or input/model change |
| Unit evaluation exception/non-finite value | Coordinator catches at unit boundary, identifies unit/input, marks downstream `NOT_RUN` | Completed independent evaluations and trace | Retry only from immutable revision; no partial mutation |
| Solver nonconvergence/infeasible/timeout | Solver returns status, residual/iteration history, and best vector labelled unusable | Failed run and last-valid pointer | User may alter initialization/settings in new revision/run |
| Closure failure after convergence | Run fails acceptance; retain computed state for diagnosis | Full result; last-valid pointer unchanged | Correct model/case and create new run |
| Cancellation | Coordinator stops at safe evaluation boundary and marks `CANCELLED` | Manifest and completed diagnostics | New run ID required |
| JSON artifact write failure | Write temporary sibling, fsync, atomic rename; do not update SQLite index until success | In-memory result and existing artifacts | Retry write with same content hash |
| SQLite unavailable/corrupt | Treat index as rebuildable; do not claim save if JSON is absent | Canonical JSON artifacts | Rebuild index by scanning and verifying hashes |
| Report/plot failure | Output adapter fails independently | Calculation artifact | Retry rendering without rerun |
| API/server loss | UI enters disconnected state; disables Validate/Run | Local unsaved edits and server artifacts | Reconnect, compare base hash, explicit resubmit |
| UI crash | Kernel/run continues independently when already accepted | Server revision and run; local recovery draft if available | Restore presentation state; never replay Run automatically |
| Invalid or stale AI ChangeSet | Reject forbidden path/base hash before applying | Base and prior revisions | AI/user creates a new ChangeSet against current base |
| AI explanation contradicts result | Display kernel result as authority; flag explanation, preserve prompt/output audit | Run artifact | Regenerate explanation only; never rerun silently |

## Transaction boundaries

1. Revision save validates schema, writes canonical JSON atomically, verifies its
   hash, then commits the SQLite index row.
2. Run creation writes an initial manifest, evaluates without mutating case state,
   writes the terminal artifact atomically, then updates the index.
3. The last-valid pointer advances only in the same index transaction that records
   an immutable, hash-verified successful result.
4. Startup scans incomplete temporary files and index rows. It may remove only
   verified temporary files; it reports orphaned valid artifacts for index rebuild.

## Diagnostic minimum

Every failure diagnostic includes stable code, severity, human message, run or
revision ID, affected unit/field when known, boundary, original exception class
without secret data, and corrective action. Debug traces are opt-in artifacts and
must not expose credentials, proprietary datasets, or unrestricted local paths.

## Degraded operation

Ephemeral calculation is allowed only when the user explicitly chooses it before
the run and accepts that it is not saved. It returns a downloadable artifact and
cannot advance the last-valid pointer or claim reproducibility. Industrial profile
disallows ephemeral runs.

## DW0 proposed desktop and worker additions

Status: target requirements accepted with ADR-010 on 2026-09-11; exact
DW4/DW6/DW7 protocol contracts and implementation remain pending.
These rows add required target behaviour; they do not certify current recovery.

| Failure | Target containment and retained evidence | Recovery |
|---|---|---|
| Worker crash or heartbeat/IPC loss | Supervisor retains admitted run identity, immutable source and received diagnostics; terminal interruption/fault record cannot advance last-valid selection | Reconcile artifacts by identity/hash; restart worker capability negotiation, never replay Run |
| Worker timeout or cancellation | Distinct lifecycle state with safe-boundary cancellation; preserve partial diagnostics separately from acceptable results | New explicit run only; define completion/cancellation race fixtures before implementation |
| Malformed, incompatible, duplicate or late message | Reject/quarantine by version, session, run ID and sequence; bound queues/frames; preserve sanitized fault | Reconcile current job; no speculative completion or silent version/backend substitution |
| Artifact commit/index failure after computation | Separate calculation completion from durable-save acknowledgement; preserve source and previous last-valid result | Reconcile exact artifact/hash; no rerun as a save retry |
| Desktop crash or damaged workspace layout | Application artifacts retained; only schema-checked presentation recovery is restored | Reset layout independently; no automatic validation, run or approval |
| AI participant/provider failure | Retain each completed contribution, individual failure and bounded-resource ledger; no invented consensus | Explicit retry within approved limits and context identity |
| Microphone denial, device loss or audio cancellation | Visible capture state and retention disposition; typed input stays capable | Explicit device/capture retry; no unnoticed recording or upload |
| Transcription failure or correction | Preserve original/edited/submitted distinctions where retention is enabled; no implicit AI send | User edits or explicitly retries with a permitted provider; no provider fallback without authorization |

Current implementation gaps include run IDs allocated at result construction,
absence of a pre-run manifest/worker lifecycle, non-atomic browser draft writes and
no automatic index-rebuild path. The [parity inventory](native/BROWSER_PARITY.md)
assigns these follow-up work; existing passing persistence tests do not establish
crash recovery or cancellation support.
