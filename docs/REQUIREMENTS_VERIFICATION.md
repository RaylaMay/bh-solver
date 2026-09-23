# Requirements and Verification Matrix

Status values are `PLANNED`, `IMPLEMENTED`, `VERIFIED`, or `DEFERRED`. Architecture
items are `VERIFIED` when their named document exists and review records approval;
software items require automated or witnessed tests.

| ID | Requirement | Verification and evidence | Status |
|---|---|---|---|
| GATE-001 | Normative vocabulary is unambiguous. | Review [VOCABULARY.md](VOCABULARY.md); prohibited bare “valid” rule present. | IMPLEMENTED |
| GATE-002 | Context, components, runtime, state, and dependencies are defined. | Mermaid render and architecture review of [ARCHITECTURE.md](ARCHITECTURE.md). | IMPLEMENTED |
| GATE-003 | Units, schemas, solver, validity, versioning, licence, AI, UI, and storage choices are frozen. | ADR-001 through ADR-009 reviewed in [DECISIONS.md](DECISIONS.md). | IMPLEMENTED |
| GATE-004 | Public data and service boundaries are written. | Contract review plus generated-schema comparison against [CONTRACTS.md](CONTRACTS.md). | IMPLEMENTED |
| GATE-005 | Scientific model promotion is governed. | Lifecycle walkthrough using one prototype model. | IMPLEMENTED |
| GATE-006 | PFD behaviour is specified without equations in UI. | Wireframe and interaction review. | IMPLEMENTED |
| GATE-007 | Dependencies and data licences are separately controlled. | Licence review and SBOM comparison. | IMPLEMENTED |
| GATE-008 | Failures preserve immutable state and last valid result. | Failure table review and later fault-injection suite. | IMPLEMENTED |
| GATE-009 | Milestones have executable acceptance criteria. | Backlog review against first-slice handoff. | IMPLEMENTED |
| CORE-001 | API quantities serialize explicitly and incompatible dimensions fail. | Unit conversion, offset-temperature, serialization, and dimensional-error tests. | VERIFIED |
| CORE-002 | Case and revision JSON round-trip exactly and migrate by schema version. | Exact canonical round-trip and field rejection pass; migration remains a pre-beta fixture. | IMPLEMENTED |
| CORE-003 | Ports enforce kind, direction, multiplicity, and required connections. | Direction/kind and graph diagnostics pass; randomized property tests remain. | IMPLEMENTED |
| CORE-004 | Compiler reports DOF, order, and recycle groups deterministically. | Known graph/DOF fixtures pass; recycle solving is explicitly deferred. | IMPLEMENTED |
| CORE-005 | Acyclic flowsheet execution is deterministic. | Four-unit vertical-slice fixture passes with stable order and results. | VERIFIED |
| CORE-006 | Units close mass, components, and energy to declared tolerances. | First-slice mass/energy residuals and prototype hand fixtures pass; full catalogue V&V remains. | IMPLEMENTED |
| CORE-007 | Property backend can be swapped without unit or case change. | Polynomial provider substitution test passes unchanged case/unit contracts. | VERIFIED |
| CORE-008 | Convergence, closure, physical, and correlation statuses remain separate. | Contract truth table and valid/extrapolated/invalid property tests pass. | VERIFIED |
| CORE-009 | Solver failures return diagnostics and preserve the last-valid pointer. | Failed-run index test passes; browser retains an in-memory prior result but overwrites canvas overlays. No UI fallback test found; see DW0 GAP-03. Timeout/restart injection remains. | IMPLEMENTED |
| CORE-010 | Run artifacts and manifests are immutable and content-addressed. | Hash, corruption, duplicate and immutable-index tests pass; full environment manifest remains. | IMPLEMENTED |
| PFD-001 | User can add, move, connect, edit, and remove first-slice equipment. | Handlers inspected; TypeScript build passes. Available browser tests cover client/preflight only; no component or witnessed walkthrough record found. Connected-delete confirmation remains (DW0 GAP-04). | IMPLEMENTED |
| PFD-002 | Validate and Run are explicit, with stale validation blocking Run. | DW1 commands enforce service-retained validation against engineering and execution-context hashes. Legacy browser Run remains disabled only while busy, without that receipt guard; presentation moves still clear its validation (GAP-01). | IMPLEMENTED |
| PFD-003 | PFD and case round-trip without UI data entering engineering state. | DW1 separates versioned presentation and engineering identity and preserves legacy round-trip fixtures. Canonical case hashes intentionally retain names. Native viewport/routes, case-to-PFD export and full acceptance remain (GAP-02/GAP-07). | IMPLEMENTED |
| PFD-004 | Results overlay quantities, warnings, and all validity categories. | New DW1 run views expose all four statuses and typed quantities. Legacy HTTP/UI still omit run-level physical/correlation fields; visual matrix and complete display remain (GAP-03). | IMPLEMENTED |
| PFD-005 | Revision/run compare and last-valid fallback are visible. | DW1 services inspect/compare persisted runs and read last-valid selection. Browser has only in-memory prior-run string comparison; persisted picker, protected canvas and structural revision comparison remain (GAP-03/GAP-07). | IMPLEMENTED |
| AI-001 | Review profile produces approval-required ChangeSets only. | Approval-required and immutable-baseline tests pass. | VERIFIED |
| AI-002 | Exploration changes isolated drafts and records rationale/runs. | Limit and isolated-revision tests pass; iterative run ledger remains. | IMPLEMENTED |
| AI-003 | Narrative placeholders remain speculative and cannot be promoted. | Hidden-profile rejection and visible run-warning behaviour implemented. | IMPLEMENTED |
| BOUND-001 | UI, storage, and concrete adapters do not leak into kernel. | Static import-boundary tests pass. | VERIFIED |
| IND-001 | Industrial use remains explicitly excluded in current releases. | Package disclaimer is present. | IMPLEMENTED |

