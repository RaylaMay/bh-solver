# `v1alpha` Public Contracts

This document is normative for the implemented first slice. Python contract names
use `snake_case`; the browser API uses the camel-case aliases shown in the HTTP
section. All persisted domain dataclasses carry a `$type` discriminator in canonical
JSON. Unknown domain fields fail closed.

Stable IDs begin with a letter, contain only letters, digits, `_`, `.`, `:`, or
`-`, and are at most 128 characters. Timestamps are ISO 8601 UTC strings. Content
digests are lowercase SHA-256 hex over compact, sorted-key UTF-8 JSON. Quantities
reject non-finite values and unreviewed unit spellings.

## Quantity and independent statuses

```text
Quantity { value: finite number, unit: reviewed Pint-backed unit string }

ConvergenceStatus = NOT_RUN | CONVERGED | FAILED
ClosureStatus     = NOT_CHECKED | PASSED | FAILED
ValidityStatus    = UNKNOWN | VALID | EXTRAPOLATED | INVALID
```

The four result dimensions are independent. A converged calculation may be
`EXTRAPOLATED`; closure cannot turn an invalid correlation into a valid one.
Boundary values preserve submitted display units. Numerical code explicitly
converts to canonical SI and applies variable/residual scaling.

## Materials, properties and states

```text
PropertyPackageReference {
  package_id, implementation, version, configuration_id?
}

MaterialReference {
  material_id, name, property_package_id, evidence_reference?
}

CompositionComponent { material_id, fraction }
StateSpecification    { variable, value: Quantity }

FlashRequest {
  property_package_id,
  composition: CompositionComponent[],
  specifications: exactly two independent StateSpecification values
}

PhaseState {
  phase, fraction, temperature, pressure, density,
  specific_enthalpy, heat_capacity?
}

ThermoState {
  property_package_id, composition, temperature, pressure,
  specific_enthalpy, phases[], validity, provenance[], messages[]
}
```

`FlashVariable` currently permits temperature, pressure, specific enthalpy, and
vapour fraction. The initial pure-liquid backend implements `(T,P)` and `(h,P)`
only. It always returns an explicit liquid phase, rejects mixtures, marks values
outside the evidence range `EXTRAPOLATED`, and rejects values outside its hard
mathematical domain.

Every property implementation satisfies:

```text
PropertyPackage.package_id -> StableId
PropertyPackage.flash(FlashRequest) -> ThermoState
```

Material streams reference registered IDs; they never persist a backend object:

```text
MaterialState {
  material_reference_id, composition, mass_flow: Quantity, thermo: ThermoState
}
```

## Ports and unit operations

```text
MaterialPort { port_id, name, direction: INPUT | OUTPUT, required }
EnergyPort   { port_id, name, direction: INPUT | OUTPUT, required }

MaterialPortValue { port_id, state: MaterialState }
EnergyPortValue   { port_id, duty: Quantity }
```

Only equal port kinds connect, output connects to input, and a required inlet must
have exactly one connection. `SignalPort` is intentionally deferred until P&ID
contracts stabilize.

```text
UnitDefinition {
  unit_id, model_id, name,
  parameters: [(name, Quantity)], metadata: [(name, string)]
}

UnitEvaluationRequest { unit_id, input_port_values[], parameters[] }

UnitEvaluation {
  unit_id, output_port_values[], residuals[], diagnostics[], events[],
  validity, audit_evidence[], metrics: [(name, Quantity)]
}
```

Every model implements one `UnitOperation.evaluate(request) -> UnitEvaluation`
contract. A unit cannot traverse the graph, call neighbours, persist data, or run
a flowsheet solver. The catalogue descriptor declares ports and required
parameters before construction.

The first catalogue contains:

| Model ID | Required parameters | Ports |
|---|---|---|
| `source` | `mass_flow`, `temperature`, `pressure`; metadata `material_id` | material out |
| `sink` | none | material in |
| `heater` | signed `duty` | material in/out; energy result |
| `mixer` | none | material in A/B, out |
| `splitter` | `split_fraction` | material in, out A/B |
| `heat_exchanger` | `effectiveness` | hot/cold material in/out |
| `radiator` | `outlet_temperature`, `emissivity` | material in/out; energy result |

## Four state forms

```text
CaseDefinition {
  case_id, title, materials[], property_packages[], units[], connections[],
  specifications[], ai_profile, schema_version: "v1alpha"
}

DraftRevision {
  revision_id, base_case_id, revision_number, case: CaseDefinition,
  changes[], created_at
}

CompiledFlowsheet {
  compiled_id, source_case_id, source_revision_id?, source_hash,
  execution_order[], variables[], degrees_of_freedom,
  recycle_groups[][], diagnostics[], schema_version: "v1alpha"
}

RunResult {
  run_id, case_id, revision_id?, compiled_id, created_at,
  unit_evaluations[], balances[], solver_result,
  convergence, closure, physical_validity, correlation_validity,
  provenance[], diagnostics[], schema_version: "v1alpha"
}
```

