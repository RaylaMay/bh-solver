# DW4/DW5 remediation — third code review

Date: 2026-09-16. Reviewer: Codex, with separate Standards and Spec review agents.
Disposition: **FAIL — do not integrate, commit or push this candidate.**

## Outcome and authorized scope

The supplied suite passes all 215 tests, and several previous defects are fixed.
Fresh fault and lifecycle probes nevertheless demonstrate six substantive findings:
three Standards findings and three Spec findings. The harness walkthrough's blanket
PASS is not supported. This review changes no implementation in either project.
The user's authorization to commit and push was conditional on passing review;
that condition is not met. No source-project commit or GitHub push was performed.

BH remains concept-development software. This is a software review, not scientific
model validation, engineering-design approval, or qualified independent V&V.

### Source identity and baseline

Both original folders are dirty `main` checkouts at
`a0d3281aee909914cdf82a6f35ef4550f0b29604`. The selected baseline is this workspace's
working files, including its newer DW1/DW6 records, rather than that commit alone.
Runtime stores were excluded from temporary review snapshots.

- Workspace baseline snapshot: `9eae8030d34567b66f8bacfd61687fe99876a3c1`.
- Incoming candidate snapshot: `34e64c59d3bbecf42b89d4b6363fe491a4136717`.
- Fixed comparison: `git diff 9eae8030d34567b66f8bacfd61687fe99876a3c1...HEAD`.
- Commit list: `34e64c5 Review-only incoming DW4 DW5 remediation candidate`.
- Comparison: 48 files, 7,716 insertions, 288 deletions. Candidate-only files are
  included; baseline-only files are retained in the review environment.

These snapshot commits exist only in a temporary review repository. They are not
commits in either original project. The [manifest](evidence/dw4-dw5-third-review-2026-09-16/manifest.json)
records original source hashes, relevant baseline hashes and evidence hashes.
Reviewed source and baseline files were rechecked unchanged after verification.
Code line numbers below refer to the incoming candidate in the other harness folder.

The [supplied implementation plan](evidence/dw4-dw5-third-review-2026-09-16/implementation-plan.md)
is the specific remediation specification. The
[walkthrough](evidence/dw4-dw5-third-review-2026-09-16/walkthrough.md) is inherited
verification testimony, checked against fresh results. Earlier
[review evidence](DW4_DW5_REREVIEW_2026-09-16.md), the originating
[handoff](DW4_DW5_DEVELOPER_HANDOFF.md), current contracts, failure policy, PFD
specification and native action plan remain applicable authority.

## Standards

**FAIL — three documented-standard violations.**

1. **P1 — Failed terminal-manifest writes cannot be repaired by retry.**
   `src/bh_sim/persistence/store.py:504–506` commits `index_attempt(attempt)` before
   `_write_attempt_manifest(winner)`. A failed RUNNING→COMPLETED manifest write
   leaves SQLite COMPLETED and JSON RUNNING. Retrying skips publication because
   the index already has a terminal winner; rebuilding SQLite restores RUNNING.
   This contradicts `docs/FAILURE_RECOVERY.md:17,27–32`: publish durable JSON before
   updating the disposable index. **The attached plan prescribes this ordering:
   implementation follows the plan, but the plan conflicts with the repository's
   recovery contract.** Correct transaction ordering without restoring the old
   rejected-identity overwrite defect.

2. **P1 — Worker loss silently selects local execution.**
   `src/bh_sim/application/services.py:177–200,217–220,272–287` treats a configured
   but dead supervisor as an in-process configuration. Session checks execute only
   inside `if is_supervised`. A production-child probe—Validate, stop worker, Run
   using its receipt—completed durably through the local adapter without diagnostics.
   This violates worker ownership in the handoff (`90–94`) and worker-loss recovery
   in `docs/FAILURE_RECOVERY.md:58`. Report unavailable capability and renegotiate
   the worker before accepting execution.

3. **P1 — In-process persistence failure leaves an unfinished attempt.**
   `src/bh_sim/application/services.py:409–422` calls `save_run(terminal)` outside
   the execution-failure handler; cleanup only clears `_active_run_id`. An injected
   `OSError` leaves RUNNING with no terminal timestamp or failure reason after
   execution stops. `docs/CONTRACTS.md:292–295` requires an auditable terminal
   outcome for every allocated attempt. Record storage failure and preserve the
   completed result's identity for reconciliation.