The architecture gate is not approved merely because `GATE-*` rows say
`IMPLEMENTED`; the steward must review them and change them to `VERIFIED`. New
requirements receive stable IDs and cannot replace failed evidence with prose.

## DW0 evidence correction

The 2026-09-10 [browser inventory](native/BROWSER_PARITY.md) and
[change record](native/CHANGE_RECORD.md) identify the current automated evidence
and source observations. The evidence corrections above do not mark any
requirement newly VERIFIED or remove its acceptance obligation. In particular,
five client/preflight tests are not component, accessibility or browser-parity
tests. Existing GATE approval records remain pending.

## Native requirements

Rayla May adopted these plan IDs with ADR-010 on 2026-09-11. DW1/DW2
advance only the implemented portions listed below; no full staged native
requirement is newly VERIFIED. See the
[native macOS witness](native/DW2_MACOS_VERIFICATION.md),
[DW2 evidence](native/DW2_CHANGE_RECORD.md),
[DW1 evidence](native/DW1_CHANGE_RECORD.md) and the
[DW0 package](native/DW0_REVIEW.md) for migration/rollback acceptance and staging.

| ID | Requirement | Evidence, remaining obligation and phase | Status |
|---|---|---|---|
| UIX-ARCH-001 | UIX and solver have no direct dependency in either direction. | DW1 neutral isolation plus DW2 recursive UIX checks and fresh-process New/Save/Open with scientific/FastAPI imports blocked; separate installed environments and worker execution remain, DW4/DW9 | IMPLEMENTED |
| UIX-ARCH-002 | Peers communicate only through versioned neutral contracts. | DW1 immutable codec and legacy golden fixtures; DW2 neutral gateway and fixed additive create/list fixtures; worker negotiation remains, DW4 | IMPLEMENTED |
| UIX-DIST-001 | Normal use needs no browser, terminal or manual server startup. | DW2 native developer launcher and macOS draft workflow witnessed without a terminal/server. Standalone packaging and clean-machine supported-platform workflow remain, DW9 | IMPLEMENTED |
| UIX-CMD-001 | Buttons, menus, hotkeys, palette, AI and CLI share application commands. | DW1 shared policy; DW2 reuse/enablement tests plus native keyboard draft and unavailable Run palette witness pass. AI authority integration remains, DW6 | IMPLEMENTED |
| UIX-PFD-001 | Native PFD satisfies browser parity and outstanding PFD requirements. | [DW3 editor](native/DW3_PFD.md), command/widget tests, measured 50-equipment raster target and scoped native witness. Worker/results, printing/export and full accessibility remain DW4/DW5/DW9. | IMPLEMENTED |
| UIX-PERF-001 | Select rendering from representative measured workloads. | DW3 selected raster from approved interaction workloads. DW3.1 measured 300 animation frames on the 50-equipment Cocoa scene: p95 paint 4.00 ms, p99 4.81 ms, zero intervals over 50 ms and correctness passed. Windows/x86_64 and Linux remain platform gates. | IMPLEMENTED |
| UIX-LAYER-001 | Users can manage colour-independent PFD layers and overlapping visual groups without changing engineering selection. | DW3.1 application/widget tests cover overlap, active halo, visibility, persistence, explicit member selection, patterns/tooltips and reduced motion; real result frames remain DW4/DW5. | IMPLEMENTED |
| UIX-WORKSPACE-001 | Flowsheet, Dynamics and Controls use independently versioned linked documents and unavailable workspaces state their gate. | DW3.1 manifest/control fixtures and disabled native switcher with M7/M9 explanations; dynamic/control document repositories and engines remain M7/M9. | IMPLEMENTED |
| UIX-EXT-001 | Extensions use versioned manifests, explicit execution tiers, permission admission and attributable unverified output. | DW3.1 golden manifest, policy rejection/crash/malformed-output tests, isolated protocol schema and proposed C ABI. Runtime loader, sandbox, signatures and SDK licence remain gated. | IMPLEMENTED |
| UIX-RUN-001 | Runs execute in a supervised independent worker. | Admission, crash/cancel/timeout, persistence fault and no-replay fixtures, DW4 | PLANNED |
| UIX-RUN-002 | Solver stepping and display refresh are independent. | Bounded queue tests and complete-artifact comparison with decimated display; binary format gate for dynamic arrays, DW4/M7 | PLANNED |
| UIX-A11Y-001 | Essential operations are keyboard reachable and colour independent. | DW2 offscreen checks plus native macOS New/Open/Save, unsaved Cancel, panel focus and layout recovery witnessed; dynamic status values now exposed in AX. Full VoiceOver/list announcements, scaling and PFD/results actions remain, DW2/DW3/DW5 | IMPLEMENTED |
| UIX-AI-001 | AI is an attributable participant with bounded authority. | Profile, stale-context, ChangeSet approval and budget tests, DW6/DW8 | PLANNED |
| UIX-AI-002 | Multiple participants preserve individual output and dissent. | Partial-failure, independent-output and non-consensus fixtures, DW8 | PLANNED |
| UIX-VOICE-001 | Optional conversation mode uses normal AI authority. | Voice-to-proposal test plus typed-only equivalence, DW7 | PLANNED |
| UIX-VOICE-002 | Transcript mode supports editing before send and retention control. | Original/edited/submitted text, explicit-send, deletion/export and provider/device-loss tests, DW7 | PLANNED |
| UIX-AUDIT-001 | Material AI actions link input, context, proposal, run and human disposition. | Reconstruction from retained artifacts without private reasoning, DW6–DW8 | PLANNED |
| UIX-DOC-001 | Material changes include editable intent/rationale and verification records. | DW0/DW1/DW2 Appendix A records and dated integrity checks; continuing review and CI enforcement where practical remain, all phases | IMPLEMENTED |
| UIX-DOC-002 | Numerical implementations link to cards, equations, units and V&V. | Existing model lifecycle and independent traceability review; DW work cannot grant promotion | PLANNED |