`CaseDefinition`, `DraftRevision`, and `RunResult` are frozen values.
`CompiledFlowsheet` is derived and may be regenerated from the hashed case.
Canonical artifacts are immutable and content-addressed. SQLite stores only an
index; an approved case row is not advanced by another artifact with the same ID.
A last-valid pointer advances only for converged, closed, physically valid runs
whose correlation status is `VALID` or `EXTRAPOLATED`.

## Compiler and solver boundaries

The graph coordinator validates model IDs, parameters, metadata, port existence,
kind, direction, fan-out, duplicate feeds, required inputs, degrees of freedom,
and strongly connected recycle groups. `v1alpha` reports recycle groups but does
not execute them.

```text
ResidualVariable { name, initial_value, scale, lower_bound?, upper_bound? }
ResidualProblem  { variables[]; evaluate(values[]) -> Residual[] }
Residual         { name, value, scale, unit }
SolverIteration  { iteration, residual_norm }
SolverResult     { status, values[], iterations[], final_residuals[], message }

SteadySolver.solver_id -> string
SteadySolver.solve(ResidualProblem) -> SolverResult
```

SciPy bounded least squares is the first replaceable adapter. Neither equipment
models nor persisted schemas expose SciPy objects.

## Audit values

```text
Diagnostic    { code, message, severity, subject_id? }
ModelEvent    { code, message, timestamp_s? }
AuditEvidence { name, equation, inputs[], outputs[], assumptions[], evidence_reference? }
BalanceRecord { name, residual: Quantity, tolerance: Quantity, status }
ProvenanceRecord { source, model, version, evidence_reference? }
```

Audit equations are human-readable support for reconstruction; the UI must not
recalculate them.

## AI change boundary

```text
AiProfile       = REVIEW | EXPLORATION | NARRATIVE
ChangeSetStatus = PROPOSED | APPROVED | APPLIED | REJECTED

ExplorationLimits { maximum_iterations, maximum_runs, maximum_elapsed_seconds }

ChangeSet {
  change_set_id, profile, base_revision_id, proposed_revision,
  changes[], engineering_rationale, status, exploration_limits?
}
```

Review changes require explicit approval. Exploration requires declared bounds.
Application always returns a new revision and never mutates the baseline.
Narrative changes must retain the visible narrative profile, and narrative runs
emit a warning diagnostic.

## Browser API

All responses are `{ "apiVersion": "v1alpha", "data": ... }`.

```text
PfdDraft {
  schemaVersion: "v1alpha", draftId, revision, baseCaseId?, updatedAt,
  nodes: ReactFlowNode[], edges: ReactFlowEdge[]
}

ValidationResult { valid, degreesOfFreedom, diagnostics[] }

RunResultDto {
  runId, draftId, revision, converged, conservationClosed,
  diagnostics[], nodeResults[], completedAt
}
```

PFD positions, viewport fields, animations, display labels, and colours never enter
scientific contracts. API conversion maps explicit node parameters and handles to
registered unit, quantity, and port contracts.

| Method and path | Behaviour |
|---|---|
| `GET /api/v1alpha/health` | Service readiness |
| `PUT /api/v1alpha/drafts/{draftId}` | Idempotently save or create the next immutable PFD revision |
| `GET /api/v1alpha/drafts/{draftId}` | Load the latest saved PFD revision |
| `POST /api/v1alpha/drafts/{draftId}/validate` | Convert and compile without running |
| `POST /api/v1alpha/drafts/{draftId}/runs` | Validate, run, persist, and return overlays |

Malformed HTTP shapes return `422`. A well-formed but incomplete flowsheet returns
`200` with engineering diagnostics. A run attempt produces an immutable core
`RunResult`, including validation or evaluation failures.

## DW0 proposed boundary contract work

Status: **DESIGN SCOPE APPROVED** with ADR-010 on 2026-09-11. No schema, codec,
public type or persisted artifact changes occurred in DW0. The subsequent
[DW1 boundary specification](native/DW1_BOUNDARY.md) records the implemented
`bh-command-v1alpha` slice and its separate presentation/engineering identities;
[DW1 evidence](native/DW1_CHANGE_RECORD.md) records its verification. The table
below retains the complete staged scope, including contracts not yet implemented.

