# DW1 review test batch — documentation-derived specification

Date: **2026-09-16**. Prepared by: **Codex**, at Rayla May's request.
Status: **PROPOSED TEST SPECIFICATION; NOT EXECUTED**.

This batch defines acceptance tests and code-review checks before examining the
implementation. It tests whether DW1 delivers its documented neutral application
boundary while preserving scientific authority, immutable evidence and legacy
compatibility. It is not a finding that the implementation is defective or correct.

Read with the [rework batch](DW1_REWORK_BATCH.md) and
[preparation/change record](DW1_REVIEW_PREPARATION_RECORD.md).
The numbered test IDs below are local review identifiers, not new requirements.
All **80 test families** initially have status **NOT RUN**; parameterized cases
must be reported individually. No executable test harness is delivered in this round.

## 1. Authority and exact review target

The target for the next round is the current checkout's DW1 responsibilities,
including their later modifications. Intake found `main` at
`a0d3281aee909914cdf82a6f35ef4550f0b29604` with substantial unstaged/untracked work.
The [intake manifest](evidence/dw1-review-plan-2026-09-16/intake.json) records
selected file hashes and full Git status. A commit alone does not identify this
checkout. Reconcile live changes and create a recoverable isolated snapshot before
execution. Hashes in this preparation record were collected without inspecting code.

Authority keys used by the test tables:

| Key | Source and applicable scope |
|---|---|
| B | [DW1 boundary](DW1_BOUNDARY.md), the eight synchronous commands, receipts, hash projection, compatibility and explicit limitations |
| C | [Public contracts](../CONTRACTS.md), quantities, statuses, immutable artifacts, HTTP behavior and versioning |
| A | [Architecture](../ARCHITECTURE.md) and [ADR-001–010](../DECISIONS.md), dependency direction, scientific authority, compatibility and storage |
| P | [PFD specification](../PFD_SPECIFICATION.md), explicit actions and engineering/presentation distinction; only DW1 service obligations apply here |
| F | [Failure policy](../FAILURE_RECOVERY.md), typed failures and preservation, qualified by B's explicit DW1 limits |
| V | [Verification matrix](../REQUIREMENTS_VERIFICATION.md), existing requirement IDs and evidence limitations |
| N | [Native action plan](../NATIVE_WORKSTATION_ACTION_PLAN.md), Sections 2, 11, 12/DW1, 14 and Appendix A |
| H | [DW1 change record](DW1_CHANGE_RECORD.md), inherited implementation claims and original review scope; not a current test oracle by itself |
| G | [Fixture README](../../tests/fixtures/dw1/README.md), frozen regression traces and exact normalization rules |
| Q | [Public baseline transition](PUBLIC_BASELINE_TRANSITION.md), sanitized historical evidence qualification |
| L | [Model lifecycle](../MODEL_LIFECYCLE.md), separate scientific verification and approval |

DW0's [owner disposition](DW0_OWNER_DISPOSITION.md) already authorizes the neutral
extraction; do not reopen platform, licence-route or DW0 approval. The architecture
steward resolves actual incompatible-contract proposals. Old broad target wording
does not override B's explicit staged limitations.

### Included and deferred behavior

| Included in this DW1 review | Separate gate; do not invent a DW1 implementation obligation |
|---|---|
| Neutral DTOs, strict codec, registry, ports and thin adapters | Worker framing, progress, cancellation, durable admission and worker-session receipts: DW4 |
| Exact engineering identity, process-local receipts and in-process context/snapshot checks | Full distributed race guarantees, durable exactly-once delivery and multi-user authentication |
| Save/open/validate/run ordering; stored inspection, comparison and last-valid policy | Native result selectors, graphs, responsiveness and tab routing: DW4/DW5 |
| Legacy HTTP/CLI/canonical compatibility | Fixing legacy browser enablement/overlay gaps by silently breaking its API |
| Explicit persistence failure acknowledgement and preservation of old artifacts | New full manifest, startup recovery/index rebuild, binary trajectory formats: later artifact/worker gates |
| Regression protection for later additive contracts touching DW1 | Implementing DW2–DW6 features, networking, extension execution, AI or speech |
| Reference-fixture mapping and unchanged scientific outputs | New equations, coefficients, catalogue promotion or engineering-design validation |

The [DW4/DW5 rereview](DW4_DW5_REREVIEW_2026-09-16.md) concerns a sibling candidate,
not this checkout. Its findings motivate integration checks but are not DW1 defect
evidence. Do not import that candidate or assume its code is present.