## DW3 evidence disposition — 2026-09-13

PFD-001 now has native application/widget tests for add/move/typed connect/input edit,
connected-delete confirmation, undo/redo and copy/paste, plus a
[scoped Mac walkthrough](native/DW3_NATIVE_VERIFICATION.md). PFD-003 has native
immutable save/reopen tests for layout, routes, viewport, preferences and original
input notation. [Public baseline transition](native/PUBLIC_BASELINE_TRANSITION.md)
qualifies historical evidence; no old hash is silently updated.

These rows remain IMPLEMENTED rather than globally VERIFIED: full PFD worker/run,
result overlays, compare, last-valid recovery, browser migration, accessibility and
export gates are still open. P-02's accepted initial timing targets pass for the
50-equipment raster reference, as scoped in the [benchmark](native/DW3_BENCHMARK.md).
Passing software checks is not scientific model approval.

## DW3.1 evidence disposition — 2026-09-14

The [DW3.1 change record](native/DW3_1_CHANGE_RECORD.md) records layers/groups,
workspace navigation and extension/control foundations. Focused automated checks
cover presentation-vs-engineering hashing, old PFD envelope defaults, group overlap
and deletion recovery, colour-independent status patterns, positive/reverse/zero/
stale states, reduced motion, manifest/version/permission rejection, extension
failure containment and fixed control/plugin fixtures.