Nonblocking judgement: possible **Duplicated Code** in
`worker/entry.py:create_default_adapter` and `composition.py:create_services`.
Both construct the same catalogue/property/runtime context inventory. A shared
inventory builder would reduce context-hash drift. This is a suggestion, not a
documented-standard violation.

**Standards: 3 hard findings, worst P1; 1 nonblocking smell suggestion.**

## Spec

**FAIL — two P1 findings and one P2 finding.**

1. **P1 — Cancelled in-process runs still publish successful results.**
   `src/bh_sim/application/services.py:409–420` saves results without checking the
   winning cancellation state. The handoff requires “one authoritative terminal
   disposition” and late messages “without overwriting the winning outcome”
   (§DW4-C). Cancelling a running solve subsequently returned COMPLETED, left its
   attempt CANCELLED with `persisted=True`, and advanced last-valid selection in a
   fresh empty store. Check cancellation before publication on both execution paths.

2. **P1 — Ordinary child cancellation has no bounded interruption.**
   `src/bh_sim/worker/entry.py:228–237` executes synchronously inside its message
   loop; `src/bh_sim/adapters/worker_supervisor.py:275–286` schedules escalation
   only with `force=True`. The handoff requires: “If a backend cannot cooperate,
   enforce a bounded escalation” (§DW4-C). A real child with a two-second delayed
   adapter returned Cancel promptly but continued solving for approximately
   another 1.86 seconds. The ordinary request cannot be read until execution ends;
   a stuck backend waits for the separate run timeout. Provide a control path and
   bounded escalation. The probe's 300 ms observation is not a product deadline.

3. **P2 — Saving an engineering edit removes the stale-result warning.**
   `src/bh_sim/uix/workstation_editor.py:779` derives result staleness from document
   dirtiness. The PFD specification requires stale states to remain visibly
   distinct. Run at 75 kW → edit duty to 125 kW → Save removes the stale label while
   retaining the old run/workbook, without another solve. Compare engineering
   identity with the result's source identity; Save must not clear the mismatch.

**Spec: 3 findings; worst P1, including cancelled results advancing last-valid.**

## Confirmed improvements and evidence limits

- The four current DW5 acceptance tests pass, including originating-tab routing,
  four-status scientific-failure overlay retention and immediate receipt
  invalidation after parameter edits. These tests instantiate the gateway without
  a supervisor, so they establish in-process UI behavior.
- Replayed earlier persistence/session probes confirm normal terminal-manifest
  rebuilding, rejection of empty staged paths, and rejection of receipts after a
  worker restart. Worker shutdown without restart exposes the remaining fallback.
- The new protocol-version quarantine test passes as part of the full suite.
- DW4/DW5 change records now describe the length-prefix framing and INTERRUPTED
  reconciliation accurately. This does not establish full lifecycle acceptance.

## Verification performed here

Runtime: macOS 26.6.2 arm64; Python 3.13.12; pytest 8.4.2; Ruff 0.16.4;
Pyright 1.1.411; PySide6-Essentials 6.11.2. Tests used the existing runtime and a
frozen temporary candidate. No dependency installation was needed.

Commands below ran from the candidate root. Python probe runs also set
`PYTHONDONTWRITEBYTECODE=1`. Evidence files normalize incidental local paths;
their numerical outcomes and original source identities are retained.

| Command | Fresh result |
|---|---|
| `PYTHONPATH=src QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q` | 215 passed, one Starlette deprecation warning, 30.19 s |
| `.venv/bin/ruff check --no-cache src tests tools` | Passed |
| `.venv/bin/ruff format --check --no-cache src tests tools` | Passed, 112 files |
| `PYTHONPATH=src .venv/bin/pyright --pythonpath .venv/bin/python` | 0 errors, warnings or informations |
| `.venv/bin/python tools/check_project.py` | Passed, 184 baseline Git objects, historical bytes unchanged, 407 public file links |
| `git diff --check 9eae8030d34567b66f8bacfd61687fe99876a3c1...HEAD` | Exit 2: trailing whitespace in incoming `docs/PROJECT_CONTINUATION_PROMPT.md:3` |
| `PYTHONPATH=src:tests .venv/bin/python ../evidence/standards-probe.py` | Reproduced manifest retry/rebuild and unfinished-attempt defects |
| `PYTHONPATH=src:tests .venv/bin/python ../evidence/dead_worker_probe.py` | Reproduced silent local execution after real worker shutdown |
| `PYTHONPATH=src:tests .venv/bin/python ../evidence/bh_review_spec_cancel.py` | Reproduced cancelled-result publication and delayed child cancellation |
| `PYTHONPATH=src:tests QT_QPA_PLATFORM=offscreen .venv/bin/python ../evidence/bh_review_spec_stale.py` | Reproduced Save clearing stale display |
| `PYTHONPATH=src:tests .venv/bin/python docs/native/evidence/dw4-dw5-rereview-2026-09-16/remaining_probes.py` | Three earlier regression probes now show corrected behavior |

