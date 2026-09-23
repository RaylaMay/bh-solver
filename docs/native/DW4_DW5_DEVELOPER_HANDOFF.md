# DW4/DW5 senior-developer handoff: worker, results and graphs

Date: 2026-09-14. Project owner and document author: **Rayla May**.
Preparation: Codex, following Rayla May's request for a reviewable development plan.
Status: **PROPOSED IMPLEMENTATION HANDOFF — NO RUNTIME CHANGE IN THIS WORK UNIT**.

Rayla May requests drag-and-drop PFD elements, whole-process and individual-unit
graphs, and explicit documentation and onward handoff instructions for DW4/DW5.
Review this package before implementation. It elaborates the existing DW4/DW5
scope; it does not freeze a worker protocol, approve new physics or enable dynamics.

## 1. Outcome and sequence

Deliver small, reviewable slices in this order:

| Slice | Result | Exit evidence |
|---|---|---|
| Intake | Reproduce the current workstation and identify current source/evidence | Baseline record, preserved working tree, discrepancy list |
| Editor follow-up | Drag equipment from the palette onto the PFD; preserve existing canvas movement and port gestures | Native gesture, keyboard alternative, history and recovery tests |
| DW4-A | Freeze worker, admission, lifecycle and persistence contracts | Reviewed protocol/state tables, versioned success/failure fixtures, migration decisions |
| DW4-B | Run the existing kernel in a supervised process through those contracts | Real child-process validation/run, identity parity and independent import checks |
| DW4-C | Contain cancellation, crashes, timeouts and persistence failures | Fault-injection matrix, durable reconciliation, no replay and last-valid tests |
| DW4-D | Connect native Validate/Run/Cancel and attempt inspection | Multi-tab, stale-response, keyboard and responsiveness evidence |
| DW5-A | Expose workbooks, result selectors, statuses and attributable PFD overlays | Artifact-to-view parity and complete status matrix |
| DW5-B | Provide docked/floating graphs and result comparison | Source/units/selection tests, exports, measured graph workloads |
| DW5-C | Complete draw-to-export acceptance and onward handoff | Native walkthrough, migration/rollback evidence, Appendix A records |

The editor follow-up can proceed independently of worker development. DW5 may
prototype against clearly identified fixtures while DW4 proceeds; production
result integration depends on DW4's accepted contracts. Keep LAN/VPN collaboration
in [DW3.3](DW3_3_COLLABORATION.md). Neither network editing nor its protocol becomes
a prerequisite for local DW4/DW5 work through this handoff.

## 2. Take over the actual repository

Read the current [documentation index](../README.md), [vocabulary](../VOCABULARY.md),
[architecture](../ARCHITECTURE.md), [ADRs](../DECISIONS.md),
[contracts](../CONTRACTS.md), [model lifecycle](../MODEL_LIFECYCLE.md),
[PFD specification](../PFD_SPECIFICATION.md), [failure policy](../FAILURE_RECOVERY.md),
[dependency register](../DEPENDENCY_REGISTER.md),
[verification matrix](../REQUIREMENTS_VERIFICATION.md), [milestones](../MILESTONES.md)
and [native plan](../NATIVE_WORKSTATION_ACTION_PLAN.md), including Appendix A.
Also read the [DW1 boundary](DW1_BOUNDARY.md), [browser parity inventory](BROWSER_PARITY.md),
[DW3.2 guide](DW3_2_WORKSTATION.md) and [DW3.2 change record](DW3_2_CHANGE_RECORD.md).
Current scoped implementation records qualify older historical descriptions.

Start with `git status --short`, the current branch/commit and the file tree. At
preparation, HEAD was `a0d3281`; substantial DW3/DW3.1/DW3.2 work remained modified
or untracked. Checking out that commit alone does **not** recover this workstation.
Preserve the complete working tree and user data before changing anything. Establish
an attributable source snapshot for the implementation review; do not reset, clean,
overwrite another developer's files or silently include unrelated changes in a commit.