Concurrent documentation added ADR-012 and DW6's explicitly authorized bounded
exploration target during preparation. Those additions preserve canonical bytes
and require accepted worker/results integration; they do not change DW1's
process-local receipt or legacy compatibility oracles. This batch's no-implicit-Run
checks concern DW1 draft/recovery operations, not a prohibition on a later separately
authorized exploration plan. Reconcile any further authority changes at R0.

## 2. Harness and oracle design

Use independent layers of evidence:

1. **Neutral contract tests:** direct public construction and serialized requests.
   Exercise both; codec rejection alone does not protect in-process callers.
2. **Application tests with recording ports:** record ordered prepare, compile,
   context, draft-write, input-write, evaluate, artifact-write and read calls.
   Snapshot arguments so later mutation cannot falsify the call history.
3. **Concrete adapter tests:** temporary synthetic repositories and documented
   reference fixtures. Compare immutable files/hashes and index references before
   and after faults. No real project store or proprietary case is an input.
4. **Compatibility tests:** frozen pre-DW1 golden data, exact command fixtures,
   retained HTTP requests and CLI subprocesses. Never regenerate expected output
   from the candidate to make it pass.
5. **Source and dependency review:** inspect transitive imports, responsibilities,
   public types/docstrings and all ways to reach execution. Static checks alone
   cannot establish runtime isolation or absence of scientific policy in UI/API.

Derive the engineering-hash oracle independently from the normative canonical
projection: remove only top-level `title` and each unit's `name`, preserve every
other field and array order, serialize using the specified canonical convention,
then SHA-256. Do not call the production engineering-hash helper to compute the
expected result. For canonical artifacts, frozen bytes are the oracle; they are
not regenerated through the current serializer.

Use fixed synthetic case/draft identities, recorded random seeds, bounded generated
inputs and deterministic synchronization hooks. Context changes must be injected
at named execution points, not made dependent on sleeps. Synthetic numeric values
are test stimuli, never newly sourced engineering coefficients. Numerical comparisons
use fixture/card tolerances where applicable; bytes, IDs, hashes, units, status
enums, call counts and acceptance predicates are exact. Do not invent tolerances
or loosen comparison after seeing a failure.

Every negative admission test asserts **zero draft/input/result writes and zero
evaluations**, unless it is explicitly the post-persistence context race described
in B. Reads and preparation needed to reject a request may occur. Every read-only
test asserts **zero writes, validations and evaluations**. Count calls as well as
checking the returned diagnostic. Positive controls prove the harness can reach
the behavior that negative tests claim to prevent.

## 3. Ordered test families

Risk labels order work; they do not waive acceptance obligations:
**critical** protects execution authority, scientific identity or immutable evidence;
**high** protects compatibility, isolation and reproducibility;
**review** requires human assessment as well as automated checks.

### Batch A — baseline and evidence integrity (high)

Trace: UIX-DOC-001, CORE-002/010; B/G/H/Q/N.

| ID | Stimulus / method | Required observation and evidence |
|---|---|---|
| DW1-T001 | Freeze branch/HEAD, staged and unstaged changes, untracked relevant files, fixture hashes, dependencies and runtime versions before review. | Recoverable candidate snapshot plus manifest; no unrelated edit removed. Record exact paths included/excluded and receipt/service composition under test. |
| DW1-T002 | Reconcile the 2026-09-11 verification record and 2026-09-13 public transition with today's bytes. | Historical results remain attributed to their source; changed historical hashes are qualified, not repaired or called current regressions solely from mismatch. |
| DW1-T003 | Authenticate every frozen HTTP, CLI, public-export and canonical fixture against available manifests/public Git evidence. | Missing or conflicting provenance yields EVIDENCE GAP, never a fresh golden generated by the candidate. Distinguish sanitized implementation hashes from surviving fixture-byte evidence. |
| DW1-T004 | Run existing focused tests and standard checks on the frozen unmodified candidate; capture collection and exit codes. | Baseline failures and skips recorded before repair; no blanket PASS based on process exit or inherited test counts. |

### Batch B — neutral contracts and strict serialization (high; rejection paths critical)

Trace: UIX-ARCH-002, CORE-001/002/008, BOUND-001; B/C/A.

