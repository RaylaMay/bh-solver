# Architecture Decision Record

ADR-001 through ADR-009 are the accepted `v1alpha` history. ADR-010 was accepted
with annotations Rayla May supplied on 2026-09-11 and supersedes the browser-primary direction
of ADR-008 and the limited desktop-distribution policy identified below. The
existing browser implementation remains the migration/rollback baseline.

## ADR-001 — Canonical units

**Decision.** API and persistence fields use `{value, unit}` quantities validated
by Pint. Kernel calculations convert to SI base units; solvers receive dimensionless
scaled arrays. Offset temperatures are converted before arithmetic. Units may not
be inferred from field names.

**Reason.** This keeps files readable while preventing silent dimensional errors.
Pint objects are not persisted. Incompatible dimensions are validation failures.

## ADR-002 — Schemas and serialization

**Decision.** Pydantic validates the versioned HTTP boundary; frozen Python domain
contracts define canonical persisted state. Canonical interchange is UTF-8 JSON
with sorted object keys for hashing; arrays retain order. Every top-level domain
artifact includes `schema_version: "v1alpha"`. Domain unknown fields are rejected;
presentation DTOs may retain declared React Flow extension fields. Compiled state
can be serialized for audit but is always reproducible from its source hash.

**Reason.** Explicit, language-neutral contracts allow Python, TypeScript, and
future tools to exchange reproducible artifacts without sharing runtime classes.

## ADR-003 — Solving strategy

**Decision.** Use hybrid sequential-modular execution. Compile acyclic groups in
topological order; represent cycles as strongly connected groups with explicit tear
variables and a `SteadySolver` residual problem. SciPy is the first adapter. Units
do not embed root-finding or call neighbours.

**Reason.** This resembles the user’s HYSYS mental model while permitting future
simultaneous, sparse, or commercial solver adapters.

## ADR-004 — Result status and extrapolation

**Decision.** Report convergence, conservation, physical validity, and correlation
validity independently. Validity is `UNKNOWN`, `VALID`, `EXTRAPOLATED`, or
`INVALID`. A model may extrapolate only within a declared mathematically safe hard
domain and must mark the result `EXTRAPOLATED`; outside that domain evaluation
stops. Narrative-profile runs additionally emit a visible warning diagnostic.

**Reason.** A small residual must never disguise an unphysical or unsupported state.

## ADR-005 — Revisions and immutable runs

**Decision.** Saving an edit creates an immutable `DraftRevision`; approving creates
a new `CaseDefinition`. Each run receives a UUID and content hash and writes a new
immutable artifact. Failed runs are retained. A separate index points to the most
recent successful, closed, physically acceptable result and is never advanced by
a failed run.

**Reason.** This permits comparison, recovery, audit, and AI experimentation without
overwriting the baseline.

## ADR-006 — Licensing and optional dependencies

**Decision.** The default kernel uses only OSI-approved permissive dependencies.
Code and scientific data licences are recorded separately using SPDX identifiers
where available. Copyleft, source-restricted, commercial, and proprietary packages
remain explicit optional adapters installed and configured by the user; canonical
cases store adapter IDs, not bundled binaries or data.

**Reason.** Future operational or commercial use must not acquire hidden licence or
redistribution constraints.

## ADR-007 — AI authority

**Decision.** AI interacts only through versioned application APIs. `review` creates
a `ChangeSet` requiring user approval; `exploration` operates on an isolated draft;
`narrative` allows visibly speculative inputs. AI cannot approve cases or models,
overwrite artifacts, suppress diagnostics, alter canon, or supply kernel outputs.

**Reason.** Natural-language assistance is useful for a single user, but numerical
and governance authority remain explicit and auditable.

## ADR-008 — UI separation and run control

**Decision.** React/TypeScript and `@xyflow/react` own PFD presentation. FastAPI owns
the local versioned HTTP boundary. The UI contains no engineering equations and
does not directly import Python kernel objects. Validation and run are explicit
user actions; editing never triggers an implicit solve.

**Reason.** The browser can be replaced or wrapped as a desktop application without
changing scientific behaviour, and incomplete drafts remain safe to edit.

## ADR-009 — Storage

**Decision.** JSON is the canonical artifact. SQLite stores indexes and relationships,
not the only copy of engineering content. TOML stores local project configuration.
Artifacts are addressed by SHA-256 over canonical JSON. Large arrays may later use
an immutable binary sidecar referenced by hash; the format requires a new ADR.

**Reason.** Human-inspectable artifacts and rebuildable indexes reduce lock-in and
improve recovery.

## ADR-010 — Native workstation and independent UIX/solver boundary