Treat [the public transition record](PUBLIC_BASELINE_TRANSITION.md) and old evidence
as dated observations. Do not rewrite old hashes to make later edits pass an old
manifest. This planning work adds a README link, so the README hash in the DW3.2
manifest becomes historical; the implementation and captured evidence remain intact.
Record any additional differences before relying on that baseline.

The previous completed work unit recorded 173 Python tests, 13 native widget tests,
5 web tests, type/lint/build checks, and the accepted 50-equipment raster benchmark.
These are inherited results, not a fresh DW4 verification. Rerun relevant checks
against the exact incoming source and list skips and failures separately.

### Implementation map and verified gaps

| Area | Current evidence | Development instruction |
|---|---|---|
| Canvas gestures | [pfd_canvas.py](../../src/bh_sim/uix/pfd_canvas.py) implements equipment movement, snapped release, port-to-port connection and stream gestures | Extend these gestures; do not rebuild routing or bypass edit commands |
| Equipment palette | [pfd_editor.py](../../src/bh_sim/uix/pfd_editor.py) adds selected equipment through a button; the inspected UI has no palette drag/drop handlers | Add palette-to-canvas placement explicitly |
| Workstation/history | [workstation_editor.py](../../src/bh_sim/uix/workstation_editor.py), [history policy](../../src/bh_sim/application/history.py) and [journal adapter](../../src/bh_sim/adapters/history.py) provide durable edits and independent tabs | Preserve Save, undo, alternatives, input flushing and read-only historical views |
| Native calculations | [desktop_preview.py](../../src/bh_sim/adapters/desktop_preview.py) advertises calculation/result commands as unavailable | Compose supervised services behind the gateway; merely enabling buttons is insufficient |
| Run path | [services.py](../../src/bh_sim/application/services.py) and [ports.py](../../src/bh_sim/application/ports.py) execute synchronously; receipts belong to a service session | Introduce asynchronous admission/events without blocking Qt or changing legacy HTTP semantics silently |
| Run identity/lifecycle | [runner.py](../../src/bh_sim/engine/runner.py) allocates run IDs while constructing results; [core statuses](../../src/bh_sim/core/status.py) have no cancellation dimension | Allocate before execution and introduce a separate lifecycle; do not insert cancellation into convergence |
| Result projection | [engineering.py](../../src/bh_sim/adapters/engineering.py) exposes unit metrics, diagnostics and four run statuses | Add reviewed views for streams/ports, balances and available solver history; do not infer absent data |
| Persistence | [store.py](../../src/bh_sim/persistence/store.py) persists canonical results and queries last-valid data, but does not implement the full admission/reconciliation lifecycle | Add fault-tested admission, terminal records and index rebuild; preserve old artifacts |
| Identity mismatch risk | [PFD engineering hash](../../src/bh_sim/application/pfd.py) includes engineering subsystems; current `PreparedRevisionDto`/Run takes an older draft shape | Specify a native project/input identity binding; do not lose subsystem changes when issuing validation receipts |
| Last-valid semantics | The current SQL accepts correlation `VALID` **or** `EXTRAPOLATED` when the other acceptance dimensions pass | Expose that distinction; any policy change needs an explicit reviewed decision and compatibility tests |
| Dynamics | [transients.py](../../src/bh_sim/transients.py) is a prototype thermal-buffer calculation, not a governed flowsheet trajectory engine | Do not manufacture time histories from its scalar output or promote it through a UI feature |

## 3. Architectural and scientific constraints

- Keep Qt Widgets, the raster QGraphicsView canvas, neutral contracts and the
  existing scientific kernel. Keep React/FastAPI and compatibility fixtures.
- UIX owns gestures, layout and rendering. Application services own admission,
  receipts, case/result selection and persistence policy. The worker owns graph
  compilation, models, properties and numerical execution. Composition wires ports.
- UIX must not import engine/application/persistence implementations or perform
  engineering calculations. No Qt, Pint or numerical-library objects cross neutral
  contracts. Keep rendering adapters replaceable and dependencies explicitly reviewed.
- Preserve canonical artifact bytes and existing hash meanings. Distinguish the
  full checkpoint hash, native engineering hash, canonical case hash and execution
  context hash; name each scheme and its projection in the contract document.
