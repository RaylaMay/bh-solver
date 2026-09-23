# DW1 rework batch — apply after the review evidence

Date: **2026-09-16**. Prepared by: **Codex**, at Rayla May's request.
Status: **PREPARED; NO IMPLEMENTATION REWORK APPLIED**.

This is the corrective-work sequence for the
[DW1 test batch](DW1_REVIEW_TEST_BATCH.md). Code has not been inspected in this
round, so there are no newly confirmed DW1 implementation defects to repair yet.
Each work unit below activates only for demonstrated failures in its area. If its
tests pass and source review finds no violation, record **NO REWORK REQUIRED**.

The requested documentation-first round is complete when these two batches are
reviewable. The subsequent execution round binds the tests to public interfaces,
reviews the existing code, records failures, implements supported corrections and
reruns the relevant checks. Preparing this sequence does not mean repairs have
already occurred or that DW1 has passed review.

## 1. Rules for applying the batch

1. **Freeze before fixing.** Preserve the current dirty checkout and relevant
   untracked files in a recoverable isolated snapshot. The planning
   [intake manifest](evidence/dw1-review-plan-2026-09-16/intake.json) is an identity
   record, not a backup. Reconcile new changes before using it. The current
   working project, not the sibling DW4/DW5 candidate, is the default target.
2. **Establish evidence before implementation changes.** Run baseline checks,
   implement the documentation-derived test cases and inspect code. Record the
   review's findings before repairs, with a minimal failing reproduction or a
   specific static contract violation. Baseline failures remain visible.
3. **Keep requirement authority fixed.** Test expectations come from the test
   batch's cited contracts. Existing code may identify public names and fixtures;
   it cannot redefine the expected behavior simply because a test fails.
4. **Fix the smallest responsible boundary.** A unit/serialization defect does
   not authorize a service rewrite, UI redesign, physics change or wholesale
   source move. Preserve later additive work and user-owned changes.
5. **Record every applicable defect once.** Use the existing
   [milestone backlog](../MILESTONES.md) for work tracking. Add one dated DW1
   execution/rework record linked from its existing DW1 section; that record may
   contain the detailed finding ledger. Do not create a second standing backlog.
6. **Preserve a red/green chain.** Record the failing test on the frozen before
   state, the exact correction, passing targeted evidence and impacted regression
   results. A test changed to match the candidate needs explicit oracle rationale,
   not just a new expected value.
7. **Stop only the affected change at a real gate.** Ordinary corrections to
   accepted DW1 behavior need no renewed DW0 approval. Incompatible contracts,
   new scientific behavior or an unresolved policy choice use their existing
   steward/model gates. Continue independent fixes and checks.

No commits, publication, merging of sibling work, dependency upgrades, browser
retirement or user-artifact migration are implied by this rework plan.

## 2. Review and repair order

```text
R0 freeze and bind oracles
 -> R1 contracts and dependency boundaries
 -> R2 registry and draft behavior
 -> R3 receipts, hashes and execution context
 -> R4 persistence and failures
 -> R5 result selection and comparison
 -> R6 compatibility and later-contract integration
 -> R7 fresh review, evidence and handoff
```

Perform the initial review across all test families before hiding any failure
behind a repair. Within implementation, respect these dependencies. A change to
an earlier boundary reopens the affected downstream tests; unchanged passing
checks need not be repeated until the final regression gate.

### R0 — establish a reproducible review baseline

**Entry:** documentation-first specification available; execution scope established.

**Work:**

- Re-read current authority if its hashes changed. Identify all later modifications
  to shared DW1 files without discarding them.
- Create the isolated source snapshot, fixture manifest and exact environment
  record; keep actual project runtime stores out of testing.
- Map T001–T080 to existing tests, new tests and manual observations. Existing
  coverage earns credit only when its assertions prove the stated oracle.
- Bind public names and diagnostic codes after reading current declarations.
  Resolve only the specific open oracle when necessary; do not infer a policy from
  implementation. Parameter cases must appear in evidence, not be silently dropped.
- Record baseline tool failures before touching source. Inspect historical and
  current integrity tools before execution; preserve the public-transition record.

**Candidate files:** existing `tests/` modules/fixtures, new review tests within
that tree, one dated execution record and its evidence directory. No source repair
belongs to R0.

**Exit:** T001–T004, T075 mapping ready; test collection is nonempty, oracles have
authority, and every unresolved oracle has a named owner and bounded impact.

### R1 — repair neutral types, codec and dependency violations

**Trigger:** T005–T018 or T072 reveals a concrete violation.

**Permitted corrections:**

- Make public DTO values deeply immutable; defensively preserve caller ownership
  at the construction/serialization boundary. Retain existing value semantics.
- Reject malformed versions, tagged types and numeric representations before
  dispatch, including direct Python callers where applicable.
