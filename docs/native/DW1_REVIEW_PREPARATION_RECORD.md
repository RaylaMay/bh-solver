# DW1 documentation-first review preparation record

Date: **2026-09-16**. Contributor: **Codex**. Project/profile: BH solver.
Status: **PREPARED; IMPLEMENTATION REVIEW AND REWORK NOT EXECUTED**.

## Objective and instruction

Rayla May requested a DW1 review beginning with documentation rather than code,
taking account of project goals and engineering rigor, producing a comprehensive
test batch followed by a rework batch. This work prepares the acceptance
specification and sequenced corrective-work handoff. No implementation was read,
tested or repaired in this round. File paths/status and opaque file hashes were
inspected for scope and continuity only.

An optional clarification was sent about preparation-only versus immediate
execution. In the absence of further steering during preparation, the explicit
documentation-only instruction determines this round's boundary. Code review,
executable test implementation and repairs remain the next work unit.

## Project boundary and source state

BH is local-first concept-development software for the documented reference
steady flowsheet and legacy demonstrations. Scientific truth remains with the
kernel; native UIX, HTTP and CLI use neutral contracts and application services.
No model, engineering design, industrial use or release acceptance is granted.

Intake branch: `main`. HEAD: `a0d3281aee909914cdf82a6f35ef4550f0b29604`.
There were no staged changes. Numerous later documentation/source modifications
and untracked work already existed; full status and 310 selected file hashes are
recorded in the [intake manifest](evidence/dw1-review-plan-2026-09-16/intake.json).
The manifest captures identity, not a backup or code-review result. It excludes
runtime stores, private handoffs, personal notes, installed dependencies and build
outputs. Live changes outside this work unit were observed in the untracked DW6
handoff file inventory; no such files were edited or read by this work.

The final preservation check also detected concurrent DW6 additions to governing
documents and changes to the DW6 acceptance specification. The first check stopped
on these unexpected hash changes. Documentation diffs and relevant specification
references were inspected: ADR-012 adds scoped human-authorized exploration and a
test-first DW6 handoff, without changing DW1's canonical/receipt/compatibility
contracts. All concurrent changes were preserved; the final verification record
lists them separately from this work's edits. It does not claim those documents
remained byte-identical throughout the session.

Overlap: the existing `docs/README.md` was already modified by earlier work;
this work adds only links under its DW1 supporting records. Shared application
registry and neutral boundary files already contain later changes; the proposed
review must preserve them. No applicable `AGENTS.md` was found in the inspected
ancestor chain or repository file inventory.

## Authority and evidence inspected

Read completely: the supplied continuation prompt; engineering-continuity skill;
root README; docs README, VOCABULARY, ARCHITECTURE, DECISIONS, CONTRACTS,
MODEL_LIFECYCLE, PFD_SPECIFICATION, FAILURE_RECOVERY, DEPENDENCY_REGISTER,
REQUIREMENTS_VERIFICATION, MILESTONES, INDUSTRY_DEVELOPMENT_STREAM and
NATIVE_WORKSTATION_ACTION_PLAN (including Appendix A).

Also read: DW1_BOUNDARY, DW1_CHANGE_RECORD, the DW1 fixture README, DW0_REVIEW,
DW0_OWNER_DISPOSITION, BROWSER_PARITY, PUBLIC_BASELINE_TRANSITION, the historical
DW1 verification log and DW4_DW5_REREVIEW_2026-09-16. Implementation references
inside these documents are inherited claims; their linked source was not opened.
Later concurrent governing-document additions were read as documentation diffs;
DW6's changed specification was searched only for relevant boundary references.

References: ADR-001–010; CORE-001–010 as relevant; BOUND-001; PFD-002–005;
UIX-ARCH-001/002, UIX-CMD-001, UIX-DOC-001/002; existing DW0 gap and DW1 records.
No new requirement IDs or approved policies are created.

## Findings from documentation, assumptions and evidence limits