- Validate and Run remain explicit. Engineering or execution-context changes stale
  the dependent receipt; movement, routing, group highlighting and graph navigation
  do not. Never replay Validate, Run, AI or extensions during recovery.
- Separate execution lifecycle, storage acknowledgement, convergence, closure,
  physical validity, correlation validity and scientific catalogue approval.
  A completed process or a passing test establishes none of the other dimensions.
- Keep reference models visibly `BLOCKED_EVIDENCE / TEST FIXTURE ONLY`. New equations,
  coefficients, properties, dynamics and model promotion require the normal evidence,
  model-card and independent V&V lifecycle. No arbitrary user-script execution here.

## 4. Editor follow-up: drag-and-drop PFD elements

Use the current command registry and `AddEquipmentEdit`, `MoveObjectsEdit` and
`ConnectPortsEdit`. Share placement/snap behaviour with existing interactions.

1. Drag a registered equipment item from Equipment onto the active editable PFD.
   Show a translucent placement preview, snap indication and valid/invalid cursor.
   Map viewport coordinates through the current zoom/pan transform. Create the
   unit and its declared ports only on a valid drop, with missing inputs still unset.
2. Use a bounded, versioned internal MIME payload containing catalogue identity,
   model ID/version and placement intent. Validate it against the current catalogue
   at drop time. Treat payloads as data: reject malformed, oversized, unknown or stale
   model references, foreign file/URL/script payloads and drops onto read-only views.
3. A valid drop creates one logical engineering edit and one durable history entry.
   Escape, leaving the canvas or rejecting the drop creates no unit and no history.
   A palette drag means a fresh unit; copy/paste retains its existing parameter rules.
4. Preserve dragging existing equipment, multi-selection and attached orthogonal
   streams. One completed group movement records one presentation edit. Check that
   group snapping preserves relative geometry instead of snapping members inconsistently.
   Keep current stream connection and branch gestures distinct from placement.
5. Do not connect equipment automatically merely because it overlaps a line or port.
   Retain explicit typed connection actions and adjustable snap settings. Dropping a
   free-standing material stream is not a valid new topology operation.
6. Keep visible Add/Connect controls and keyboard placement/movement alternatives.
   Route all methods through the same validation, naming and confirmation policy.
   Keep the originating case fixed during a gesture; cancel if that target disappears
   or becomes historical. A failed journal write must revert the preview and show why.

Verify scaled displays, zoom/pan, overlapping items, empty canvas, snapping disabled,
Escape/outside drop, catalogue changes, duplicate/drop delivery, multi-tab gestures,
connected movement, history classification and undo/redo after Save/restart. Preserve
the accepted 50-equipment p95 paint ≤33 ms and event-to-paint ≤50 ms targets.

## 5. DW4: supervised solver and resilient run control

### DW4-A — Freeze the protocol and ownership first

The following contract names describe proposals, not existing exported types.
Version them independently of `v1alpha` scientific artifacts and the old HTTP API.

| Contract family | Required content |
|---|---|
| Worker handshake/envelope | Protocol range/selected version, worker session ID, capabilities, actual model/property/solver versions, request/job/run IDs, sequence, payload tag and byte limits |
| Validation request/receipt | Exact source checkpoint and engineering identities, hash schemes, revision mappings, execution context, compiler diagnostics/DOF and issuing session |
| Admission/job | Actor, idempotency key, immutable source references and verified hashes, preallocated run ID, explicit configuration, backend identity and reproducibility manifest |
| Events/control | Accepted, running/progress, diagnostics, cancellation request/acknowledgement, terminal result/failure/cancellation/interruption and immutable artifact references |
| Attempt record | Admission and terminal lifecycle independent of scientific statuses; timestamps, reason, partial evidence, persistence state and links to exact inputs/results |
| Telemetry envelope | Source run/session, sequence, data time and its meaning, completeness/status metadata, bounded samples and dropped-display-sample counters |

