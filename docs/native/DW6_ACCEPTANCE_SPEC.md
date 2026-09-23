# DW6 acceptance specification — revision 1

Status: **OWNER-SELECTED BEHAVIOR; TEST-FIRST HANDOFF; PRODUCT NOT IMPLEMENTED**.
Date: 2026-09-16. Owner: Rayla May. Preparation: Codex.

Rayla May explicitly instructed implementation of the agreed test-first handoff.
This specification freezes observable behavior for the receiving developer. It
does not assert that DW4, DW5, DW6 or a scientific model has passed acceptance.
The frozen package contains a dated copy of this document; subsequent amendments
need an attributable owner/reviewer disposition and a new package digest.

## 1. Authority and scope

References: ADR-007/009/010/011 and the DW6 extension in `docs/DECISIONS.md`;
AI-001–003, UIX-AI-001, UIX-AUDIT-001, UIX-CMD-001, UIX-ARCH-001/002,
UIX-A11Y-001, UIX-HISTORY-001 and UIX-DOC-001.

Deliver a native text workspace with Review, Exploration and Narrative authority,
explicit context, immutable audit and a replaceable provider. OpenAI is the first
production adapter. Other remote/local adapters are future implementations, not
implicit compatibility claims. Provider/model selection is explicit; no fallback.
API keys are session-only unless the user explicitly chooses the OS credential
store. Never put credentials in project files, audit, diagnostics or exports.

Review requires human approval of the exact proposal. Narrative stays labelled
through persistence and execution and cannot be promoted to Review. Exploration
requires an explicitly approved plan; it may adapt only the named existing
parameters inside inclusive, dimensionally compatible bounds. It cannot change
topology, model selection, property packages, evidence or catalogue approval.
There is no arbitrary shell, plugin, URL-fetch, browser or provider-hosted tool.

The maximum approved exploration budget is one participant, five candidate
iterations, five admitted solver attempts, 300 seconds, 50,000 total input/output
tokens, 20 application tool calls and zero automatic retries. Users can lower
these ceilings. Raising a ceiling is a new policy decision, not a preference.

## 2. Production entry point and test seams

The implementation shall expose the following composition function from
`bh_sim.desktop_launcher`; the ordinary GUI entry point shall call this function:

```python
create_workstation(data_root: Path, *, ai_transport=None, ai_clock=None,
                   credential_store=None) -> DesktopRuntime
```

`DesktopRuntime.window` is the real native workstation, `gateway` is its shared
`CommandGateway`, and `close()` releases only resources owned by that runtime.
`worker_pid` exposes the actual supervised child's PID for process diagnostics.
The caller creates `QApplication`. `main()` selects normal production defaults.
The factory is not an alternate acceptance implementation. No fake gateway,
solver, repository, result projection or acceptance-result callback is permitted.

The only injected replacements are external boundaries:

- `ai_transport`: an HTTPX synchronous transport supplied to the real OpenAI
  adapter. Provider I/O runs outside the Qt thread. With `None`, use the normal
  HTTPS transport. The harness never injects generated scientific results.
- `ai_clock`: `monotonic() -> float`, `utc_now() -> str`. Deadlines use the former;
  audit timestamps use the latter. Recovery never resumes execution automatically.
- `credential_store`: `get(provider_id)`, `set(provider_id, value)`,
  `delete(provider_id)`. Failure must not fall back to plaintext persistence.

Persistence faults are injected at the OS filesystem boundary, real worker faults
at the child-process boundary. These are not service substitutes. Core artifacts
remain the independent authority for values displayed in UI and audit.

## 3. Neutral commands and types

Add standard-library-only frozen types in `bh_sim.boundary.contracts`, registered
with the existing strict codec and shared `CommandRegistry`. Existing envelopes
retain their version and meaning. New persisted AI envelopes use
`bh-ai-context-v1`, `bh-ai-session-v1`, `bh-ai-plan-v1`, `bh-ai-audit-v1` and
`bh-ai-provider-output-v1`. Unknown fields/versions fail closed. Every command uses
the existing request/actor identity; profiles must not be silently downgraded.