| ID | Stimulus / method | Required observation and evidence |
|---|---|---|
| DW1-T005 | Round-trip every DW1 request, result, terminal event and nested DTO; compare existing command fixtures byte-for-byte where canonical encoding is specified. | Stable versions, tags, fields, quantities and identities; no scientific/runtime objects in the wire form. Public type inventory states any missing fixture. |
| DW1-T006 | Attempt assignment to DTOs and mutation through nested collections, extension mappings, caller-owned input aliases and returned results. | Published values remain unchanged or invalid construction is rejected; frozen outer objects alone are insufficient. Serialization/hashes before and after agree. |
| DW1-T007 | Send absent, malformed or unsupported command schema versions and use HTTP/artifact versions in their place. | Explicit rejection before side effects; no automatic version fallback or interpretation as a different envelope. |
| DW1-T008 | Send unknown discriminator/command, unknown domain fields, missing required fields, wrong nested type and wrong parameter type for a known command. | Fail closed with typed boundary diagnostics; no handler invocation. Declared presentation extension members remain allowed. |
| DW1-T009 | Submit NaN, both infinities, overflow numeric literals, booleans in numeric positions, numeric strings and null where numbers are required, through JSON and direct construction. | Invalid representations never reach scientific ports or canonical artifacts; huge input does not escape as an unhandled numeric conversion exception. Finite edge values follow the declared type/domain contract. |
| DW1-T010 | Submit Unicode labels, empty/invalid IDs, boundary-length IDs and unsupported unit strings; exercise explicit offset-temperature quantities. | Text and accepted IDs preserved; stable-domain IDs follow C. Legacy presentation IDs retain their documented mapping. Neutral DTOs do not perform unit equations; reviewed conversion rejects incompatible/unreviewed units. |
| DW1-T011 | Feed malformed JSON and ambiguous object shapes, including duplicate keys and excessive nesting. | Malformed JSON rejected without execution. Duplicate-key/depth policy is explicitly documented and tested once selected; absent published limits are an ORACLE GAP, not an invented size/depth failure threshold. |
| DW1-T012 | Give old DW1 fixtures to the current codec and later additive tagged DTOs to older readers/capability-limited compositions. | Old fixtures retain meaning and bytes; unsupported tags fail explicitly. A shared envelope version does not imply support for every later command. |

### Batch C — imports, replaceability and orchestration ownership (high)

Trace: UIX-ARCH-001/002, UIX-CMD-001, BOUND-001; A/B/N.

| ID | Stimulus / method | Required observation and evidence |
|---|---|---|
| DW1-T013 | Resolve absolute, relative, package re-export and transitive imports throughout boundary/application families, including nested modules. | Neutral closure is standard-library-only for DW1; application policy uses neutral/domain contracts and declared ports, not concrete Qt, storage, numerical or provider implementations. Report actual paths, not string-match counts. |
| DW1-T014 | In a fresh subprocess block Qt, Pint, NumPy, SciPy, NetworkX, concrete property backends and FastAPI; import neutral contracts, codec and registry and use fake ports. | Imports and neutral operations succeed; forbidden modules never enter `sys.modules`. Confirm blocker works with a deliberate forbidden-import positive control. |
| DW1-T015 | Import/run the reference kernel in isolation with Qt, UIX, AI and speech dependencies blocked. | Kernel remains independent; no presentation state enters scientific objects. Distinguish blocked-import testing from a genuinely separate installed environment. |
| DW1-T016 | Exercise root-package imports and every frozen public prototype export in a fresh process. | Neutral import remains lazy; requested legacy exports retain names/order/defining-module compatibility as documented by G. No unwanted eager prototype load. |
| DW1-T017 | Review API/CLI entry points and composition roots; spy on service calls for each retained operation. | Adapters translate inputs/outputs, composition wires dependencies, application owns orchestration. No endpoint-owned solving, equations, repository transaction policy or second Run bypass. |
| DW1-T018 | Replace engineering, draft, artifact and demonstration ports independently with contract-conforming doubles, including unavailable-capability adapters. | Application behavior remains testable without concrete implementations; missing capability is explicit. No hidden global backend or dependency fallback. |

### Batch D — dispatch, attribution and session deduplication (critical)

Trace: UIX-CMD-001, UIX-ARCH-002, PFD-002, AI-001/003; B/C/A.