Document framing, encoding, protocol mismatch behaviour, queue/message/storage
bounds, timeout/heartbeat clocks, event ordering, retries, cancellation races and
artifact-write ownership. Check partial reads, stdout contamination, malformed
JSON, duplicate/out-of-order/late frames and wrong-session/run messages with golden
fixtures before connecting the production UI. Reserve stdout exclusively for the
protocol if pipes are selected; send bounded sanitized diagnostics separately.

Recommended initial topology: one spawned local solver process with framed typed
messages over local pipes, supervised by an application-side adapter. Keep one
active solver job at a time initially; reject additional Run requests with a clear
busy diagnostic while permitting editing in all case tabs. This is a proposed
implementation default, not a performance or security-isolation claim. Review
process ownership explicitly: the accepted failure policy expects admitted work to
survive a UI crash. A UI-owned subprocess alone does not demonstrate that behaviour.
Specify a durable local supervisor/reconnection lifetime or obtain an explicit
failure-policy revision before choosing cancellation-on-UI-exit semantics.

### DW4-B — Bind the existing kernel without changing model equations

1. Add a worker entry point and a supervisor adapter. Keep heavy imports inside the
   worker. Launch it with explicit runtime/arguments and no shell or arbitrary
   executable selection from case data. Design process startup for macOS/arm64,
   Windows/x86_64 and later Linux; report which platforms actually ran.
2. Add quick-return command admission and typed event delivery through neutral ports.
   Drain messages without blocking the Qt event loop. Do not run the current
   synchronous `EngineeringPort.run` on the GUI thread or hold a global edit lock
   across solver work. Keep the legacy in-process adapter available for compatibility.
3. Persist and acknowledge the exact run input before dispatching execution. Bind the
   history entry/checkpoint, project engineering hash, canonical case/revision and
   worker context together. Preserve unit/subsystem/object-ID mappings. A run may
   seal immutable input artifacts without creating an implicit named Save version or
   clearing undo; document the difference from legacy `_execute`'s save-before-run.
4. Validate in the selected worker context. Reject stale receipts, changed models,
   missing backends and worker context mismatches before execution. Do not silently
   substitute a property package or accept a late receipt for a newer draft.
5. Extend execution plumbing so the admitted run ID survives success and all failure
   paths. Preserve existing callers and scientific bytes through explicit adapters
   and fixtures; do not replace an already-computed result's identity after the fact.
6. Record source/build identity, dependencies/data/model versions, explicit numerical
   settings, initialization, seeds where used, platform and timing in the manifest.
   Distinguish nondeterministic IDs/timestamps from deterministic engineering output.

### DW4-C — Persistence, cancellation and recovery

- Choose one authority for final artifact publication. Recommended: worker returns
  bounded output or a checked staged-artifact reference; the repository adapter
  verifies and publishes it before reporting durable completion. Do not accept an
  arbitrary worker-supplied path or permit two writers to race the last-valid index.
- Persist immutable admission/events/terminal records with rebuildable indexes.
  Reconcile duplicate requests to the same admitted job, including after a restart;
  changing the payload under the same request ID must reject. Lost replies never
  justify another solver execution. Do not resume a queued job on recovery as a Run.
- Cancellation first requests a documented safe boundary. If a backend cannot
  cooperate, enforce a bounded escalation and retain an interrupted/terminated
  outcome. Do not label a process kill as cooperative numerical cancellation.
- Define one authoritative terminal disposition for completion/cancellation/timeout
  races. Keep late messages as diagnostics without overwriting the winning outcome.
  An accepted job with no recovered terminal result becomes an auditable interruption
  once reconciliation determines the worker is gone; it does not disappear.
- Record partial diagnostics and any partial trajectory separately from accepted
  results. Preserve every known status without claiming unknown work completed.
- Commit canonical result bytes before indexing and last-valid selection. Distinguish
  calculation completion from durable storage. Retry a failed write with the same
  content identity, never by recalculating. If storage itself is unavailable, show
  the unpersisted outcome and retain recoverable evidence without a false saved message.
- Rebuild corrupt/missing indexes from verified canonical records. Test orphaned
  artifacts and interrupted publication on copied stores; preserve the originals.