Independently version provider capabilities, proposals, budget records and human
dispositions as `bh-ai-provider-capabilities-v1`, `bh-ai-proposal-v1`,
`bh-ai-budget-v1` and `bh-ai-disposition-v1`. A human-decision audit body identifies
its disposition version, exact subject hash, actor and decision. Provider,
credential, extraction, spelling and audit-repository ports belong in the neutral
boundary; adapters implement them without exposing their SDK types. Provider
capabilities describe structured output, token counting and cancellation behavior;
an unsupported capability disables the operation rather than changing providers.

Add persisted `profile` and `execution_scope` to native drafts, validation receipts
and result views. Legacy native drafts default explicitly to `REVIEW`/`ordinary`;
new exploration scopes identify their isolated session. The validation identity
binds both fields; mismatched validation/run command profiles reject. Worker inputs and canonical
case `ai_profile` agree with them. Keep old scientific artifact bytes unchanged.

The following constructor fields are the public test contract. Quantity fields
use the existing neutral `QuantityDto`. Collections are immutable tuples.

| Type | Fields, in constructor order |
|---|---|
| `AiProviderParameters` | `provider_id, model_id, api_key, remember=False` |
| `AiContextParameters` | `target: HistoryTarget, selected_ids, attachment_paths=()` |
| `AiSessionParameters` | `context_id, profile, question` |
| `AiSessionTarget` | `session_id` |
| `AiSendParameters` | `session_id, context_hash` |
| `AiParameterChange` | `object_id, parameter, before: QuantityDto, after: QuantityDto` |
| `AiProposalTarget` | `session_id, proposal_id, proposal_hash, expected_head` |
| `AiProposalEditParameters` | `target: AiProposalTarget, changes` |
| `AiRange` | `object_id, parameter, lower: QuantityDto, upper: QuantityDto` |
| `AiBudget` | `participants=1, iterations=5, runs=5, elapsed_seconds=300, tokens=50000, tool_calls=20, retries=0` |
| `AiPlanParameters` | `session_id, ranges, budget, feedback=("parameters", "results", "diagnostics")` |
| `AiPlanTarget` | `session_id, plan_id, plan_hash` |
| `AiAdoptParameters` | `session_id, candidate_id, target: HistoryTarget` |
| `AiResponseFlagParameters` | `session_id, response_id, reason` |
| `AiDictionaryParameters` | `words, locale` |
| `AiSpellcheckParameters` | `text, locale` |

| Command | Parameter type | Returned data |
|---|---|---|
| `ai.provider.configure` | `AiProviderParameters` | provider view |
| `ai.context.preview` | `AiContextParameters` | immutable context view |
| `ai.session.create` | `AiSessionParameters` | session view |
| `ai.session.send` | `AiSendParameters` | admitted session view; returns promptly |
| `ai.session.inspect/cancel/export/hide` | `AiSessionTarget` | session view, except export returns audit export |
| `ai.proposal.approve/reject/apply` | `AiProposalTarget` | session view |
| `ai.proposal.edit` | `AiProposalEditParameters` | session view with a new unapproved proposal |
| `ai.exploration.plan` | `AiPlanParameters` | plan view |
| `ai.exploration.start` | `AiPlanTarget` | admitted session view; explicit plan approval and start |
| `ai.exploration.adopt` | `AiAdoptParameters` | new Review session with an unapproved proposal |
| `ai.response.flag` | `AiResponseFlagParameters` | session view |
| `ai.dictionary.add` | `AiDictionaryParameters` | dictionary view with `words, locale` |
| `ai.spelling.check` | `AiSpellcheckParameters` | spelling view with `text, issues`; each issue has `word, start, length, suggestions` |

Responses are deeply immutable DTOs, not arbitrary dictionaries. Repeated admitted
request IDs are durable and idempotent; different content with the same ID rejects.
Approval commands are human operations. Provider output is data and cannot supply
an approval status, human actor, executable callback or arbitrary command envelope.
The application binds origin; naming an actor in provider text grants no authority.