The native Cocoa animation probe passes Rayla May's initial p95 33 ms target for
the 50-equipment reference scene. This evidence supports the current Mac renderer
choice. It does not verify solver telemetry, complete trajectories, a plugin
sandbox, numerical control behavior, propulsion physics or other platform classes.

## DW3.2 implementation evidence — 2026-09-14

| ID | Requirement | Evidence and remaining gate | Status |
|---|---|---|---|
| UIX-SHELL-002 | Contextual toolbar/optional ribbon, independent case tabs, accessible dock controls and workspace templates | DW3.2 widget tests and native layout captures; full assistive-technology witness and other platforms remain | IMPLEMENTED |
| UIX-HISTORY-001 | Continuous local recovery, immutable versions/snapshots, retained alternatives and persistent undo/redo | History fault/migration/dedup tests, native widget checks and structural comparison; long-history paging and authenticated collaboration remain separate | IMPLEMENTED |
| UIX-COMMAND-002 | In-app typed commands reuse GUI editing policy and confirmations | Closed-grammar, unit rejection, connected-delete, completion and command recall tests; arbitrary scripting excluded | IMPLEMENTED |
| UIX-COLLAB-001 | Simultaneous BH editing over LAN/VPN with actor-specific conflict-safe undo | Following DW3.3 protocol/failure-review gate; network editing remains disabled | PLANNED |

The [DW3.2 record](native/DW3_2_CHANGE_RECORD.md) separates native timing and widget
checks from unverified OS assistive-technology behaviour. No global PFD, scientific,
collaboration or release requirement becomes VERIFIED from these additions alone.

## DW6 prepared acceptance package — 2026-09-16

These bounded acceptance obligations refine existing IDs. Status remains PLANNED:
initial red tests and verifier self-tests do not establish implemented behavior.
The exact mandatory node inventory is frozen in the
[reviewer package](../handoffs/dw6/README.md).

| Existing requirements | Required acceptance evidence | Status |
|---|---|---|
| AI-001/003, UIX-AI-001 | Exact proposal approval, atomic application, profile propagation, Narrative non-promotion and forbidden mutation tests | PLANNED |
| UIX-AI-001, UIX-AUDIT-001 | Explicit context/feedback, isolated bounded exploration, durable reservations and no-replay fault tests | PLANNED |
| CORE-008/009/010, UIX-RUN-001 | Real child worker, artifact values/identity, four statuses and unchanged original last-valid selection | PLANNED |
| UIX-CMD-001, UIX-A11Y-001 | Production launcher/shared commands, keyboard workflow, spelling, responsive UI and macOS witness | PLANNED |
| UIX-ARCH-001/002, UIX-DOC-001 | Strict neutral types, legacy bytes, trusted package integrity, source identity and review record | PLANNED |

Actual package checks and expected pre-DW6 failures are recorded in the
[preparation record](native/DW6_HANDOFF_RECORD.md). Live-provider/native witness and
implementation review remain mandatory before accepting the eventual candidate.

## DW4/DW5 remediation evidence — 2026-09-23

CORE-009/010, PFD-002/004/005, UIX-RUN-001, UIX-ARCH-001/002 and UIX-DOC-001 receive
focused failure-path and real-child regression evidence in the
[remediation record](native/DW4_DW5_REMEDIATION_2026-09-23.md).
The six third-review findings are the bounded acceptance target. Full milestone
status is not promoted to VERIFIED: native/VoiceOver witness, UI-crash reconnect
ownership, hosted cross-platform CI and release acceptance remain separate gates.