| ID | Stimulus / method | Required observation and evidence |
|---|---|---|
| DW1-T019 | Dispatch each of the eight supported DW1 commands with correct parameters and recording ports. | Correct handler, request identity, outcome and terminal event. A completed command containing a failed scientific run remains distinguishable from a rejected command. |
| DW1-T020 | Discover capabilities on complete, mock-only and deliberately incomplete compositions; request missing commands. | Only available capabilities advertised; unavailable work explicitly rejected. No synthetic engineering result used to satisfy discovery or execution. |
| DW1-T021 | Repeat exactly the same request ID/content after successful completion and after each terminal rejection/failure category. | Same recorded terminal outcome within that registry session, with no repeated side effects; record which failures occur before a registry can accept a request identity. |
| DW1-T022 | Reuse a recorded ID while changing command, actor, profile, target, receipt, engineering content or presentation content separately. | Different content is rejected; original recorded outcome remains intact; no execution occurs for the conflicting request. |
| DW1-T023 | Repeat a request against a newly created service/registry session; separately reuse the old receipt. | No durable exactly-once claim. Old receipt cannot authorize execution in the new service. Restart itself performs no validation or Run. |
| DW1-T024 | Vary attribution strings, unsupported profiles, INDUSTRIAL and attempts to use actor identity as approval. | Attribution preserved, never treated as authentication/approval. Unsupported engineering profile/capability rejected without silently using REVIEW or promoting fixtures. |
| DW1-T025 | Add legacy/bypass/approved/valid flags to new Run requests and attempt to access compatibility behavior via normal command dispatch. | Strict command path always enforces its receipt policy; legacy HTTP compatibility remains confined to its named use case. |

### Batch E — draft lifecycle and conversion (high)

Trace: CORE-001/002/003/004, PFD-002/003, UIX-CMD-001; B/C/P/G.

| ID | Stimulus / method | Required observation and evidence |
|---|---|---|
| DW1-T026 | Save and reopen complete and incomplete drafts, including repeated identical save. | Immutable/idempotent revisions per the documented repository semantics; no approval, implicit Validate or Run. Older saved bytes remain unchanged. |
| DW1-T027 | Save changed content, reopen latest, and read an older retained artifact; include conflicting identities. | New revision does not overwrite old content; latest selection is correct; invalid identity cannot replace another draft. |
| DW1-T028 | Round-trip duplicate legacy IDs using object kind/ID/occurrence, missing handles, extensions, Unicode labels and existing base-case IDs. | Saving preserves representable legacy fields and occurrences. Authoritative validation rejects duplicate engineering IDs; compatibility does not make invalid topology executable. |
| DW1-T029 | Put result-like/status/parameter names inside presentation extensions and transient overlays; save/open/prepare/run. | Declared original extension data retained separately from transient output; no presentation member changes submitted engineering parameters or supplies calculated results. Runtime overlays strip/persist only as G specifies. |
| DW1-T030 | Validate an unsaved exact snapshot, then inspect repository call history. | Authoritative preparation/compile and receipt only; no implicit save, evaluation or approval. Persisted baseline remains unchanged. |
| DW1-T031 | Use all seven first-slice model/handle mappings, signed duties, explicit units and affine temperatures. | Reviewed adapter mapping matches canonical fixtures/contracts, including `massFlow`; UI/neutral layer performs no engineering conversion. No new model approval inferred. |
| DW1-T032 | Introduce missing parameters, unknown model/material/property IDs, invalid ports/directions/multiplicity, unconnected inputs, nonzero DOF and a recycle. | Authoritative compiler/adapter diagnostic and affected object preserved; no silent backend substitution or unsupported recycle execution. DW1 reports, rather than reimplements, graph policy. |

### Batch F — engineering identity and validation receipts (critical)

Trace: PFD-002/003, CORE-002/010, UIX-ARCH-002; B/C/A/P.

