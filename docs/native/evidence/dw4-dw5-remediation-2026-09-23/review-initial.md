# DW4/DW5 remediation initial independent code review

Date: 2026-09-23. Reviewer: separate Codex review agent using `code-review`, with parallel Standards and Spec agents. This is software review, not qualified scientific or engineering V&V. No implementation files were changed by reviewers.

Reviewed clean candidate `014de19e03f9b6a3ab3bd94e3d706d98f032ac97` against fixed review-only baseline `81cb8a239a3cb8b6ddb4d69c97d8876b8fdfa68c`. Both resolve; the diff is nonempty. Original project histories were untouched.

- Diff: `git diff 81cb8a239a3cb8b6ddb4d69c97d8876b8fdfa68c...HEAD`.
- Commit list: `014de19 Review-only candidate: repair six DW4 DW5 lifecycle findings and retain newer authority`.
- Specification: `docs/native/DW4_DW5_THIRD_REVIEW_2026-09-16.md`, originating DW4/DW5 handoff, and current contracts, failure policy, PFD specification and native plan.
- Standards: the same repository authority plus the code-review skill's smell baseline. Imported DW1/DW6 authority is preservation work; DW6 implementation is outside this review.
- Issue-tracker setup is absent. The skill recommends `/setup-matt-pocock-skills` for issue-linked reviews; the supplied specification avoids blocking this review.
- Parent continuity/evidence records were still being prepared and were not reviewed as final.

## Standards

**FAIL — two documented-standard violations.**

1. **P1 — Admission-write failure leaves an allocated attempt unfinished.**
   `src/bh_sim/application/services.py:274` calls `_record_attempt(attempt)` before the exception handler begins at line 279. A failed admission write raises `OSError` while `_pending_attempts` retains `ADMITTED`, with no terminal timestamp or failure reason and no active execution. This violates `docs/CONTRACTS.md:292–295` (“Every allocated attempt needs an auditable terminal outcome”) and `docs/FAILURE_RECOVERY.md`'s requirement to record post-allocation failures. Include admission publication in the failure boundary and retain an accurately labelled terminal record when storage remains unavailable.

   Reproduced with a disposable store using `PYTHONPATH=src:. QT_QPA_PLATFORM=offscreen .venv/bin/python docs/native/evidence/dw4-dw5-remediation-2026-09-23/review_admission_fault_probe.py`.

2. **P2 — New worker control reader removes bounded request handling.**
   `src/bh_sim/worker/entry.py:142–152` creates an unbounded queue and continuously drains incoming validation/job messages while numerical execution can block. Backlogged full drafts can accumulate without limit. The cancellation set at lines 140/150 also retains every cancellation ID indefinitely. This violates `docs/FAILURE_RECOVERY.md`'s worker-message requirement to bound queues/frames and the DW4-C handoff's bounded messaging obligations. Bound queued work and retained cancellation identities while keeping cancellation/shutdown reachable when the work queue is full.

An inherited recovery gap remains: `rebuild_index_from_artifacts()` preserves an existing terminal SQLite row over conflicting canonical attempt JSON. A disposable probe reproduces historical S1's JSON `RUNNING`/index `COMPLETED` split remaining unchanged after rebuild. The rebuild method is outside this implementation diff; this is a pre-existing limitation, not a third introduced finding. Removing the disposable index before rebuild avoids that retained-cache case.

## Spec

**FAIL — one P1 finding.**

- **P1 — Cancellation can be lost before worker registration.** In `src/bh_sim/application/services.py:283–296`, the application publishes RUNNING and releases its lock before `execute_job` registers the job. Meanwhile, `src/bh_sim/adapters/worker_supervisor.py:305–306` discards cancellation for an unregistered job. Cancel records CANCELLED locally, but the job subsequently begins execution without cancellation or escalation. DW4-C requires: “If a backend cannot cooperate, enforce a bounded escalation.” Coordinate cancellation with admission so this window cannot dispatch uncancelled work.

  Reproduced with the real delayed worker, a barrier immediately before supervisor registration, and a 0.15-second configured grace: Cancel returned CANCELLED with no timer; after 0.6 seconds the child was still solving; the application returned RUN_CANCELLED only after 2.028 seconds. Publication remained blocked, but interruption exceeded the cancellation policy. Probe: `docs/native/evidence/dw4-dw5-remediation-2026-09-23/spec_admission_probe.py`.

No additional implemented-wrong behavior or unrequested scope found in the reviewed remediation. Retained DW1/DW6 authority is consistent with the preservation boundary. No scientific implementation change was identified.

## Verification and limits

`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests/test_dw45_remediation.py tests/test_dw5_acceptance.py` passed: **14 tests, 5.32 seconds**. The Spec reviewer separately ran the equivalent focused command with the same result. These tests cover normal cancellation, storage faults, worker loss and saved-edit staleness, but cancellation begins after worker progress and misses the admission window.

The aggregate reviewer replayed the historical `docs/native/evidence/dw4-dw5-third-review-2026-09-16/standards-probe.py`. It confirmed manifest retry/rebuild now produces COMPLETED and rejected execution records FAILED. It then stopped because validation of a dead configured worker now correctly raises WORKER_UNAVAILABLE; this historical probe assumes that old defect and therefore did not complete. This partial probe is not a full passing check.

Parent full checks are separate evidence, not claimed as reviewer execution here. Native Cocoa/VoiceOver witness, cross-platform execution, browser checks and DW6 acceptance were not performed by these reviewers. Final changes require a delta review after remediation and continuity records are complete.

**Summary: Standards 2 findings, worst P1; Spec 1 finding, worst P1.**