### Required read-model fields

Additional fields require a package amendment, not silently changed tests.
The fields below are the required observable projection; implementations may retain
additional private state. Persisted envelopes still reject unknown fields.

- Provider: `provider_id, model_id, enabled, remembered` (never the key).
- Context: `schema_version, context_id, context_hash, source_draft_id, source_head,
  source_engineering_hash, selected_ids, text, attachments`. Each attachment has
  `name, media_type, source_hash, text_hash, text, extraction`. Extraction has
  `extractor_id, extractor_version, page_count, warnings`; text files have zero
  pages. Hashes are lowercase SHA-256.
- Session: `schema_version, session_id, profile, context_hash, source_draft_id,
  source_stale, state, responses, proposals, candidates, ledger, diagnostics`.
- Response: `response_id, text, provider_id, model_id, flags`.
- Proposal: `proposal_id, proposal_hash, source_head, status, changes,
  approved_by, rationale, schema_version`. Status is `PROPOSED/APPROVED/APPLIED/REJECTED`.
- Plan: `schema_version, plan_id, plan_hash, session_id, ranges, budget, feedback`.
- Candidate: `candidate_id, iteration, case_id, profile, changes, state, run_id,
  artifact_hash, diagnostics`. Missing run/artifact identifiers are empty strings.
- Ledger: `iterations, runs, tokens_used, tokens_reserved, tool_calls,
  elapsed_seconds, uncertain_actions, schema_version`. Reserved tokens are still outstanding;
  used plus reserved cannot exceed the approved ceiling.
- Audit export: `schema_version, session_id, records, artifacts`.
  Artifacts have `artifact_id, media_type, sha256, content_utf8` and include every
  referenced case/revision/run plus the context and approved plan.

Session states: `DRAFT`, `SENDING`, `REVIEW_READY`, `RUNNING`, `COMPLETED`,
`FAILED`, `CANCELLED`, `INTERRUPTED`, `LIMIT_REACHED`. Terminal responses cannot
restart a cancelled/interrupted session. A draft can be explicitly sent; a
Review-ready session can be reviewed or given an Exploration plan. Recovery is
read/reconciliation only. A further explicit user submission creates a new session
linked to its predecessor; no automatic retry/reset of the old budget.

## 4. Context, proposals and provider output

The context preview captures flushed native inspector edits, the exact committed
history head, explicit selected objects and user-chosen documents. Source IDs and
engineering hashes are separate from presentation hashes. Unselected objects,
other tabs, machine paths and ambient files must not leak into the request. Attach
TXT/Markdown and locally extracted PDF text; empty/scanned PDFs return
`DOCUMENT_TEXT_UNAVAILABLE`. Do not upload original PDFs, run OCR or silently
truncate. The preview exposes extracted text for review, including missing-text
page warnings. Reject oversize input before transmission: 10 MiB per file,
100 pages per PDF, 200,000 extracted UTF-8 bytes across attachments. These are
initial resource caps, not scientific limits. A user can select a smaller excerpt.

`selected_ids` may name known equipment/stream IDs or persisted run/revision
references belonging to the selected source. Unknown/cross-case IDs reject.
Claim `field` values are JSON Pointers into the referenced canonical artifact;
the claimed unit is checked against its enclosing quantity.

Context identity hashes canonical JSON of the required context fields excluding
`context_id` and `context_hash`. Immutable source content and selected quantities
must remain recoverable from audit export. Later disk edits cannot replace it.

OpenAI calls `/v1/responses/input_tokens` for the exact submitted request, then
reserves counted input plus the requested output allowance before generation.
Use `/v1/responses`, `store=false`, `background=false`, `stream=false`,
`truncation="disabled"`, no tools, and strict JSON-schema output. Responses arrive
asynchronously to the desktop even though the adapter uses ordinary HTTP requests.
Default output allowance is 4096 tokens, reduced to fit the remaining budget;
reject when no allowance remains. Count reasoning output in reported output usage.
Use a maximum 60-second provider request timeout bounded by the session deadline.
No SDK, transport or application automatic retries; no API calls at startup.

