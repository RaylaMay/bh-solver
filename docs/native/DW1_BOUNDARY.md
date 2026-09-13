# DW1 neutral application boundary

Date: 2026-09-11. Authority: accepted ADR-010 and
[DW0 owner disposition](DW0_OWNER_DISPOSITION.md).
Scope: the existing reference-fixture steady flowsheet and legacy demonstrations.
This boundary does not introduce Qt, a worker, new model physics or an industrial
profile. Implementation evidence is recorded in [DW1's change record](DW1_CHANGE_RECORD.md).

## Version and ownership

The synchronous command schema is `bh-command-v1alpha`. It is independent of the
existing HTTP envelope `apiVersion: v1alpha` and canonical artifact
`schema_version: v1alpha`. Neutral DTOs carry ordinary immutable values, explicit
quantity values/unit text and versioned presentation data. No Qt, Pint, scientific
backend, graph or database object is exposed to an interaction adapter.

The application owns command dispatch, validation receipts, save/run use-case
ordering, result inspection and comparison. Declared ports own the boundaries to
draft storage, artifact storage, engineering preparation/validation/evaluation
and prototype demonstrations. Concrete adapters translate those requests and
results. The composition root selects and wires the existing reference engine
and stores. Scientific code and its canonical codec remain unchanged.

The package's public prototype imports remain compatible while neutral imports
avoid eagerly loading those implementations. The browser keeps its existing HTTP
DTOs and aliases at its adapter; those React-oriented types are not the shared
command contracts.

## Supported synchronous commands

| Command | Parameters | Result / effects |
|---|---|---|
| `draft.save` | Immutable draft snapshot | Persist an immutable/idempotent PFD revision; no approval or run |
| `draft.open` | Draft ID | Read latest saved draft; no automatic validation/run |
| `draft.validate` | Exact immutable draft snapshot | Authoritative preparation/compile, service-retained validation receipt; no implicit save |
| `run.start` | Draft snapshot and issued receipt ID | Check receipt/current engineering identity before save/evaluate/persist; return run view |
| `run.inspect` | Run ID | Read immutable stored result |
| `run.select_last_valid` | Case ID | Read last acceptable run using all four scientific dimensions |
| `run.compare` | Two run IDs from the same case | Report changed stored quantities/statuses without rerunning; reject cross-case comparison |
| `demo.evaluate` | Legacy demonstration name | Evaluate the retained prototype demonstration through its port |

The envelope carries command name, schema version, request ID, actor ID, profile
and typed parameters. Terminal command outcome/event is separate from scientific
acceptability: successfully handling a Run can return an unconverged or invalid
scientific result. Unknown versions/commands and unsupported capabilities produce
explicit rejection. Request IDs provide attribution, not durable exactly-once
delivery. Within one registry session, an exact duplicate request returns its
recorded terminal outcome; reusing that ID for different content is rejected.
Actor IDs are attribution fields, not authentication or evidence of qualified
engineering approval. No worker progress protocol or cancellation claim is made
here.

The new first-slice engineering adapter remains limited to the illustrative
reference material/property setup. Unsupported profile or catalogue capabilities
must fail explicitly rather than silently adopting REVIEW or changing a backend.
AI proposal/approval authority is not widened by command dispatch.

## Engineering identity and explicit Run

The engineering hash scheme is `bh-engineering-v1alpha`. It hashes the canonical
`CaseDefinition` representation with **only `title` and each unit's `name`
omitted**. All remaining canonical fields, collection order, explicit quantity
representations, connections, model/material/property references, specifications
and profile remain in that projection. The underlying canonical artifact hash
is unchanged and continues to include those names. No old artifact is rewritten.

Layout, label/caption and supported React extension data are held in the separate
presentation DTO (`bh-presentation-v1alpha`). They never supply engineering
values. Changing a display label or position leaves the engineering hash unchanged;
changing a parameter quantity representation, model or topology requires new
validation. A physically equivalent differently expressed input quantity still
changes this hash: there is no hidden tolerance or UI equation in identity checks.

Presentation entries use object kind, ID and occurrence so even invalid legacy
drafts with duplicate IDs can be saved/opened without losing fields; authoritative
validation still rejects duplicate engineering IDs. Original browser extensions
and transient overlays occupy separate JSON members. First-slice parameter
locators retain their existing spelling (for example `massFlow`); the reference
adapter alone maps them to kernel parameters. These compatibility details do not
permit presentation extensions to supply calculated values or alter a Run.

Validation creates and retains an opaque receipt in the application service.
The receipt identifies its draft scope, prepared revision, original source
artifact hash, engineering hash/scheme, execution-context hash and compiler
report. Run admission trusts the retained receipt, not caller-supplied validity
or hash assertions. It recomputes the submitted snapshot's identities and rejects
missing/unknown/stale receipts before writing or evaluating. Presentation-only
changes may produce a new source artifact while retaining engineering validation.
Preparation failures return `INVALID_DRAFT`; a compiler rejection returns an
invalid receipt whose diagnostics remain visible and which cannot authorize Run.

Execution context must identify the actual reference configuration and relevant
implementation, not merely the string `v1alpha`. DW1's in-process adapter
fingerprints relevant source and configured catalogue/property state. Missing
identity evidence must fail explicitly; a distributable code/data manifest is
later packaging work. Receipts are process-local: restart requires explicit
revalidation and never replays a Run.

Run rechecks context after input persistence, and the concrete in-process adapter
evaluates a private engine snapshot matching the validated context. A context
change detected during persistence can leave an immutable saved draft/input, but
does not produce an acknowledged run under the changed context. This is a bounded
in-process guard, not the durable worker-admission protocol scheduled for DW4.

## Legacy HTTP and CLI compatibility

The existing `/api/v1alpha` paths, request/response aliases, fixture warnings,
status mapping, quantity formatting and canonical artifact bytes remain the
compatibility contract. The legacy browser Run use case preserves its existing
save→prepare/compile/run→persist semantics, including the absence of a separate
prior-validation receipt. That path is explicitly named compatibility behaviour;
new command callers receive no switch that bypasses receipt enforcement.

The current browser therefore still has the DW0 gaps in Run enablement, stale
validation display, failed canvas overlays and missing run-level physical/
correlation status fields. Service extraction does not claim those UI requirements
VERIFIED. Native work can use the stricter command path and complete those views.

Legacy CLI command names, arguments and report JSON remain compatible:
`solid-radiator`, `droplet-radiator`, `surge-buffer`. Their prototype equations,
coefficients and warnings remain unchanged behind a demonstration port; they are
not promoted into the approved flowsheet catalogue.

## Result, persistence and failure limits

New run views preserve convergence, closure, physical validity and correlation
validity independently and expose typed returned quantities and immutable artifact
references. Comparisons report prior/current quantities and status changes; they
do not invent numerical deltas across different units. Absence of a metric or unit
is explicit. The result contains changed metrics/statuses only, and both runs must
belong to the same case (`CASE_MISMATCH` otherwise). Full structural revision
comparison and native history/workbooks remain later work.

The application acknowledges a persisted run only after the artifact repository
returns. Existing core artifact hashes and last-valid policy remain authoritative.
This extraction does not add durable run admission, crash recovery, cancellation,
index rebuild or a binary trajectory format. Those require DW4 and the separate
artifact decisions already identified in DW0. Failed attempts that reach the
existing engine remain immutable results; pre-adaptation failures still follow
their declared boundary diagnostics.

## Verification requirements

Compatibility fixtures capture the pre-DW1 HTTP, canonical case/revision/compiled/
run and CLI behaviour. Generated run IDs and timestamps are normalized explicitly
in tests only; stored user artifacts are never normalized or overwritten.

New tests must cover malformed/unknown command versions and types, immutable
inputs, missing/stale/forged receipts, cross-draft scope, presentation versus
engineering edits, changed execution context, separate statuses, failed-run
last-valid selection and comparison. Fake ports establish that rejection happens
before persistence/evaluation. Recursive import checks, resolved relative imports
and an isolated import subprocess verify the neutral/application dependency
closure. The exact commands and observed evidence belong in the change record;
passing them does not approve a model or demonstrate Windows/Linux support.