- DW1 explicitly scopes eight synchronous commands, separate canonical/engineering
  identity, process-local receipts and in-process context/snapshot checks. Worker
  durability/cancellation and native results acceptance belong to later gates.
- The legacy HTTP Run path intentionally preserves its no-prior-receipt behavior;
  new commands must not inherit that bypass. Existing browser deficiencies are
  retained acceptance debt, not desired native behavior.
- Last-valid eligibility includes correlation `EXTRAPOLATED` when convergence,
  closure and physical validity qualify. The 144-case matrix is derived from the
  published enum sets and predicate, not inferred from code.
- Public sanitization qualifies historical DW1 records. Their old passing checks
  and surviving source hashes cannot authenticate the current dirty checkout.
- The recent DW4/DW5 failed review refers to a sibling candidate. Its findings are
  not transferred into a DW1 defect list for this checkout.
- Wire-field details, some receipt scope examples, fingerprint dependency coverage
  and parser hardening limits require binding/clarification during execution.
  The test specification explicitly distinguishes open oracles from failed tests.

No new confirmed implementation defect, empirical pass rate or qualified independent
review is claimed. Code and test bodies, historical checker scripts, physics/data
implementations and source patches were not inspected.

## Selected design and alternatives

Deliver a specification with 80 local test families, independent oracles, fault
injection, mutation sensitivity, traceability and per-case evidence; pair it with
eight gated rework units R0–R7. This keeps expected behavior independent of current
implementation and makes later corrections reviewable.

Alternatives rejected: guessing executable constructor/codec signatures from prose;
inspecting code despite this round's constraint; inventing defects to justify a
rework patch; repeating historical checks as fresh evidence; broad refactoring or
merging the sibling candidate. Tradeoff: executable tests and actual defect evidence
remain next-round work rather than being falsely represented as delivered now.

## Files changed and impacts

- [Test batch](DW1_REVIEW_TEST_BATCH.md): documentation-derived acceptance design.
- [Rework batch](DW1_REWORK_BATCH.md): ordered, failure-driven correction instructions.
- This preparation/change record and its intake/verification evidence.
- [Documentation index](../README.md): links to this package.

Schema/migration: none. Dependency/licence: none. Security/privacy: no external
provider, network request or private case use; portable records use relative paths.
Scientific/validity: no equations, quantities, status policy or model approvals
changed. Existing requirement and milestone acceptance statuses remain unchanged.

## Verification performed in this preparation

Methods: Git status/branch/HEAD/staged-stat inspection; complete documentation reads;
path inventory; selected file SHA-256 capture with standard-library Python; local
link, test-ID, fence, traceability-reference and preservation checks of this new
package; `git diff --check` for the changed index. Exact observations and environment
are retained in the [verification record](evidence/dw1-review-plan-2026-09-16/verification.json).

These checks verify document structure and preservation only. No pytest, product
lint/type/build, CLI calculation, scientific calculation, current/historical project
checker, GUI, worker, browser, model V&V or cross-platform test was run. They require
the next execution round; their absence does not become a PASS. No subagents or
independent reviewers contributed to this preparation.
The initial preservation-check failure was caused by concurrent document edits,
not by a product test failure; it is retained in the verification record.

## Recovery and next bounded task

Rollback: remove only this package's new files/evidence after checking for subsequent
edits, and remove only its added index entries. Preserve all prior dirty/untracked
work, historical evidence and runtime stores. No Git commit, reset, clean, stash,
integration or publication was performed.

Next task: execute R0 and bind the documentation-derived tests to the current public
interfaces, then review the candidate and apply only evidence-supported rework.
Acceptance: complete per-test disposition, exact source/evidence identity, critical
authority/persistence/status tests and required regression checks; no unresolved
mandatory failure concealed by fixture changes or skipped cases.

Owner/steward decisions: none needed for preparation. Only genuine ambiguous or
incompatible contract changes need the named contract authority; scientific changes
retain their separate model lifecycle. Reviewer assignment/qualification must be
recorded before claiming independent acceptance. Receiving sessions must reconcile
the intake manifest against current files before proceeding.
