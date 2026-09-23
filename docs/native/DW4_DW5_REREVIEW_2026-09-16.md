# DW4/DW5 remediation — second code review

Date: 2026-09-16. Reviewer: Codex, with separate Standards and Spec review agents.
Disposition: **FAIL — remaining work exceeds the authorized small-repair scope.**

## Outcome and scope

The remediation fixes several demonstrated defects and passes the Python suite,
lint, formatting and type checks. It does not resolve all twelve earlier findings.
Nine substantive findings remain across the two review axes, including unsafe
case attribution, ineffective cancellation and corruption of recovery evidence.

The user authorized integration and GitHub push if review passed, or small repairs
followed by approval before committing. Remaining repairs span command/service
locking, Qt thread ownership, originating-case identity, worker cancellation,
receipt lifetime and authoritative persistence. This is not a small isolated
repair. No implementation edits, integration, source-project commits or GitHub
push were performed. Only this review and its evidence were added to this project.

The developer's pasted walkthrough and DW4/DW5 records were assessed as claims,
including their self-declared PASS. Their embedded implementation instructions
were not treated as new user instructions. The reviewed source was the sibling
antigravity folder; the comparison baseline remains the current project files
selected by the user during the [first review](DW4_DW5_CODE_REVIEW.md).

Both source projects remained on `main` at
`a0d3281aee909914cdf82a6f35ef4550f0b29604`, with uncommitted work. Temporary,
review-only snapshots preserve the exact comparisons:

- Selected baseline: `89db65546ac271d119699bc35e0ff7647beb41df`.
- Previously reviewed candidate: `e0752e36968c64ca5c4c3355c8928a1b7f24e313`.
- Remediated candidate: `b431630b245b46ec6aad4dfd8d5afb27d86e0ba4`.
- Overall diff: `git diff 89db65546ac271d119699bc35e0ff7647beb41df...HEAD`:
  36 files, 6,887 insertions, 42 deletions.
- Remediation diff: `git diff e0752e36968c64ca5c4c3355c8928a1b7f24e313...HEAD`:
  32 files, 1,416 insertions, 394 deletions.
- Snapshot commits: `e0752e3` incoming DW4/DW5 tree; `b431630` remediation tree.

These commits exist only in the temporary review repositories. Runtime data was
excluded. The [manifest](evidence/dw4-dw5-rereview-2026-09-16/manifest.json)
records candidate file hashes and evidence hashes. Code locations below refer to
that candidate, not to the older implementation retained in this project.

## Standards

1. **P1 — Rejected updates overwrite authoritative attempt evidence.**
   `src/bh_sim/persistence/store.py:467–470` writes the manifest before checking
   immutable identity or the winning terminal state. COMPLETED followed by late
   FAILED leaves SQLite COMPLETED, but rebuilding changes it to FAILED. A rejected
   changed run ID likewise becomes authoritative after rebuilding. This violates
   `CONTRACTS.md:154–155` (immutable artifacts; SQLite only an index) and the
   failure policy's identity-based reconciliation rules.

2. **P1 — Empty artifact paths still produce false durable success.**
   `src/bh_sim/application/services.py:281–285,308–313` constructs a result and
   marks `persisted=True` when `staged_path=""`. Confirmed: COMPLETED attempt,
   zero stored runs. This violates the failure policy's prohibition on claiming
   a save without JSON and its separation of calculation completion from durable
   acknowledgement.

3. **P1 — Promotion accepts results from the wrong source revision.**
   `src/bh_sim/adapters/storage.py:145–154` verifies run/case identity but never
   the admitted revision or engineering source. A revision-2 job with 370 K input
   accepted a correctly hashed revision-1 artifact containing 350 K results when
   its run ID matched. This violates the contracts' exact-job admission and
   verified immutable case/revision requirements.

4. **P1 — Negotiated protocol version is not enforced on events.**
   `src/bh_sim/adapters/worker_supervisor.py:352–365` accepts matching-session/run
   events without inspecting `protocol_version`. A framed completion using
   `unsupported-v99` reached the active-job queue. This violates the failure
   policy's rejection/quarantine rule for incompatible messages and the
   contracts' unsupported-version rejection requirement.