| ID | Stimulus / method | Required observation and evidence |
|---|---|---|
| DW1-T033 | Independently reconstruct `bh-engineering-v1alpha` hash and compare representative cases and generated bounded cases. | Exactly the specified projection; canonical artifact hash remains separately unchanged. Expected hash computation does not reuse production projection logic. |
| DW1-T034 | Change only case title, unit name, layout, label/caption or supported presentation extension fields, one at a time. | Engineering identity unchanged; original canonical name/title changes still affect artifact identity. Reuse of receipt works only in its original draft scope and unchanged execution context. |
| DW1-T035 | Mutate every other canonical field class separately: IDs, parameters, unit text, metadata, model/material/property references/configuration, connections, specifications, profile and array order. | Each changed canonical projection changes engineering identity. Unsupported mutations fail preparation; none bypass stale-validation checks. Record field coverage, not just one changed duty. |
| DW1-T036 | Express the same physical input in different reviewed quantity representations; then change display-only metadata without changing the submitted quantity. | Changed input value/unit representation stales validation even when physically equivalent. Display-only metadata does not. No approximate hash comparison. |
| DW1-T037 | Run without a receipt, with an unknown/random receipt, altered receipt details or caller-supplied hash/validity assertions. | Rejection before any write/evaluation; retained service record is the authority, never echoed caller claims. |
| DW1-T038 | Use A's receipt for B with otherwise identical engineering content; vary draft ID and relevant revision/scope identities separately. | Cross-draft authorization rejected. Legitimate presentation-only source changes follow B, so the test must not require strict equality of old/new canonical source hashes. Document any unprescribed revision-scope rule. |
| DW1-T039 | Validate A, edit engineering content to B, and submit B with A's receipt; also test receipt/snapshot mismatch after save/open. | Stale request rejected before writes/evaluation. Editing does not validate or Run implicitly. Returning to exact validated content is judged by the documented identity/scope policy, not a guessed expiry rule. |
| DW1-T040 | Cause adaptation/preparation failure and, separately, compiler rejection. | Preparation yields `INVALID_DRAFT`; compiler rejection yields visible invalid receipt/diagnostics. Neither can authorize Run; receipt retains DOF/report and attributable source/context information when preparation succeeded. |
| DW1-T041 | Restart application service, mutate caller-held DTO containers, or mutate a returned receipt view before Run. | Restart requires explicit validation; caller mutation cannot alter retained authority. No implicit replay, fabricated receipt or shared mutable prepared engine state. |
| DW1-T042 | Execute Validate→presentation-only edit→Run and inspect persisted input/result linkage. | Receipt remains usable but result identifies the actual submitted/persisted source; changed title/name is not silently replaced with old validated presentation. Scientific values come from the validated engineering context. |

### Batch G — execution context and time-of-check races (critical)

Trace: PFD-002, CORE-010, BOUND-001; B/A/F.

| ID | Stimulus / method | Required observation and evidence |
|---|---|---|
| DW1-T043 | Keep the schema string fixed while changing relevant implementation identity, catalogue entries, property state/configuration or reference data independently. | Context identity changes or capability fails explicitly; prior receipt rejects before execution. Document fingerprint coverage and justified exclusions. |
| DW1-T044 | Make required fingerprint evidence missing, unreadable or incomplete. | Explicit failure; no schema-only/default/empty fingerprint treated as verified identity. No fallback property package. |
| DW1-T045 | Change context after validation but before Run admission. | Stale context rejects before persistence/evaluation. Diagnostic distinguishes context from engineering-input changes where the contract permits. |
| DW1-T046 | Recording port changes context during draft/input persistence, before the post-save recheck. | Immutable saved input may remain; no evaluation/acknowledged run under changed context, no last-valid advancement. Preserve partial-save evidence and explicit failure. |
| DW1-T047 | After admission, mutate the live engine/catalogue/property configuration while evaluation uses its captured state. | Evaluated private snapshot matches validated context or operation rejects. No hybrid old/new configuration or shared mutable numerical state. Deterministic hooks prove timing. |
| DW1-T048 | Revalidate after a legitimate context change and then explicitly Run using the new receipt. | Positive control succeeds under the new identified context with preserved provenance; old artifacts and receipt outcomes remain immutable. No automatic revalidation/retry concealed in Run. |

### Batch H — persistence, failures and acknowledgement (critical)

Trace: CORE-002/009/010, PFD-005; B/C/F/A.