- Keep neutral quantity transport separate from scientific unit conversion.
- Move misplaced orchestration/concrete imports behind existing declared ports;
  keep root exports lazy and compatibility wrappers intact.
- Document non-obvious codec and import rules at their actual ownership boundary.

**Likely affected families, subject to inspection:** `boundary/`, application port
declarations, package exports, adapters and composition wiring. Do not rename or
move the whole package. Later DTO tags must stay registered where supported.

**Exit:** T005–T018 pass, frozen DW1 command/canonical fixtures unchanged, and
direct-construction plus fresh-process isolation checks demonstrate the repair.
New parser limits or incompatible rejection behavior need an explicit contract
disposition; do not choose arbitrary limits from this plan.

### R2 — repair dispatch, deduplication and draft policy

**Trigger:** T019–T032 or T066 finds a dispatch, attribution, conversion or
side-effect-order violation.

**Permitted corrections:**

- Ensure exactly matching request IDs/content return the recorded terminal outcome
  within the documented session, and conflicting content never invokes a handler.
- Keep unsupported profiles/capabilities explicit. Actor fields stay attribution;
  do not add an improvised authentication or engineering-approval scheme.
- Make save/open/validate effects match their separate use cases. Preserve
  immutable/idempotent saves and validation without implicit persistence.
- Correct lossless legacy mapping, occurrence handling and extension/overlay
  separation while retaining authoritative compiler rejection of invalid graphs.
- Prevent new command callers from reaching the legacy HTTP receipt bypass.

**Likely affected families:** application registry/services, draft/HTTP adapters
and codec only as implicated. No durable registry store or concurrency protocol
is required by DW1.

**Exit:** T019–T032 pass with exact call histories; relevant HTTP/CLI golden traces
pass. A successfully handled scientific failure remains distinct from command
rejection. The compatibility route has an explicit confined test.

### R3 — repair validation authority, identity and context binding

**Trigger:** any failure in T033–T048. Prioritize this work before enabling new
execution routes because it determines which input/context may be run.

**Permitted corrections:**

- Restore the exact engineering projection: omit only title and unit names,
  retaining all other canonical fields and order. Never change canonical artifact
  hashing to make presentation reuse work.
- Trust service-retained receipt state only. Recompute current submitted identities
  and reject missing, stale, invalid, unknown and cross-draft authority before
  writes/evaluation.
- Retain valid receipt use for presentation-only changes while linking the result
  to the actual submitted source artifact. Do not execute old source labels by
  accident.
- Fingerprint the actual relevant code/catalogue/property context. Missing identity
  evidence fails explicitly; no schema-string or backend substitution fallback.
- Preserve the post-input-persistence context recheck and evaluate a private
  snapshot matching the validated context. Use deterministic tests at both sides
  of the persistence race.

**Likely affected families:** validation service, engineering adapter, projection
and context helpers, composition configuration. No worker-session or distributed
admission redesign belongs here unless a later separately scoped review requires it.

**Exit:** T033–T048 pass against the independent projection oracle, all rejected
pre-admission cases have zero writes/evaluations, the documented partial-save race
is preserved accurately, and legacy canonical bytes remain unchanged.

### R4 — repair persistence acknowledgement and failure containment

**Trigger:** T049–T056 identifies false success, evidence corruption, loss of
previous immutable state or untyped/leaking diagnostics.

**Permitted corrections:**

- Return durable success only after the appropriate repository operation succeeds;
  calculation completion alone is insufficient.
- Keep prior artifacts and last-valid selection unchanged on write/index failures;
  retain and identify any permitted partial/orphan immutable artifact.
- Preserve existing failed scientific results and expose pre-adaptation failures
  honestly. Do not manufacture a successful run or completed manifest.
- Correct identity/hash verification at the responsible existing storage boundary.
- Sanitize public error details while preserving stable diagnostics, known subject
  identity and useful original-cause information.
- Ensure recovery/read paths cannot trigger validation, approval or evaluation.

**Likely affected families:** application run use case, engineering/storage/draft
adapters and existing repository methods. Durable admission, global crash recovery,
new manifest formats and automatic rebuild remain at their documented later gates.

**Exit:** T049–T056 pass with fault injection at each named persistence point,
before/after artifact hashes and repository-call traces. No attempt to meet this
exit may silently broaden DW1's durability claims.

### R5 — repair independent statuses, last-valid selection and comparison

**Trigger:** T057–T064 reveals status collapse, incorrect eligibility, missing
failed-result visibility or fabricated/misassociated comparison quantities.

**Permitted corrections:**

- Preserve all four independent dimensions through views, serialization and
  adapters. Command completion is not scientific acceptance.
- Apply the documented last-valid predicate consistently at its application/store
  authority, with no duplicate diverging UI policy introduced by the fix.
- Keep failed results inspectable and protect existing last-valid references.
- Make missing metric/unit state explicit; compare stored values by object/metric
  identity without generating cross-unit deltas or rerunning.

