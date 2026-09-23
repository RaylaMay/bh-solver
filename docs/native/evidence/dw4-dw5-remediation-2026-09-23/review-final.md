# DW4/DW5 remediation — final independent software review

Date: 2026-09-23. Reviewer: separate Codex review agent using `code-review`, with parallel Standards and Spec agents. **Scoped software remediation PASS.** This does not accept the full DW4/DW5 milestone or establish qualified scientific/engineering V&V.

## Source and scope

The review-only candidate is `d8bad6ef39c706cb1f964f59bddacd0ffbf95815`, compared with fixed review-only baseline `81cb8a239a3cb8b6ddb4d69c97d8876b8fdfa68c`. The initial review examined `014de19e03f9b6a3ab3bd94e3d706d98f032ac97`; the final review examined its delta and retained the original comparison context.

- Overall command: `git diff 81cb8a239a3cb8b6ddb4d69c97d8876b8fdfa68c...HEAD`.
- Delta command: `git diff 014de19e03f9b6a3ab3bd94e3d706d98f032ac97...HEAD`.
- Commits: `014de19 Review-only candidate: repair six DW4 DW5 lifecycle findings and retain newer authority`; `d8bad6e Review-only follow-up: close admission and cancellation races; record recovery limits`.
- Specification: the six findings in `docs/native/DW4_DW5_THIRD_REVIEW_2026-09-16.md`, originating DW4/DW5 handoff, and current contracts/failure/PFD/native-plan authority.
- Standards: documented repository requirements and the code-review skill's heuristic smell baseline. No implementation edits were made by reviewers.
- Imported DW1/DW6 records preserve newer authority; DW6 implementation is outside scope. Historical evidence whitespace and frozen PDF bytes were preserved.

The candidate was clean at delta intake. During final aggregation the parent added verification logs/manifests and updated `verification.json`; implementation remained at the reviewed commit. Original source-project history was not committed or rewritten by these reviewers. Issue-tracker setup is absent; the supplied specification enabled both review axes without issue retrieval.

## Standards

**PASS for the scoped remediation. No remaining blocking findings.**

Both initial findings are resolved:

- Admission publication failure now produces `PERSISTENCE_FAILED`, retains a terminal `FAILED` audit record with timestamp/reason, and prevents execution. An independent disposable-store probe confirmed that the retained record remains inspectable and the solver is never called.
- Worker control handling now rejects concurrent work without accumulating requests or cancellation IDs. Synchronized output preserves framing while one execution thread operates. The concurrent-validation regression confirms prompt `WORKER_BUSY` rejection.

Fresh Standards verification: `PYTHONPATH=src:. QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests/test_dw45_remediation.py tests/test_dw4_command_integration.py` — **20 passed in 6.16 seconds**. The independent admission-failure probe also passed.

The remediation and GitHub-preparation records distinguish temporary review commits, uncommitted source-project changes, final verification and future publication. Current contract/failure additions explain storage limits, conservative staleness, configurable cancellation grace and recovery using a fresh index. The previously identified populated-index rebuild limitation is explicitly documented.

This pass does not close full DW4/DW5, native witness, platform, ownership/reconnect, scientific V&V or engineering approval gates.

## Spec

**PASS for the scoped remediation. No remaining findings.**

The prior P1 cancellation race is corrected. The application sets its cancellation event before acquiring the supervisor lock; the supervisor checks that event while atomically registering dispatch. Cancellation either prevents dispatch or reaches the registered job and starts bounded escalation.

Fresh real-child probes exercised both race boundaries with a three-second delayed backend and 0.15-second cancellation grace:

- Before registration: `RUN_CANCELLED` in 0.002 seconds; worker remained healthy; no dispatch.
- Immediately after the predicate check, before registration: child terminated; `RUN_CANCELLED` returned in 1.007 seconds, including supervisor polling.

Both preserved last-valid selection and cleared active-job/timer state. Reviewer probe: `spec_followup_probe.py` in the temporary review workspace. An initial arbitrary one-second response assertion was too strict for the existing polling interval; the corrected two-second bound passed. This was a probe adjustment, not a product change.

Admission failure retains an inspectable terminal audit without execution. The worker no longer queues pending work or accumulates cancellation IDs. Documentation distinguishes in-memory recovery, inherited evidence, final checks and preparation from actual GitHub publication.

No unrequested scope or additional incorrect implementation was identified. Full milestone native witness, process ownership/reconnection, hosted CI and release gates remain open as documented. This is software review, not qualified scientific or engineering V&V.

## Aggregate verification and limits

The aggregate reviewer independently ran:

`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests/test_dw45_remediation.py tests/test_dw4_command_integration.py tests/test_dw5_acceptance.py`

Result: **25 passed in 7.66 seconds**. A source/test/current-document delta whitespace check also passed. The historical admission bug-oracle was replayed and now stops at its old assertion after reporting the corrected `FAILED` state, terminal timestamp/reason and `PERSISTENCE_FAILED`; the current regression and independent updated probe provide passing evidence.

The parent separately completed final-source checks recorded in `docs/native/evidence/dw4-dw5-remediation-2026-09-23/verification.json`: 228 Python tests, 29 focused tests, Ruff, Pyright, project integrity, unchanged frontend tests/lint/build and package build. These are parent-produced evidence inspected during aggregation, not checks represented as reviewer execution. Full cumulative whitespace checking intentionally reports preserved historical evidence/PDF formatting; current product/document checks pass.

Final records and guarded transfer must continue to identify the exact source inventory. No reviewer performed target transfer, original-project commit, remote publication, native Cocoa/VoiceOver witness, hosted cross-platform CI, performance benchmarks, DW6 acceptance or scientific V&V. Those distinctions remain in the remediation handoff.

**Summary: Standards 0 remaining findings; Spec 0 remaining findings.**