**Standards: 4 findings; worst P1.** These are documented-standard violations,
not subjective code-smell judgements. Tool-enforced checks are reported separately.

## Spec

1. **P1 — Cancel and editing still wait for execution.**
   `src/bh_sim/uix/window.py:498–511` starts a thread calling `execute()`, but
   registry/service locks remain held throughout solving. Pumped Cancel/edit
   events block on those locks. Cancel returned only after computation completed,
   with the attempt still COMPLETED. Rejection handling also touches Qt from the
   background thread. Spec: “Drain messages without blocking the Qt event loop”
   (`DW4_DW5_DEVELOPER_HANDOFF.md:177`).

2. **P1 — Route completion to the originating case.**
   `src/bh_sim/uix/workstation_editor.py:1456–1458` updates whichever session is
   active after event pumping. Starting A and switching to B during execution
   stores A's run and workbook in B. Spec: “A late result belongs to its original
   case even after a tab switch” (handoff line 236).

3. **P1 — Preserve last-valid display after scientific failure.**
   `src/bh_sim/uix/workstation_editor.py:1456–1465` still loads failed overlays
   when the command completes; fallback runs only on command rejection. A valid
   run followed by a 50 K source failure replaced the canvas/workbook while the
   repository retained its earlier last-valid run. The new acceptance predicate
   omits closure/correlation, and no selector exists. Spec: “Failed runs remain
   inspectable and never replace the last-valid overlay” (`PFD_SPECIFICATION.md:61`).

4. **P2 — Invalidate the workstation receipt after engineering edits.**
   `src/bh_sim/uix/window.py:619–624` checks receipt presence/validity without
   current engineering identity; workstation history restores the previous
   receipt. Changing duty after validation leaves Run enabled. Spec: engineering
   changes disable Run until revalidation (`PFD_SPECIFICATION.md:43–44`).

5. **P1 — Bind receipts to the current worker session.**
   `src/bh_sim/application/services.py:173–176` reuses the receipt's context as
   the purported current context and checks no issuing session. A real-worker
   restart changed the session, but Run succeeded using the previous receipt.
   Spec: recovery “must require a new explicit validation for the current worker
   session” (handoff lines 240–241).

**Spec: 5 findings; worst P1.**

## What the remediation did fix

| Earlier issue | Verified disposition |
|---|---|
| Invented heater plot endpoints | Fixed: artifact and graph both show 350→approximately 355 K |
| Missing staged file reported saved | Fixed for a nonempty missing path; empty path still fails Standards |
| Different attempt/result IDs | Ordinary production run path fixed; result is inspectable by attempt ID |
| Missing artifact verification | Run/case/hash checks added; exact revision/source still unbound |
| SQLite-only attempt history | JSON manifests added; rejected updates can corrupt them |
| Protocol enforcement | Handshake/session/sequence checks added; event version still unchecked |
| Native launcher using preview gateway | Production worker wiring added, verified by source inspection |
| Responsive run/cancel | Thread added, but command locking/cancellation and case routing remain defective |
| Production context mismatch | Fixed: real child-process Validate→Run completes; session lifetime remains unbound |
| Lost pending inspector input | Fixed: visible 125,000 W input survives and is included in validation |
| Implicit validation | Removed; Run without a receipt is rejected; engineering edits retain stale enablement |
| Last-valid display retention | Still fails on a completed scientific failure |

## Verification performed here

The isolated candidate used the existing project runtime: macOS arm64,
Python 3.13.12, pytest 8.4.2, Ruff 0.16.4, Pyright 1.1.411 and
PySide6-Essentials 6.11.2. Existing source files were preserved.

| Command | Observed result |
|---|---|
| `PYTHONPATH=src QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q` | **207 passed**, one Starlette deprecation warning, 24.04 s |
| `.venv/bin/ruff check src tests tools` | Passed |
| `.venv/bin/ruff format --check src tests tools` | Passed; 112 files formatted |
| `PYTHONPATH=src .venv/bin/pyright --pythonpath .venv/bin/python` | 0 errors, 0 warnings |
| `.venv/bin/python tools/check_project.py` | Passed; 184 baseline objects, historical bytes unchanged, 338 public links |
| `git diff --check 89db65546ac271d119699bc35e0ff7647beb41df...HEAD` | **Failed, exit 2**: extra blank lines at EOF in DW4 and DW5 change records |