The original old UI probe was also attempted with the offscreen environment. It
stopped with `AttributeError` because it assumes the old bug retains a receipt;
the receipt is now correctly cleared. It is recorded as an incomplete probe, not
as a product failure or a passing full UI check. Current acceptance tests and new
focused probes supply the relevant evidence.

Logs and runnable probes are in the
[evidence directory](evidence/dw4-dw5-third-review-2026-09-16/manifest.json), including
[pytest](evidence/dw4-dw5-third-review-2026-09-16/pytest.log),
[standards faults](evidence/dw4-dw5-third-review-2026-09-16/standards-probe.log),
[worker shutdown](evidence/dw4-dw5-third-review-2026-09-16/dead-worker-probe.log),
[cancellation](evidence/dw4-dw5-third-review-2026-09-16/spec-cancel.log), and
[stale display](evidence/dw4-dw5-third-review-2026-09-16/spec-stale.log).
The [Spec probe notes](evidence/dw4-dw5-third-review-2026-09-16/spec-probe-commands.md)
explain the synthetic delay and canonical last-valid lookup. All injected faults
used disposable stores; real-child probes stopped their own workers.

Native Cocoa/VoiceOver witness, cross-platform execution, packaging, browser
tests/build and renderer benchmarks were not repeated: confirmed blockers already
prevent integration. Browser source is unchanged in this comparison. No omitted
check is treated as a pass. DW6's deliberately pre-implementation acceptance suite
is outside this DW4/DW5 review.

## Baseline preservation, questions and next bounded work

The incoming folder lacks this workspace's newer DW1/DW6 authority text. Its files
would remove ADR-012 and later sections from architecture, contracts, vocabulary,
failure policy, requirements and other documents. Its milestone additions would
replace the DW6 disposition. These are integration conflicts with newer baseline
work, not evidence that the harness intentionally reversed those decisions.
Preserve the current documents and integrate only reviewed DW4/DW5 additions in a
future passing candidate. The extra link count reflects retained baseline records;
338 is not the correct total for the current combined review tree.

Recommended next work units:

1. Correct the persistence plan against the existing JSON-authoritative contract.
   Test rejected updates, write failure, same-content retry and index loss together.
2. Separate configured execution mode from worker liveness. A lost configured
   worker must fail visibly and require current-session validation after recovery.
3. Apply one cancellation/publication policy to both execution paths. Add real
   child cancellation/escalation tests and terminal storage-failure tests.
4. Derive displayed staleness from engineering source identity, including Save,
   undo/redo and presentation-only changes. Preserve the fixed tab/overlay tests.
5. Resubmit with corrected evidence claims and a selective documentation merge.

Open owner/steward questions: what worker ownership/reconnection behavior is
required after UI crash versus intentional Quit, and what cancellation grace
period and escalation policy should be documented? These choices do not justify
silent fallback or promotion of a cancelled result. Resolving the demonstrated
contract violations does not require changing scientific models.

Review setup note: `docs/agents/issue-tracker.md` is absent. The code-review skill
recommends `/setup-matt-pocock-skills` for issue-linked reviews; the supplied plan
and handoff provided the specification here, so that absence did not block review.

Only this report and its evidence directory were added. No schema, dependency,
licence, scientific or runtime behavior was changed by the review. Rollback removes
only these new review artifacts; retain earlier reports and both source trees.
Receiving sessions should verify the manifest against the actual candidate before
reusing these findings or checks. Acceptance remains conditional on corrected
code, fresh failure-path evidence and another review.

**Summary: Standards 3 hard findings, worst P1; Spec 3 findings, worst P1.**