| ID | Stimulus / method | Required observation and evidence |
|---|---|---|
| DW1-T049 | Trace a normal admitted Run through input persistence, context recheck, evaluation and terminal artifact repository return. | Required order established; persisted success returned only after repository acknowledgement. Result references resolve to correct immutable run/case/revision content. |
| DW1-T050 | Fail draft save and input artifact save independently, before evaluation. | Typed failure, zero evaluations/result writes, no last-valid advancement; previous artifacts unchanged. Record any permitted partial immutable input. |
| DW1-T051 | Produce evaluation exception, non-finite result, nonconvergence, closure failure and validity failures through reference/fake engineering ports. | Attempts reaching the engine retain its declared failed-result evidence and independent statuses; pre-adaptation exceptions remain explicit boundary failures. No claim that DW1 already has durable admission for every pre-result crash. |
| DW1-T052 | Fail result write before and after file publication; fail SQLite/index update after artifact publication. | No false durable acknowledgement or last-valid advance. Previous bytes remain unchanged; any orphan artifact is identified. Existing repository retry semantics are recorded; automatic rebuild is not invented. |
| DW1-T053 | Supply missing, corrupt, hash-mismatched or wrong-identity stored artifacts to inspect/compare/last-valid reads. | Explicit repository/boundary failure, never silently repaired by recalculation or replaced by a guessed result. Hash and identity verification responsibilities remain visible. |
| DW1-T054 | Save identical content twice; attempt conflicting content under an immutable identity; verify original bytes and index. | Idempotent identical writes per contract, conflicting immutable replacement rejected, existing artifacts preserved. No candidate-generated fixture updates. |
| DW1-T055 | Raise exceptions containing synthetic credential/path sentinels at engineering and storage ports, including SQLite failure. | Public typed diagnostic retains useful code/cause and known affected identity without leaking sentinels or raw traceback. Missing documented diagnostic fields are recorded, not suppressed by a broad catch. |
| DW1-T056 | After failures, repeat read/open and explicitly retry where allowed; recreate the service to simulate restart. | No recovery-triggered validation, evaluation or approval. Retrying a persistence step must not masquerade as retrying the calculation; distinguish registry cached failure from explicit recovery/new request. |

### Batch I — scientific statuses, last-valid and comparison (critical)

Trace: CORE-008/009/010, PFD-004/005; B/C/A/P.

| ID | Stimulus / method | Required observation and evidence |
|---|---|---|
| DW1-T057 | Transport every combination of 3 convergence × 3 closure × 4 physical × 4 correlation states: **144 combinations**. | All four values survive neutral serialization/view mapping independently. Synthetic combinations test transport and selection, not physical realizability. Unknown/not-checked never become success. |
| DW1-T058 | For the same 144 combinations, test last-valid admission against the explicit predicate below. | Only two combinations qualify. In particular EXTRAPOLATED correlation qualifies with visible status; EXTRAPOLATED physical validity does not. Assert exact truth table. |
| DW1-T059 | Persist qualifying run A, each nonqualifying run B, then qualifying C; repeat with no prior qualifying run and interleaved cases. | B remains inspectable; A stays selected until C; other cases unaffected. No qualifying result returns explicit absence, never fabricated zeroes or an arbitrary failed run. |
| DW1-T060 | Inspect failed/successful runs with missing metrics, negative/zero quantities, diagnostics and immutable artifact references. | Stored values/units/statuses/provenance retained; unavailable metric/unit explicit. No UI result fabrication, hidden scientific recalculation or bare unqualified 'valid' summary. |
| DW1-T061 | Compare identical run, two unchanged stored runs, changed quantity, added/removed metric and each independent status change. | Only changed metrics/statuses returned; prior/current values correct, missing side explicit; repeated comparison deterministic and read-only. |
| DW1-T062 | Compare differently expressed units, unequal/missing units and identically named metrics on different equipment. | No invented cross-unit delta, implicit conversion or metric misassociation. Explicit before/after quantities and object identity remain available. |
| DW1-T063 | Compare two cases, missing run IDs, and corrupted references. | Cross-case comparison gives `CASE_MISMATCH`; other read errors are explicit; zero writes/validation/evaluation. |
| DW1-T064 | Vary command completion state independently from scientific status, and retain repeated failed attempts with distinct explicit request/run identities. | Handled scientific failure does not become command rejection or last-valid eligibility merely through one success boolean. Attempts stay separately attributable. |

The last-valid oracle is exactly:

```text
convergence == CONVERGED
and closure == PASSED
and physical_validity == VALID
and correlation_validity in {VALID, EXTRAPOLATED}
```

Do not change this policy to require all four dimensions to say VALID, or to use
only convergence/closure. If a scientific policy change is proposed, it needs its
own authority and must not be hidden inside this review.

### Batch J — frozen legacy compatibility (high)

Trace: CORE-001/002/008/010, PFD-002/003, UIX-CMD-001; B/C/G/A.