The provider response JSON has exactly:

```json
{
  "schema_version": "bh-ai-provider-output-v1",
  "kind": "explanation",
  "text": "Attributable explanation",
  "rationale": "Concise explicit rationale",
  "changes": [],
  "claims": [],
  "requested_tools": [],
  "done": true
}
```

`kind` is `explanation` or `proposal`; a change has `object_id, parameter, before,
after`, with explicit finite `{value, unit}` quantities. A claim has
`artifact_id, field, value, unit`; its referenced authoritative field must match
or the response is flagged `CONTRADICTORY_CLAIM`. Free prose is never a kernel
value. Unknown references are `UNVERIFIED_CLAIM`. `requested_tools` contains only
the strings `validate`, `run`, `inspect`; these are non-executable requests checked
against the approved plan. No provider-hosted tools are enabled. For each accepted
candidate the orchestrator performs at most one ordered validate/run/inspect
sequence, counting each admitted application operation. Invalid candidate changes
consume an iteration and zero runs. Repeated/excessive/forbidden tool requests
cannot trigger extra effects and produce `TOOL_NOT_ALLOWED` or `BUDGET_EXHAUSTED`.
`done=true` finishes after processing the response; otherwise another candidate
turn may start within every remaining limit.

Malformed output, refusal, mismatched model identity, missing usage, provider
failure or capability change stops the session with retained evidence. Unknown
usage keeps the whole reservation; missing usage is never recorded as zero. A
denied candidate can be followed by a different candidate when `done=false`; that
is a new budgeted iteration, not an automatic retry of an external request.

## 5. Exploration execution and audit

The approval screen binds the exact source, bounds, budget, provider/model and
feedback categories to `plan_hash`. Starting authorizes only that plan. It is a
bounded authorization to invoke the ordinary validation/run coordinator, not an
approval of a case, model or result. The user can cancel at any time.

Allocate a distinct exploration draft/case identity per session and a distinct
revision per candidate. Each candidate starts from the captured source rather than
silently accumulating the preceding trial's changes. Preserve original provenance
and all scientific labels.
Fixed topology/model/backend identity is checked against the captured source at
every admission. Source-draft edits do not stop the isolated session; set
`source_stale=true`. Backend disappearance or changed capability fails visibly.
Neither ordinary last-valid selection nor the engineer's active overlay may move
as a side effect of exploration. Adoption creates a new unapproved Review proposal
against the current target, retains exploration provenance, and requires normal
validation after applying. Narrative-origin evidence cannot be laundered this way.

Elapsed time starts at admitted plan start and includes provider/worker waits.
Iterations count generation attempts (including rejected candidates); runs count
admitted attempts, even failed ones. Denied application tool requests count toward
the tool ceiling. Cancellation/reconciliation are control operations and cannot
be denied because the work budget is exhausted. At a deadline stop new work and
request cancellation; retain an outstanding operation as uncertain until its
actual terminal state is known. Do not falsely claim a remote process stopped.

Canonical audit records live under `<data_root>/ai-audit/`. Write/verify the context,
approval, action identity and reservation before dispatch. A failed write prevents
the effect; lost acknowledgement never authorizes replay. Late outputs remain
auditable without being applied. Rebuild indexes from canonical records.

Each record has `schema_version="bh-ai-audit-v1", session_id, sequence,
previous_hash, kind, actor_id, created_at, body_json, record_hash`. Sequence starts
at 1, first previous hash is empty. `record_hash` is SHA-256 over compact sorted-key
UTF-8 JSON of all fields except `record_hash`, with `ensure_ascii=False` and finite
JSON numbers. `body_json` is canonical JSON text. Export verifies chain and artifact
hashes and rejects corruption (`AUDIT_CORRUPT`) rather than repairing history.
Required event kinds include `context`, `submission`, `response`, `proposal`,
`human_decision`, `plan_approval`, `reservation`, `dispatch`, `usage`, `candidate`,
`run`, `terminal` when those events occur. A `run` body includes `run_id, case_id,
profile, worker_pid, artifact_hash` and the four independent scientific statuses.