- Bound telemetry separately from terminal/control events. Coalesce/drop display
  samples with counters; never discard terminal events or substitute telemetry for
  a full artifact. UI refresh settings must not control numerical step sizes.

Large dynamic arrays require ADR-009's separate immutable binary-artifact decision.
Specify dtype/endian, dimensions/units, ordering, compression, hash scope, atomic
publication, chunk completeness, corruption handling and migration before adoption.
DW4 can complete with bounded steady-state artifacts; it must state that trajectory
execution/storage remains unavailable where those contracts are not approved.

### DW4-D — Native command integration

Expose Validate, Run, Cancel and attempt status through menus, toolbar, ribbon,
palette and the in-app command line using shared authority rules. Persist the run's
source identity independently of the active tab. Edits during a run create new
document history and stale the displayed source comparison; they never mutate the
running input. A late result belongs to its original case even after a tab switch.

Keep attempt history separate from document undo. Undoing an engineering edit must
not cancel, delete or replay a run. Recovery can restore result references and
attempt information, but must require a new explicit validation for the current
worker session. Connect selected artifact references when creating **new** named
snapshots; retain all existing snapshots unchanged.

DW4 closes only with real child-process evidence for admission, validation, run,
cancel, timeout, worker loss, UI loss/reconnection, malformed traffic and failed
artifact/index writes. Confirm that every failure preserves the case, responsive
editing and the previous last-valid result. Do not mark the gate from mocks alone.

## 6. DW5: workbooks, graph views and result inspection

### DW5-A — Build a complete result read model

Expose available stream/port quantities, equipment inputs/results, mass/component/
energy balances, convergence/residual history, diagnostics and manifest/provenance
through versioned neutral read contracts. Reuse existing metrics; extend the
projection where canonical artifacts contain more information. Missing metrics,
unsupported quantities and unchecked statuses remain explicit, never zero-filled.

Keep separate selectors for the active attempt, the displayed result and the
application-selected last-valid result. Failed attempts remain inspectable; never
replace the acceptable canvas implicitly with failure data. When a user explicitly
views stale, failed, extrapolated or unconverged data, carry those labels into
workbooks, overlays, graphs and exports. State the source revision/run everywhere.
Do not silently change the current extrapolated-result acceptance query; review
the policy question in Section 9 and add a four-status truth table.

Map PFD objects to artifact object/port IDs in the application adapter. Unknown,
renamed or deleted current objects must not attach old values to another unit.
Allow inspecting the artifact's historical flowsheet context read-only. Keep
result comparison distinct from DW3.2 structural document comparison. Begin with
same-case stable-ID result comparison; cross-case correspondence requires a
reviewed mapping, not matching display names.

### DW5-B — One graph viewer, two locations

Provide a **Graphs** dock and an explicit **Open in window** action using the same
read-only plot model. Use a non-modal floating window so the engineer can keep
working. Suggested visible entry points: the inspector's **Plot…** action, the
equipment/stream context menu, a workbook metric action and the bottom panel strip.
Keep all of them keyboard reachable and registered with command search/CLI.

- **Whole-process view:** collect explicitly selected equipment/stream series in
  one dashboard. Start with selected inlet/outlet temperatures, pressure, mass flow
  or duty where the artifact supplies them. Do not invent a plant-average temperature,
  total duty or balance from arbitrary displayed rows; aggregates need a defined
  application/study result with units and accounting boundaries.
- **Individual unit:** identify the unit, port/location and variable precisely.
  A unit can have inlet, outlet, wall and inventory temperatures; show only the
  variables its model actually records. Permit multiple named traces and a table
  of the exact samples used for the plot.
- **Source binding:** pin a graph to a run/artifact by default. Offer an explicit
  follow-selection/live-source mode with a visible source label. Pinning a floating
  plot must survive later selection changes and case switching. Close subscriptions
  on closing the view; closing a plot never cancels its run.