| ID | Stimulus / method | Required observation and evidence |
|---|---|---|
| DW1-T065 | Replay all frozen `baseline`, `units_extensions` and `splitter` HTTP traces using temporary stores. | Exact paths/methods/statuses/envelopes/aliases/messages/units/warnings/results match after only G's permitted normalization. New optional contracts cannot change old response shape. |
| DW1-T066 | Replay legacy HTTP Run without prior validation; contrast new command Run without a receipt. | HTTP keeps save→prepare/compile/run→persist compatibility; new command rejects before effects. Browser receipt/overlay gaps stay documented and are not marked fixed by this test. |
| DW1-T067 | Replay malformed HTTP shape, incomplete flowsheet, mismatched IDs, missing draft, invalid handle and repeated explicit Run. | Frozen status/diagnostic semantics retained, including 422 shape failures versus 200 compile diagnostics where specified; separate explicit runs retain distinct identities. |
| DW1-T068 | Compare canonical case/revision/compiled/run bytes and digests for each golden scenario; round-trip unchanged originals. | No changed canonical hash meaning, extra fields, reordered arrays or silent migration. Compiled serialization remains audit data, not a replacement authority. |
| DW1-T069 | Apply transient normalization only to generated run IDs/timestamps permitted by G. | Before replacement validate format and distinctness of generated identities. Engineering values, stable IDs, diagnostics, quantities, provenance and statuses remain exact. No normalization of persisted user artifacts. |
| DW1-T070 | Run `solid-radiator`, `droplet-radiator`, `surge-buffer` through CLI subprocesses and inspect public export compatibility. | Existing names/arguments/report stdout JSON, fixture warnings and exit behavior preserved; demo port invoked; prototypes not promoted. Invocation mapping must be verified from public entry points in the execution round. |
| DW1-T071 | Exercise reference warnings, unsupported profiles/catalogues/backends and attempted fixture promotion across command/HTTP/demo entry points. | Documented legacy reference behavior preserved; new boundary fails explicitly outside supported scope; no silent profile/backend change, invented data or model approval. |

### Batch K — rigor, test sensitivity and current integration (review/high)

Trace: UIX-DOC-001/002, UIX-ARCH-001/002, CORE-002/008/009/010; N/L/A/B/V.

| ID | Stimulus / method | Required observation and evidence |
|---|---|---|
| DW1-T072 | Review each public command/port/DTO and non-obvious algorithm against purpose, units, identity, effects, failures and limits. | Complete public types and editable rationale; focused ownership, explicit dependencies, no unexplained numerical constants or speculative claims. Report concrete maintainability risks with locations and consequences. |
| DW1-T073 | Trace any scientific conversion/evaluation changes to existing cards/equations/data and compare golden outputs. | DW1 extraction changes no physics or provenance. Newly discovered scientific defects go through L; a passing software suite never grants model/design approval. |
| DW1-T074 | Substitute deliberately faulty test doubles/mutants: accept forged receipt, ignore context change, include label in engineering hash, drop a status, acknowledge failed write, advance last-valid on closure failure. | Corresponding tests fail for the expected reason. Record mutation→test mapping; never mutate the working production tree. A surviving critical mutant is a test gap. |
| DW1-T075 | Map every test ID and applicable existing requirement to an executed test node, review observation or named evidence gap. | No empty/test-discovery-only success, blanket exclusion or unreasoned skip. Failures include reproducible input, expected/actual behavior and source identity. |
| DW1-T076 | Rerun DW1 golden contracts on the current expanded boundary/registry and later additive capabilities. | Current DW2/DW3/history/control/extension additions preserve DW1 behavior; no broad deletion of later DTO registrations to make isolation tests pass. Later-specific failures are attributed to their gate. |
| DW1-T077 | Run focused DW1 tests, full existing Python regression, lint, format, type checks, browser tests/lint/build and current documentation integrity checks. | All outcomes and environment versions retained; baseline and new failures separated. These checks supplement the adversarial cases rather than replace them. |
| DW1-T078 | Review final changed artifacts, canonical/fixture hashes and all allowed normalizations against the frozen before-state. | No unrelated changes, historical evidence rewrites or silent weakening of tests; incompatible proposals have version/migration/authority analysis. |
| DW1-T079 | Reproduce each repaired defect on before/after isolated snapshots, then perform fresh read-only review of critical paths. | Red reproduction, green correction and regression evidence linked to exact bytes. Implementer self-checks are labelled; no unsupported independent/qualified-review claim. |
| DW1-T080 | Assemble final disposition and a receiving-developer walkthrough of scope, artifacts, gaps and recovery. | Reviewer can reconstruct evidence and next work without chat context. No full DW1 acceptance while mandatory cases remain failed, blocked or unexecuted; no global native/scientific/release promotion. |

## 4. Documentation ambiguities to resolve during test binding

These are **oracle/evidence gaps**, not confirmed implementation findings.
Continue all unaffected tests while a specific disputed oracle is resolved.