| Family | Required proposed content | Freeze/implementation gate |
|---|---|---|
| Command envelope | Independently named command schema version, stable command name, request ID, actor/profile, target revision and hashes when relevant, typed parameters | DW1 |
| Command outcome | Request ID, typed accepted/rejected/completed outcome, stable diagnostic codes and affected object/field, artifact references; no combined scientific success flag | DW1 |
| Validation receipt | Exact engineering hash and hash-scheme version, revision identity, catalogue/property/configuration identities, diagnostics and DOF; changes to calculation inputs or capabilities stale it | DW1 |
| Presentation document | Version, flowsheet object IDs, positions/routes/viewport/labels/layout; explicit mapping to existing React DTO extension fields | DW1/DW3 |
| Worker negotiation | `WorkerHello`, protocol version, capabilities, backend/version availability, worker session identity | DW4 |
| Run request/admission | `RunJob`, immutable case/revision references and verified hashes, run/request IDs, explicit solver configuration; `RunAccepted` acknowledges that exact job | DW4 |
| Worker events | Run/session/request identity, ordered sequence, `RunProgress`, `RunDiagnostic`, `RunCompleted`, `RunFailed`, `RunCancelled`, immutable artifact references | DW4 |
| Worker control | `CancelRun` with safe-boundary semantics; sanitized `WorkerFault`; mismatch, malformed, duplicate, late and out-of-order message handling | DW4 |
| AI participant/session | Identity, provider/model/version, exact question/context hashes, profile, assumptions/evidence, proposed ChangeSet/scenario, uncertainty/dissent, tool/run ledger and human disposition | DW6/DW8 |
| Transcript | Identity/mode/timestamps/locale, optional audio reference and retention state, provider/version, original/edited/submitted text and explicit submission links | DW7 |

The command inventory covers case/draft create/open/save/clone/import/export,
equipment add/remove/configure/connect/disconnect, presentation move/route,
validate/start/cancel/inspect run, select/compare revision/run, propose/review/apply
ChangeSet, attach AI context, and record/stop/transcribe/edit/submit transcript.
Commands unavailable in an implemented phase return an explicit capability
diagnostic; listing a command does not implement or authorize it.

### Identity, versioning and compatibility constraints

- Preserve the current canonical JSON codec and SHA-256 meaning. A current
  `CaseDefinition` includes names/title in its artifact hash. DW1 must define an
  explicit engineering-input projection or versioned presentation separation;
  silently dropping fields from `contract_digest` is prohibited.
- Preserve current `PfdDraftDto`, camel-case HTTP envelopes, stable ID/handle mapping,
  supported extension fields, display-unit values and existing artifact readers.
  Browser DTOs are not the shared neutral DTOs. Convert at the adapter boundary.
- New command/worker version fields are independent of artifact `schema_version`
  and HTTP `apiVersion`. Unsupported versions fail visibly before executing work.
  Additive envelope definitions do not imply that existing strict domain schemas
  accept new fields. Incompatible domain changes require a new version, migration
  fixtures, provenance and approval; retain old artifacts byte-for-byte.
- Do not import the Pint-backed `core.Quantity` into UIX. A neutral quantity DTO
  carries finite value/unit text; reviewed application/domain conversion owns unit
  semantics. Never implement engineering unit conversion equations in widgets.
- Persist run admission before worker execution; retries of admission must not
  create duplicate runs. A lost reply is reconciled by request/run identity and
  never by replaying Run. Every allocated attempt needs an auditable terminal
  outcome, including cancellation or worker loss.
- Current `ConvergenceStatus` lacks cancellation and `RunResult` lacks a full run
  manifest. Define an independently versioned lifecycle/manifest artifact or an
  approved domain migration before DW4; do not insert `CANCELLED` into the old enum
  or describe an interrupted run as converged. The four scientific dimensions
  stay separate and may remain unknown/not checked.
- Worker framing, byte/queue limits, supported-version negotiation, cancellation
  races and artifact-write ownership require protocol fixtures before DW4. Do not
  persist decimated telemetry as the full trajectory. Binary sidecars need ADR-009's
  separate format decision before any large dynamic arrays become authoritative.

Minimum compatibility fixtures: canonical case/revision/run byte round-trip;
React draft with extension fields and units; DTO-to-core mapping; schema rejection;
unchanged inputs with presentation-only movement; engineering edit and stale
validation; four-status truth table; failed/cancelled attempt with last-valid
preservation; duplicate command and version mismatch. Migration must write a new
artifact with source identity and never overwrite the original.

### DW2 additive draft navigation contracts

The [DW2 shell contract notes](native/DW2_SHELL.md#contracts-compatibility-and-recovery)
add `draft.create` / `CreateDraftParameters`, `draft.list` / `ListDraftsParameters`
and immutable `DraftListDto` / `DraftSummaryDto` to `bh-command-v1alpha`.
Existing tags, fields, strict decoding, canonical artifacts and HTTP schemas are
unchanged. Old codecs reject the new tags; a client must use advertised command
capabilities, not infer support from the common envelope version. Fixed new
fixtures supplement the unchanged DW1 compatibility fixtures.

The neutral `CommandGateway` exposes `command_names` and synchronous `dispatch`.
Draft creation returns an unsaved empty draft; discovery returns saved identities,
never calculated values. The repository port gains a read-only `summaries`
operation. No new worker protocol or engineering artifact format is implied.
Qt workspace settings use a separate local layout version and never enter the
neutral command or engineering hashes. No case/artifact migration is required.
