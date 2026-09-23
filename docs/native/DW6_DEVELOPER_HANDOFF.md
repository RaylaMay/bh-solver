# DW6 developer handoff — tests before implementation

Date: 2026-09-16. Owner: Rayla May. Prepared by Codex.
Status: **ACCEPTANCE PACKAGE PREPARATION; DW6 PRODUCT IMPLEMENTATION REMAINS**.

## Start here

Read [the acceptance specification](DW6_ACCEPTANCE_SPEC.md), the existing native
action plan and its normative reading list. Inspect the current source before
editing. The pre-DW6 main checkout was at
`a0d3281aee909914cdf82a6f35ef4550f0b29604` with substantial uncommitted earlier
work. The [intake inventory](evidence/dw6-handoff/intake.json) identifies its bytes;
checking out HEAD alone does not recreate that baseline.

The native launcher still uses preview calculation ports. The rejected DW4/DW5
candidate was not integrated into this checkout. Complete and accept DW4/DW5
before claiming real-worker DW6 integration. Preserve the existing kernel,
reference-fixture labels, native history and browser baseline.

## Deliver in bounded increments

1. Reconcile the source and accepted DW4/DW5 worker/artifact contracts. Report any
   incompatibility with this frozen contract; do not silently weaken its tests.
2. Implement the neutral AI contracts and shared commands, profile propagation,
   immutable context/audit and atomic exact-target ChangeSet application.
3. Implement the asynchronous text workspace, local text/PDF ingestion,
   spellcheck/dictionaries, credential port and first OpenAI adapter.
4. Implement approved bounded exploration with isolated case/result identity,
   durable reservations, fault containment, cancellation and no-replay recovery.
5. Connect all paths to the ordinary production launcher and real worker; complete
   deterministic acceptance, native witness, synthetic live-provider check and
   implementation review. Hand onward a reproducible evidence package.

The executable [reviewer package](../../handoffs/dw6/README.md) is prepared before
those increments. It intentionally fails against missing DW6 capabilities. Its
tests, fixtures and runner are owner/reviewer-controlled. Proposed corrections
need a documented reason, owner/reviewer disposition and a new freeze digest.
Never replace a failed assertion with a skip, xfail, fake service or generated
expected value derived from the candidate output.

## Implementation obligations

- Extend the existing command/history seams. Keep Qt out of application/scientific
  policy and provider packages out of the kernel. The production factory accepts
  only the external replacements documented in the specification.
- Preserve profile and scope from native document through validation identity,
  worker input, result/audit and reopen. Existing `DraftDto` conversion fixes
  Review; simply removing the registry's profile guard is insufficient.
- Exploration gets a separate case/result scope. Existing last-valid queries
  operate by case ID, so sharing the baseline case would contaminate its selection.
- Validate proposals against the actual before/after diff and commit atomically.
  Preserve user edits, failed attempts, source bytes and former approvals.
- Keep protocol DTOs separate from provider SDK objects. Pin reviewed optional
  dependencies without moving them into the default kernel. Record code, data,
  dictionary, model and distribution implications separately.
- Scope provider timeout/cancellation to the session. Zero retries applies inside
  SDKs and transports as well as the orchestrator. Do not bill unknown usage as zero.
- Record limitations honestly: structured claim checks cannot prove arbitrary
  prose correct; test fixtures cannot approve science; no remote-service retention
  guarantee follows from disabling response storage.

## Required acceptance evidence

Run the frozen suite from an external reviewer copy against the exact candidate.
Use the digest and command recorded in [the preparation record](DW6_HANDOFF_RECORD.md).
Retain complete collection, outcomes, package/candidate hashes and logs. Production
native/worker tests may not be substituted with a fake gateway or an in-process
scientific engine. Record every failure/skip; a missing prerequisite is not a pass.

Also run the repository's full Python tests, Ruff lint/format checks, Pyright,
`tools/check_project.py`, `git diff --check`, package build and browser test/lint/build.
The exact applicable commands appear in the DW4/DW5 handoff and package README.
Complete the native/live-provider witness template in the package with synthetic
data, reviewer identity, source/package hashes, model identity, actual outcomes
and unresolved defects. A form or CI YAML alone is not execution evidence.

For each increment update the existing contracts, architecture, dependency and
failure records, requirements matrix and milestone status, using Appendix A.
Do not label all of DW6 VERIFIED from a subset of tests. Scientific promotion,
speech, multiple participants, unrestricted tools and additional provider adapters
remain separate work.

## Recovery and onward handoff

Disable AI capability to return to the ordinary workstation; preserve every new
audit record and exploration artifact. Do not overwrite old source artifacts or
rewrite historical evidence. A version migration writes a new attributable artifact.

The onward handoff must state exact source state and dirty overlap, accepted
contracts, commands, dependencies, tests actually run, failures, known limits,
native/provider witness, reviewer disposition and the next bounded task. It must
separate software acceptance from scientific approval. No commit, push or merger
is authorized merely by possession of this package.