- **Presentation:** legend, axis quantity and unit, cursor/sample readout, pan/zoom,
  reset, show/hide trace, accessible colours/patterns, light/dark/high contrast and
  reduced motion. Use separate panels/axes for incompatible dimensions. Apply case
  units and overrides through the existing quantity-conversion port; precision only
  changes formatting. Default to exact-sample readouts and no smoothing.
- **Persistence:** store plot definitions/source references separately from numeric
  artifacts. Personal dock position, viewport and temporary trace visibility stay
  out of document undo. An explicitly saved shared plot definition is presentation
  metadata; it cannot stale engineering validation. Old snapshots stay immutable.
- **Exports:** separate plotted-image/report export from source-sample export.
  Include artifact hash, run/revision, variable/port IDs, units, statuses and any
  display decimation in provenance. Mark displayed/decimated samples as such; a
  full-source export must read the full artifact. Rendering/export failures must
  not rerun the solver or alter stored engineering values.

### What “temperature versus time” can mean

| Data available | Permitted view | Prohibited inference |
|---|---|---|
| One steady-state run | Values/table or a clearly labelled comparison of quantities | A physical time history made by repeating or interpolating one result |
| Numerical solver history | Residual versus iteration, if recorded | Calling iteration count or wall-clock runtime process time |
| Several saved runs | Explicit run/revision comparison; study coordinates only when recorded | Treating independent runs as a dynamic trajectory |
| Complete governed trajectory | Temperature versus recorded simulation time for each identified location | Changing time steps or calculating missing values in the UI |
| Live decimated telemetry | Clearly labelled provisional preview with source, time meaning and gaps | Claiming the preview is the complete persisted trajectory |

**DW5 delivers the viewer and typed series boundary, not a new dynamic engine.**
Test time plots with a bounded, labelled golden trajectory fixture. Enable real
T-versus-time only when a supported artifact producer, trajectory persistence
contract and scientific model exist. Until then, explain the missing capability
and M7 dependency. Do not wire `ThermalBuffer` into a fabricated sampled curve.

For future live plots, distinguish simulation time from capture/job time. Preserve
time order, event identity and pre/post-event samples. Reject malformed ordering or
non-finite time; mark unavailable values as gaps, keep reverse/zero values and
independent status metadata. Never bridge failed/missing intervals silently.
Different runs may have different time grids: overlay their recorded coordinates;
interpolation or numerical differences need a separate explicit analysis contract.

### Proposed graph contracts and renderer gate

Review neutral types for `SeriesReference`, `SeriesDescriptor`, `PlotDefinition`,
`SeriesRequest`, `SeriesChunk` and export provenance. Names remain provisional.
Carry schema version, case/revision/run and artifact identity/hash, object/port/
quantity identity, axis meaning/units, exact sample indices/time range, status,
completeness and decimation metadata. Requests must support bounded ranges/pages
and cancellation. UI plot definitions contain no embedded authoritative arrays.
The repository/series adapter verifies hashes and returns bounded neutral data;
the renderer owns only drawing and viewport transforms.