## 6. Native UI contract and failure codes

Use accessible object names for stable interaction tests:
`ai-dock`, `ai-composer`, `ai-send`, `ai-stop`, `ai-status`, `ai-profile`,
`ai-context-preview`, `ai-proposals`, `ai-approve`, `ai-reject`, `ai-apply`,
`ai-start-exploration`. The profile combo uses the three uppercase profile names.
The composer is a multiline `QPlainTextEdit`; Enter inserts a newline and the Send
button is keyboard reachable. Model output uses non-executing text rendering.
`ai-status` is a `QLabel` with the exact session state in its text. Buttons dispatch
the same commands as other surfaces. `ai-context-preview` captures the current
selection after flushing pending inspector edits. The panel shows original and
proposed values/units and never silently autocorrects engineering tokens.

Stable rejection/terminal diagnostic codes required by tests:
`PROVIDER_NOT_CONFIGURED`, `PROVIDER_FAILURE`, `PROVIDER_REFUSED`,
`PROVIDER_OUTPUT_INVALID`, `PROVIDER_USAGE_UNKNOWN`, `PROVIDER_MODEL_MISMATCH`,
`STALE_CONTEXT`, `STALE_PROPOSAL`, `APPROVAL_REQUIRED`, `FORBIDDEN_AUTHORITY`,
`NARRATIVE_PROMOTION_FORBIDDEN`, `PARAMETER_OUT_OF_SCOPE`, `PARAMETER_OUT_OF_BOUNDS`,
`INVALID_UNITS`, `BUDGET_EXHAUSTED`, `TOOL_NOT_ALLOWED`, `DOCUMENT_TEXT_UNAVAILABLE`,
`DOCUMENT_LIMIT_EXCEEDED`, `AUDIT_WRITE_FAILED`, `AUDIT_CORRUPT`.
Existing `INVALID_COMMAND`, `NOT_FOUND` and `REQUEST_ID_CONFLICT` retain their meaning.
Constructor rejection of nonfinite quantities is also acceptable before dispatch.

## 7. Verification and acceptance

Run the reviewer-owned package using its recorded SHA-256 trust anchor. All
mandatory tests must collect and pass; skips, xfails, missing tests, altered files,
early termination and absent Qt are failures. Existing repository checks also
remain required. The harness controls provider HTTP, time and credential boundaries,
not engineering results. It observes real worker processes and checks exported
canonical artifacts independently. Normal launch must use the tested factory.

An initial run is expected to fail on missing production capabilities. Package
self-tests exercise the runner and deliberately damaged observations; they are
not evidence that DW6 works. Until an implementation exists, deeper tests have
not executed past their missing-capability prerequisite.

Final acceptance also requires a macOS native keyboard/accessibility witness,
an explicitly initiated live OpenAI check using synthetic data and the selected
model, and independent implementation/specification review. No credentials or
live API calls are needed to run the deterministic suite. Remote branch protection
must be inspected/configured separately before claiming an enforced GitHub gate.
This Python harness protects against accidental gate weakening; it is not a
sandbox for malicious candidate Python code.

Primary implementation references checked 2026-09-16:
[structured output](https://developers.openai.com/api/docs/guides/structured-outputs),
[input-token counting](https://developers.openai.com/api/reference/typescript/resources/responses/subresources/input_tokens),
[provider data controls](https://developers.openai.com/api/docs/guides/your-data),
[PDF extraction](https://pypdf.readthedocs.io/en/stable/user/extract-text.html).
Recheck provider contracts when adopting an exact dependency/model. `store=false`
does not promise zero provider retention. No training or secondary-data use is
authorized by this package.