**Status:** ACCEPTED WITH ANNOTATIONS FROM RAYLA MAY, 2026-09-11; proposed 2026-09-10.
**Supersedes:** ADR-008's browser-primary direction through the staged native
migration. Introduces a desktop-distribution exception to ADR-006's
user-installed-only policy for the approved LGPLv3 Qt/PySide route, subject to
exact payload/compliance review before adoption and distribution. ADR-006's
permissive default kernel rule is retained. Accepted ADR-001–009 bodies are kept
unchanged as history; no browser/API removal is authorized by this decision.

**Annotations from Rayla May.** First development/release target is macOS/arm64; design for
eventual Windows/x86_64 and BH solver Linux. future release Linux remains pending. Minimum
OS/runtime/hardware versions will be decided as the build becomes deployable.
BH-owned code is non-commercial and source-available under the repository's
BH Non-Commercial Source-Available License; Qt/PySide uses LGPLv3, with no
commercial Qt licence route at this stage. Third-party and externally owned
material retain their own terms. See the attributable
[Rayla May's disposition](native/DW0_OWNER_DISPOSITION.md).

**Context.** Rayla May requests an installed engineering workstation requiring no
browser, terminal, developer runtime installation, or manual server startup in
normal graphical use. The current React/FastAPI slice works but its endpoints own
application orchestration. Its observed limitations are recorded in the
[DW0 parity inventory](native/BROWSER_PARITY.md). Passing those existing tests
alone would not demonstrate native parity or the required failure behaviour.

**Decision.**

1. Make native UIX, CLI and any retained HTTP adapter peers over neutral, versioned
   commands, result DTOs and typed events. UIX and solver implementations have no
   dependency on one another. A composition root wires concrete adapters to ports;
   application policy depends on contracts and ports only.
2. Keep scientific calculations, graph compilation, properties and solving in the
   kernel/worker. UIX displays returned quantities and statuses and owns only
   interaction and presentation state. Shared DTOs contain no Qt, Pint, NumPy,
   SciPy, NetworkX or concrete backend objects.
3. Use application services for revisions, exact-content validation, run admission,
   artifact persistence, last-valid selection and comparison. A supervised worker
   performs compile/evaluate work; property calls within numerical loops stay in
   that worker. A single installer may contain separate processes.
4. Preserve explicit Validate and Run, immutable engineering artifacts, all four
   independent scientific status dimensions, retained unsuccessful attempts and
   last-valid behaviour. Restart, reconnect and presentation recovery never replay
   Run or approve a case. Presentation edits do not stale engineering validation.
5. Evaluate PySide6/Qt 6 Widgets, a custom design system and QGraphicsView under
   Rayla May's platform and LGPLv3 decisions. This decision selects no Qt release,
   accelerator, benchmark target, packaging tool, AI provider or speech provider.
6. Retain React/FastAPI through native parity, compatibility, migration and rollback
   acceptance. HTTP's eventual installed-product role is a separate choice for Rayla May.
7. Preserve AI profile/ChangeSet authority, typed-text capability and separate
   optional audio, transcription and conversation ports. This ADR grants no new
   scientific approval, industrial fitness, data-upload or training authority.

**Contract/versioning plan.** Keep current canonical `v1alpha` artifact bytes,
hashing and HTTP meanings unchanged during extraction. Introduce independently
named command and worker schema versions with golden fixtures and mismatch
diagnostics. Do not alias the existing Pint-backed `core` package as the neutral
boundary. The [contract proposal](CONTRACTS.md#dw0-proposed-boundary-contract-work)
identifies the hash, cancellation, manifest and migration decisions required
before their implementation; it is not a frozen wire schema. Incompatible artifact
changes require a new schema version, migration fixtures and steward review.
Large-array storage requires a separate ADR under ADR-009.

**Rationale and alternatives.** An adapter/service/worker separation supports the
Rayla May's native workflow and independent replacement without changing model
equations. Continuing browser-only delivery does not meet the stated interaction
goal. Embedding the current browser may aid rollback but does not establish the
requested native workflow. Putting the solver in widgets violates independence
and fault containment. A broad source move adds risk before contract fixtures
exist. Another native toolkit remains an option if the Qt licence or rendering
gate fails; no comparative performance conclusion has been established.

**Consequences.** Additional message, supervision and compatibility tests are
required. Presentation persistence and engineering identity must be separated
explicitly. Bundling a desktop runtime changes distribution obligations even
though kernel dependencies remain permissive. Reference fixtures remain
`BLOCKED_EVIDENCE / TEST FIXTURE ONLY`.

**Acceptance and rollout.** Rayla May approved the boundary, contract-versioning
plan and [parity/retirement checklist](native/BROWSER_PARITY.md) with the
annotations in the [decision register](native/DECISION_POINTS.md), and authorized
DW1 on 2026-09-11. DW1 first introduces ports and an in-process implementation
for browser compatibility; DW2 uses a mock run port; DW4 adds the supervised
worker. No production Qt adoption occurs before its licence gate. DW9 retirement
requires witnessed workflows and a tested rollback, not this ADR's acceptance.

**Review record:** [DW0 preparation package](native/DW0_REVIEW.md), its dated
[Appendix A record](native/CHANGE_RECORD.md), and the
[2026-09-11 disposition by Rayla May](native/DW0_OWNER_DISPOSITION.md). This architecture
approval does not mark unimplemented software requirements VERIFIED or approve
scientific models, industrial use or an unbuilt distribution.

## ADR-011 — Durable local editing history and modular workstation surfaces

**Status:** ACCEPTED DIRECTION through Rayla May's DW3.2 implementation instruction,
2026-09-14. This extends ADR-005, ADR-009 and ADR-010 without changing their accepted
bodies or scientific authority. The [implementation guide](native/DW3_2_WORKSTATION.md)
and [change record](native/DW3_2_CHANGE_RECORD.md) qualify implementation evidence.

**Decision.** Application services own continuously durable logical-edit history,
explicit immutable saves, named snapshots, retained alternatives and attributable
undo/redo. Canonical JSON checkpoints and events remain authoritative; indexes
remain rebuildable. The native UI owns personal navigation and contextual command
surfaces, including an optional ribbon and a closed in-app command grammar. Existing
scientific artifact schemas and hash meanings remain unchanged. Recovery reads
stored state and never replays Run, validation, AI or extensions.

**Rationale and alternatives.** Session-only undo cannot survive closure. Replacing
older saves would erase audit evidence. An executable command replay would require
old models/extensions and could repeat effects. Verified immutable checkpoints make
recovery independent of those effects. Compact controls and optional dock/ribbon
layouts expose common operations without consuming the flowsheet's working area.

**Consequences.** Introduce independent versioned history contracts, migration/fault
fixtures and checks against the current history head. Retain alternate paths; do not prune silently.
Keep personal zoom, selection and temporary highlighting out of document undo.
Measure storage plus native refresh latency. Live collaboration requires the
separate [DW3.3 protocol and failure gate](native/DW3_3_COLLABORATION.md); local
checkpoint reversal is not an implementation of concurrent selective undo.

## ADR-012 — Human-authorized bounded AI exploration and independent acceptance tests

**Status:** BEHAVIOR AUTHORIZED by Rayla May's DW6 planning selections and explicit
implementation instruction, 2026-09-16. The prepared interface/test package is
reviewable implementation input, not evidence of a delivered AI workspace.

**Decision.** Extend ADR-007/010's explicit-action policy narrowly: a human may
approve and start a plan specifying the immutable source, named existing parameter
ranges, provider/model, feedback categories and hard budget. That action authorizes
ordinary coordinator validation/run of isolated candidates within those bounds.
It never authorizes baseline edits, model/case approval, topology/backend changes
or replay after recovery. Each session gets distinct case/result identity. Adoption
requires a new Review proposal against the current target and human approval.

One participant, five candidate iterations, five admitted runs, 300 seconds,
50,000 total input/output tokens, 20 application tool calls and zero automatic
retries are the approved ceilings. The plan authorizes feedback of its own generated
parameters, result summaries and diagnostics. Continue on the captured source if
the original changes; label the mismatch and require fresh adoption review.

**Rationale and alternatives.** Per-candidate human confirmation was considered;
Rayla May selected adaptive parameter exploration inside an approved plan. Fixed
scenario lists and topology-changing exploration were not selected. Isolated case
identities prevent ordinary case-scoped last-valid selection from being advanced
by exploration. Immutable local audit supports reconstruction after failures.

**Acceptance decision.** Develop reviewer-controlled tests before developer
implementation, freeze them in a separate package, and require passing tests plus
implementation review and native/provider witness before integration. The rejected
DW4/DW5 candidate demonstrated why passing supplied tests alone is insufficient.
Test amendments need owner/reviewer disposition and a new recorded digest.

**Consequences.** New neutral contracts, profile propagation, durable reservations,
provider/context controls and real-worker tests are required. OpenAI is the first
adapter behind an interface supporting future remote/local providers. API keys may
use explicit OS credential storage; project audit retains submitted sessions.
DW4/DW5 acceptance remains a prerequisite. Speech, multiple participants, new
scientific models and industrial qualification remain outside DW6.

See [the DW6 specification](native/DW6_ACCEPTANCE_SPEC.md) and
[developer handoff](native/DW6_DEVELOPER_HANDOFF.md). Earlier ADR bodies are retained.