Recommended first evaluation: Matplotlib's QtAgg integration for artifact inspection
and report export, because `pyproject.toml` already lists Matplotlib in the optional
analysis extra. Its official documentation describes Qt/PySide embedding and static
output backends. This is a candidate, not a selected desktop dependency or measured
live-plot capability. [Matplotlib backend documentation](https://matplotlib.org/stable/users/explain/figure/backends.html)

Before adoption, inspect the exact version and dependency/licence closure, isolate
the renderer behind a presentation port, and benchmark it beside the PFD. Keep
scientific imports out of UIX and standard-library-only neutral contracts; do not
relax boundary tests wholesale to admit a plotting package. If a renderer needs a
different dependency boundary, propose that change explicitly. Compare an alternative
only if evidence shows the first candidate misses the reviewed graph workload.

### DW5-C — Complete workflow and acceptance

Witness palette drop → typed connect → edit inputs → Validate → Run → inspect
workbook/overlays → open unit graph → pin a floating graph → compare saved runs →
create snapshot → restart/reopen → inspect/export without a browser or terminal.
Include a deliberately incomplete case, failed solve, lost worker, failed export
and failed write. Preserve history and the last-valid result throughout.

Repeat the accepted 50-equipment PFD benchmark with a graph open and telemetry
active. Keep p95 paint ≤33 ms and event-to-paint ≤50 ms; report p99, CPU, memory,
queue growth, dropped display samples and correctness. Define additional graph
budgets before measuring; a suggested initial stress fixture is eight traces with
10,000 source samples each, one dock and one floating view. That fixture is a
proposal, not an accepted performance target or a restriction on future models.

## 7. Verification and requirement traceability

| Requirement references | Minimum added evidence |
|---|---|
| PFD-001/003, UIX-HISTORY-001 | Palette drop/move/connect parity, one-edit gestures, history across restart, missing-member recovery and no engineering change from movement |
| PFD-002, UIX-CMD-001, UIX-RUN-001 | Exact-context receipts, durable admission, all command surfaces, stale responses, multi-tab isolation and no implicit validation/run/save-version |
| CORE-009/010, UIX-RUN-001 | Crash/cancel/timeout/completion races, missing backend, duplicate requests, corrupt frames, failed writes/index rebuild and last-valid preservation |
| UIX-RUN-002, UIX-PERF-001 | Bounded telemetry, non-lossy terminal delivery, source trajectory identity independent of refresh/decimation, PFD-plus-plot benchmark |
| PFD-004/005, CORE-001/008 | Artifact-to-view quantities/units, offset temperatures, four statuses, failed/stale view labels, result comparison and export provenance |
| UIX-A11Y-001, UIX-SHELL-002 | Keyboard alternatives, dock/float restore, focus order, themes/reduced motion and native macOS assistive-technology witness |
| UIX-ARCH-001/002, UIX-DOC-001 | Separate dependency environments, version/migration fixtures, Appendix A records and complete onward handoff |

Propose stable requirements for palette placement and graph source/series fidelity
in the matrix before implementation; keep them `PLANNED` until evidence exists.
Do not change broader requirements to `VERIFIED` from a document or an isolated mock.
Keep the existing test suites and add focused worker, lifecycle, series, graph and
native acceptance suites with explicit failure injection. Use a separate verifier
for any scientific implementation change; that reviewer reports defects rather
than becoming the sole implementer and verifier.

Run at intake and after relevant implementation changes:

```sh
QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q
.venv/bin/ruff check src tests tools
.venv/bin/ruff format --check src tests tools
.venv/bin/pyright --pythonpath .venv/bin/python
.venv/bin/python tools/check_project.py
git diff --check
uv build --offline
```

Run `npm test`, `npm run lint` and `npm run build` from `web`. Run native widget
tests and the workstation benchmark with `QT_QPA_PLATFORM=cocoa` on macOS using
isolated test data. Record exact commands for new suites. The commands above use
the current macOS environment; adapt invocation syntax explicitly for Windows.
Missing optional dependencies or offline build inputs are reported skips/blocks,
never a passing check. CI configuration is not evidence that GitHub jobs ran.

## 8. Mandatory documentation and onward handoff

For **each slice**, provide an editable Appendix A change record covering:

- Objective and exact instruction from Rayla May; requirement/ADR/model/defect links.
- Scope, boundaries, assumptions, verified facts and unresolved evidence gaps.
- Selected design, concise rationale, alternatives and tradeoffs.
- Files/contracts changed and schema, migration, dependency, licence, security,
  privacy and scientific impacts.
- Exact test commands, environment/source hashes, observed outcomes, failures,
  skips and checks not run with reasons. Preserve initial failures and fixes.
- Risks, known limitations, rollback steps, remaining development and decisions.

Update the documentation with the implementation rather than after it:

| Document | Required update |
|---|---|
| `ARCHITECTURE.md` | Actual process ownership, inbound dependencies, run/event and result/plot ports |
| `CONTRACTS.md` | Versioned envelopes, hash projections, state transitions, series semantics and old-reader behaviour |
| `DECISIONS.md` | New accepted decisions or clearly proposed alternatives; preserve prior ADR bodies |
| `FAILURE_RECOVERY.md` | Crash/reconnect, cancellation races, queue/write/index/export failures and no-replay recovery |
| `PFD_SPECIFICATION.md` | Drag/drop, graph entry points, units/status/source presentation and keyboard workflow |
| `DEPENDENCY_REGISTER.md` | Exact worker/renderer packages, optionality, licences and distribution consequences |
| `REQUIREMENTS_VERIFICATION.md` | Requirement-to-test/artifact links and qualified status changes |
| `MILESTONES.md`, native plan and `README.md` | Delivered slices, remaining gates and current handoff links |

Document public modules, commands, ports and non-obvious functions: purpose,
inputs/outputs, units, side effects, failure modes and contract/model references.
Explain reasons for tolerances, sampling, limits and workarounds. Use named,
sourced/configured values. Do not replace explicit engineering rationale with
hidden model reasoning or a claim that AI-generated code is self-verifying.

At DW4 completion, hand DW5 a frozen protocol/schema package, runnable worker fixture,
capability inventory, artifact/attempt samples, migration and fault matrix, native
integration instructions, source hashes and rollback procedure. A senior reviewer
must be able to validate/run/cancel/fail/recover without reconstructing undocumented
protocol choices. Keep pending graph/trajectory work separate from DW4 completion.

At DW5 completion, hand the next developer a current architecture map, reproducible
launch/check commands, field/series catalogue, graph adapter guide, saved project and
snapshot fixtures, source-to-result mapping, compatibility report and native evidence.
List unfinished M7 trajectory production, DW6–DW8 AI/HAZOP, DW3.3 collaboration and
DW9 distribution work individually, with prerequisites. Do not imply a GUI graph
viewer completes a dynamic engine, HAZOP programme or release qualification.

Every delivery states the exact source/branch state, existing user-change overlap,
files owned by this slice, remaining failures, next bounded action and responsible
review role. Store portable evidence without usernames, credentials or private case
content. Rollback disables the new worker/plot composition and opens the retained
editor; preserve new artifacts and journals even when old clients cannot consume them.

## 9. Decisions and suggested defaults

| Topic | Recommendation / required review |
|---|---|
| Dock versus popup | Implement both through one model; use the side dock by default and a pinned non-modal window on explicit request. No further owner decision blocks this. |
| “Whole process” graphs | Start with chosen unit/stream traces. Ask Rayla May only if a specific aggregate is required; define its engineering accounting before implementation. |
| Real time-domain calculations | Keep M7 gated. If Rayla May wants T-versus-time production before M7, obtain an explicit bounded dynamics/model programme rather than expanding DW5 silently. |
| Worker after UI exit | Steward must resolve crash survival, intentional Quit and reconnect ownership against the accepted failure policy before DW4-A freezes. Ask Rayla May if changing the promised behaviour is necessary. |
| Extrapolated last-valid results | Preserve and label the current behaviour initially. Ask Rayla May/steward before changing it to an exclusively in-domain result policy. |
| Worker/plot limits and renderer | Senior developer proposes measured, configurable defaults; steward reviews protocol, dependency and licence impact. Graph stress targets remain proposals until reviewed. |
| Platforms | Develop for macOS/arm64 first, with Windows/x86_64 and Linux-compatible boundaries. Report native platforms actually tested; minimum supported versions remain a later release decision. |

## 10. Receiving-developer starting instruction

> Review this handoff against the current repository and preserve all existing
> work. Report the actual baseline, discrepancies and any decision required for
> the first slice. Start with the bounded editor follow-up and DW4-A contract
> review; do not restart DW0–DW3.2 or replace the scientific kernel. Implement
> accepted slices through shared commands and ports, record Appendix A evidence
> for each slice, and leave an explicit reproducible handoff for the next developer.
> Keep dynamic calculations, network collaboration, AI/HAZOP execution and browser
> retirement behind their separate gates. Distinguish proposals, implemented
> behaviour, measured results and unverified expectations throughout.

Preparation scope and checks appear in the [planning change record](DW4_DW5_HANDOFF_RECORD.md).