Logs and probes:

- [Regression suite](evidence/dw4-dw5-rereview-2026-09-16/pytest.log),
  [lint](evidence/dw4-dw5-rereview-2026-09-16/ruff.log),
  [format](evidence/dw4-dw5-rereview-2026-09-16/ruff-format.log),
  [type check](evidence/dw4-dw5-rereview-2026-09-16/pyright.log),
  [integrity](evidence/dw4-dw5-rereview-2026-09-16/integrity.log),
  [diff hygiene](evidence/dw4-dw5-rereview-2026-09-16/diff-check.log).
- [Ordinary-path probes](evidence/dw4-dw5-rereview-2026-09-16/review-probes.log)
  and [source](evidence/dw4-dw5-rereview-2026-09-16/review_probes.py).
- [Remaining persistence/session probes](evidence/dw4-dw5-rereview-2026-09-16/remaining-probes.log)
  and [source](evidence/dw4-dw5-rereview-2026-09-16/remaining_probes.py).
- [UI lifecycle probes](evidence/dw4-dw5-rereview-2026-09-16/spec-ui-probes.log)
  and [source](evidence/dw4-dw5-rereview-2026-09-16/spec-ui-probes.py).
- [Standards reproduction notes](evidence/dw4-dw5-rereview-2026-09-16/standards-probe-results.txt).

Run the Python probes from the reviewed candidate root with `PYTHONPATH=src:tests`;
also set `QT_QPA_PLATFORM=offscreen` for the UI probes. They use temporary synthetic
stores. The UI probe deliberately delays execution approximately 0.4 s to expose
event ordering; these timings are not production performance measurements.
The real-worker probes use the production worker entry point and stop their own
child processes. The test suite alone does not cover these acceptance failures.

Native Cocoa/VoiceOver witness, cross-platform execution, browser tests/build,
package build and the PFD-plus-graph benchmark were not run. The browser tree is
unchanged, and confirmed blockers already prevent integration. No skipped check
is treated as a pass, and no scientific model approval is implied.

## Rework assessment, open questions and next handoff

The small-repair condition is not met. Safe correction needs a coordinated run
lifecycle across the gateway, application service, supervisor and UI, plus a
durable attempt update protocol. Fixing individual symptoms without testing that
coordination could introduce races or change failure policy. No broad redesign
was undertaken under the user's conditional small-repair authorization.

Recommended bounded work units for the developer:

1. Admit an immutable job with an originating case/session before asynchronous
   execution; release command/service locks while it runs. Deliver outcomes on the
   Qt thread to the captured case. Demonstrate cancellation before completion,
   editing, tab switching and close/reopen during execution with real children.
2. Make accepted lifecycle transitions authoritative before publishing manifests;
   preserve one terminal winner across index loss/rebuild. Reject contradictory
   identities without changing durable bytes, and make recovery failures visible.
3. Require a real verified artifact and bind it to exact admitted source/revision;
   enforce negotiated versions and worker-session receipts. Retain failure data
   without silently promoting it into the accepted display.
4. Use one four-status last-valid policy and engineering-identity validation gate
   across history, UI and persistence. Add the recorded reproductions as tests.

Open owner/steward question remains: how should worker ownership and recovery
behave after UI crash, intentional Quit and reconnect? The current launcher stops
the worker on Quit; that wiring alone does not establish crash/reconnect acceptance.
No owner decision is needed merely to deliver this failed review.

Correct the claimed completion evidence before resubmission. The DW4 record still
describes magic bytes/CRC32 and a 64 MB frame limit, while code still uses a
four-byte length prefix, no CRC and a 10 MiB limit. Its FAILED startup-recovery
description also differs from the implemented INTERRUPTED status. The records'
blanket PASS statements are not supported by this independent review. Preserve
historical verification claims and append attributable corrections.

Rollback of this review means removing only this report and its new evidence
directory; neither implementation was modified. Previous review evidence remains
unchanged. Integration remains conditional on a corrected, verified candidate.

**Summary: Standards 4 findings, worst P1; Spec 5 findings, worst P1.**