**Likely affected families:** result mapping, application inspection/comparison,
repository selection and neutral outcome types, only as needed. Native canvas,
graph and workbook fixes remain DW5 work.

**Exit:** all 144 status transport and eligibility cases pass; sequencing and
cross-case tests pass; comparison/read operations produce no writes/evaluation.
The suite must catch both rejecting allowed correlation extrapolation and
accepting disallowed physical extrapolation.

### R6 — preserve legacy behavior and later additive integrations

**Trigger:** T065–T071/T076 fails, or any earlier repair touches compatibility.

**Permitted corrections:**

- Restore HTTP aliases, response shapes, mappings, warnings and legacy Run ordering
  through thin adapters over application services.
- Preserve canonical bytes and approved normalization boundaries; investigate the
  difference rather than regenerating goldens.
- Restore CLI command names/arguments/stdout, lazy public exports and fixture-only
  labeling; retain prototype numerical behavior.
- Preserve later optional command discovery, old envelope decoding and additive
  DTO registrations. Attribute unrelated later feature failures to their milestone.

**Incompatible proposal:** document old/new behavior, exact schema/API effect,
affected readers, migration fixtures and rollback. Architecture steward approval
is needed before changing an accepted incompatible contract, under
[documentation governance](../README.md#governance). Meanwhile continue compatible
corrections. No approval is needed to restore already accepted behavior.

**Exit:** T065–T071/T076 and affected import/contract tests pass against unchanged
authenticated fixtures; original browser source and launch path remain available.

### R7 — final verification, independent review disposition and handoff

**Entry:** all activated corrections have targeted passing evidence; unresolved
gates and unactivated work units have explicit dispositions.

**Work:**

- Run critical mutation/sensitivity checks and the planned complete regression
  commands; capture actual node counts, skips, failures and process exit codes.
- Review the final diff for unintended equations, version/hash changes, weakened
  tests, swallowed failures, new dependencies and unrelated edits.
- Have a read-only reviewer revisit the exact final source and critical evidence
  when such a reviewer is assigned. Report reviewer identity/role and method.
  An implementer's subsequent review is self-review; a second AI session alone
  does not establish qualified independence or scientific V&V.
- Update the one dated execution record, milestone link and affected requirement
  evidence descriptions. Leave global status unpromoted where broader native,
  scientific or platform obligations remain open.
- Preserve old DW1 evidence. Add attributable corrections/limitations without
  changing historical logs or pretending old tests ran against the new tree.

**Exit:** T072–T080, all applicable acceptance cases and required regression checks
pass; final disposition explicitly separates software acceptance from scientific,
design and release gates. If anything prevents acceptance, report PARTIAL/FAIL
with exact remaining work; completed repairs can still be handed off honestly.

## 3. Finding and correction record

Use local identifiers such as `DW1-RV-001` in the dated execution record; these
identify findings, not new normative requirements. Route deferred work through
the existing milestone backlog.

```text
Finding ID / title / severity / affected requirement:
Observed source snapshot and file/line or public operation:
Expected behavior and authoritative document/section:
Reproduction test ID, command, input and actual behavior:
Consequence and side effects; evidence links:
Confirmed defect | baseline defect | oracle gap | later-stage work:
Selected correction, rationale and alternatives:
Changed files/contracts; compatibility and scientific impact:
Before-test result and after-test result, exact source identities:
Regression and test-sensitivity evidence; unperformed checks:
Reviewer, role, independence limits and disposition:
Residual risks, rollback and next acceptance gate:
```

Priority is consequence-based. Receipt bypass, false durable success, corrupted
immutable evidence, wrong-source execution and incorrect last-valid promotion are
acceptance blockers. Type/docstring/style findings should explain their real
maintenance or boundary risk; file length alone does not justify a rewrite.

## 4. Recovery, completion and onward handoff

Before each repair, keep an attributable patch and before-state for the affected
files in the isolated review area. Roll back only that work unit after checking
for newer changes. Never use broad reset/clean, remove current runtime stores or
overwrite later work to recreate the historical DW1 tree. Tests operate on copies
and synthetic stores; unchanged artifact schemas should need no user-data migration.

The final handoff must include:

- Exact source/dirty-state identity and all changed files, with overlap disclosed.
- Test-ID→requirement→finding→correction→evidence mapping and executed counts.
- Historical versus freshly observed results, and all blocked/skipped tests.
- Contract/dependency/privacy/scientific impacts and reviewer responsibilities.
- Unresolved decisions with their actual authority source, not generalized requests
  to approve DW1 again.
- A bounded next task, its prerequisites and acceptance criteria.

No Rayla May decision is needed to finish this documentation package. A future
execution may need a narrow contract clarification or the designated independent
reviewer. Neither uncertainty authorizes invented behavior or an acceptance claim.