| Gap | Handling and responsible role |
|---|---|
| Exact nested wire shapes and many stable diagnostic codes are not enumerated in B. | Test author binds to existing public contract declarations and frozen fixtures during the authorized code round, after keeping these behavior oracles fixed. Do not manufacture exact codes beyond documented `INVALID_DRAFT`/`CASE_MISMATCH`. Contract steward resolves contradictions. |
| Revision scope, receipt reuse after returning to identical content, and failure-cache details need precise examples. | Derive from B's exact-snapshot/draft-scope/session promises; use fixtures where authoritative. If still ambiguous, record OPEN ORACLE and ask steward for the narrow rule; never infer the rule solely from current implementation. |
| 'Relevant implementation' context fingerprint coverage is not an exhaustive module/data inventory. | Reviewer maps every preparation/evaluation dependency and configured catalogue/property value. Implementation must justify exclusions; additions that change packaging/identity contracts receive steward review. |
| No DW1 transport byte/depth limits, thread-safety guarantee or durable deduplication contract. | Treat bounded parser abuse/concurrent dispatch as characterization or proposed hardening until a contract exists. Do not import DW4 worker limits into DW1. Ordinary malformed/version rejection is already mandatory. |
| Broad failure policy describes pre-run manifests, atomic browser writes and rebuild behavior that B explicitly defers. | Verify DW1's acknowledgement/preservation obligations now; retain remaining work at GAP-06/DW4 and applicable artifact gates. Do not label all target policy as historically implemented. |
| DraftRevision version wording and other DW0 GAP-09 discrepancies remain historically recorded. | Check current canonical golden bytes and version rules; no opportunistic strict-domain field addition. Contract steward documents/migrates any actual incompatibility. |

## 5. Execution commands and evidence contract

Commands below are **planned**, not run in this preparation. First inspect the
test/configuration entry points in the execution round; do not install/update
dependencies merely to hide an environmental failure. Use the locked environment
and record missing extras as blockers. Proposed new tests belong under the existing
`tests/` tree, grouped by the families above, with IDs visible in node IDs/metadata.

From the isolated repository root, the documented existing checks are:

```bash
.venv/bin/python -m pytest -q tests/test_boundaries.py tests/test_application.py tests/test_dw1_compatibility.py
.venv/bin/python -m pytest -q
.venv/bin/ruff check src tests tools
.venv/bin/ruff format --check src tests tools
.venv/bin/pyright --pythonpath .venv/bin/python
.venv/bin/python tools/check_project.py
git diff --check
```

From `web/`:

```bash
npm run test
npm run lint
npm run build
```

Add an explicit command for the new review tests after binding their filenames;
capture collected node IDs and assert a nonzero expected count. Record any required
`PYTHONPATH`/offscreen Qt settings; an offscreen run is not a native witness. Inspect
the current integrity helper before running it. The historical
`check_dw1_review.py` is not a current acceptance gate because Q records expected
post-sanitization mismatches. Do not repair old hashes to make it green.

For each test family retain:

```text
Test ID / parameter case / requirement / source section:
Candidate commit + dirty-snapshot manifest; fixture and test hashes:
Command or manual method; environment; seed/synchronization hook:
Input/setup; independent expected outcome; actual outcome:
Call trace; before/after artifact hashes; relevant diagnostics:
PASS | FAIL | BLOCKED | NOT RUN | NOT APPLICABLE (reason required):
Defect or oracle-gap reference; evidence paths; reviewer and role:
```

Put new execution evidence in a new dated directory beneath `docs/native/evidence/`,
separate from this planning record and original DW1 evidence. Preserve raw local
outputs where appropriate; label sanitized copies and retain content hashes.
Never include real credentials or private case data. Logs must identify final exit
codes, collected/executed/skipped counts and all parameterized failures.

## 6. Acceptance decision

The **review batch is executed** when every family has a traceable outcome or
explicit scope/oracle disposition. **DW1 software acceptance passes** only when all
applicable mandatory behaviors pass, critical test-sensitivity checks pass,
required regression checks pass, and no unresolved defect or missing oracle defeats
the claimed scope. Environmental skips are not passes. Baseline failures may be
separately attributed but still limit the final acceptance claim.

Report software behavior, architectural compliance, compatibility, evidence gaps
and maintainability separately. Preserve existing requirement statuses unless their
full named automated/witnessed obligations are actually met. Independent scientific
V&V, native release acceptance, platform support and engineering-design approval
remain separate obligations.
