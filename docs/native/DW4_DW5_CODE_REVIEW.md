# DW4/DW5 incoming implementation — code review

Date: 2026-09-15. Reviewer: Codex, with separate Standards and Spec review agents.
Disposition: **FAIL — do not integrate, commit or push this candidate.**

## Scope and source identity

The user requested review of the sibling antigravity project's DW4/DW5 work and
commit/push to this project's `main` only if it passed. The user selected this
project's current working files as the comparison baseline. Both source projects
were on `main` at `a0d3281aee909914cdf82a6f35ef4550f0b29604`, with extensive
uncommitted earlier work. Reviewing only Git HEAD would have missed the changes.

The comparison freezes 30 changed/added files, with 5,847 insertions and 24
deletions. Runtime data under `.bound-horizons/` was excluded. Temporary review-only
commits captured the selected working trees:

- Baseline: `89db65546ac271d119699bc35e0ff7647beb41df`.
- Candidate: `e0752e36968c64ca5c4c3355c8928a1b7f24e313`.
- Diff: `git diff 89db65546ac271d119699bc35e0ff7647beb41df...HEAD`.
- Commit list: `e0752e3 Review snapshot: incoming DW4 and DW5 working tree`.

These synthetic commits exist only in temporary review repositories. Neither
source checkout was committed or pushed. The candidate implementation was not
copied into this project. Only this review and its evidence were added here.
The [manifest](evidence/dw4-dw5-review/manifest.json) records SHA-256 identities for
each changed file on both sides and for the retained evidence.

The attached change records are implementation claims, not execution instructions
or approval. Requirements were checked against the existing native action plan,
PFD specification, contracts, architecture and failure policy. The
[developer handoff](DW4_DW5_DEVELOPER_HANDOFF.md) is explicitly proposed planning
material; its suggested renderer and stress fixture were not treated as accepted
technology decisions. No scientific model approval is conferred by this review.

Code locations below refer to the reviewed **candidate**, not the earlier source
files retained in this project. P1 means a high-priority correctness or acceptance
blocker; P2 means a material issue that also needs correction before this delivery
can claim completion. Tool-enforced failures are recorded separately from the
human review findings, as required by the code-review skill.

## Standards

1. **P1 — Fabricated plot values.** `src/bh_sim/adapters/storage.py:681–684`
   emits fixed 300→350 K endpoints. The heater fixture calculates 350→355 K, but
   its plot displays 300→350 K. Other branches invent missing duties, temperatures
   and convergence samples. This violates `ARCHITECTURE.md:9–10` (kernel owns
   numerical truth) and `FAILURE_RECOVERY.md:5`: “No recovery path may invent
   engineering values.”

2. **P1 — Failed persistence reported as durable success.**
   `src/bh_sim/application/services.py:238–267` suppresses promotion exceptions,
   constructs an empty result view and sets `persisted=True`. An absent staged
   JSON reproduced `COMPLETED`, `persisted=True`, and no inspectable run artifact.
   This violates the failure policy's JSON/index failure rules and its separation
   of calculation completion from durable-save acknowledgement.

3. **P1 — Admission and artifact have different run identities.**
   `src/bh_sim/application/services.py:297–304` executes without passing the
   allocated run ID; `src/bh_sim/worker/entry.py:205–209` does likewise. The kernel
   allocates another ID. Reproduction shows `attempt.run_id != result.run_id`;
   inspecting the admitted ID returns `NOT_FOUND`. This violates the contracts'
   exact-job admission and identity-based reconciliation requirements.

4. **P1 — Promotion does not verify the admitted artifact.**
   `src/bh_sim/adapters/storage.py:114–123` accepts any decoded `RunResult` from
   the supplied path without comparing digest, run, case or revision with the job
   and completion event. Unrelated content can be indexed and selected as
   last-valid. This violates verified-hash admission and exact-artifact
   reconciliation requirements in the contracts and failure policy.

5. **P2 — Attempt audit exists only in the disposable index.**
   `src/bh_sim/persistence/store.py:234–265` stores lifecycle evidence solely in
   SQLite. The Standards reviewer removed a temporary index and rebuilt it:
   canonical inputs returned, but no attempts did. This violates
   `CONTRACTS.md:154–155` (“SQLite stores only an index”) and failure-policy
   transaction rule 2 requiring an initial manifest before evaluation.

6. **P1 — Worker protocol metadata is not enforced.**
   `src/bh_sim/adapters/worker_supervisor.py:105–115` accepts unsupported
   protocols; lines 283–287 route events solely by run ID, ignoring session and
   sequence. Unsupported protocol text also survives codec round-trip. This
   violates the failure policy's rejection/quarantine requirement for
   incompatible, duplicate and late messages.

Standards: **6 findings; worst severity P1.** These are documented-standard
violations; no additional subjective smell findings were needed.

## Spec

1. **P1 — Wire the worker into native launch.**
   `src/bh_sim/adapters/desktop_preview.py:102–109` adds an unused factory.
   `desktop_launcher.py` still selects preview ports with Validate/Run disabled;
   calling the new factory without a supervisor also creates no worker. Spec:
   “Start, monitor, cancel and restart the worker from the application layer”
   (`NATIVE_WORKSTATION_ACTION_PLAN.md:709`).

2. **P1 — Make Run asynchronous and cancellable.**
   `src/bh_sim/uix/window.py:478–483` synchronously waits for execution on Qt's
   thread; the service holds its lock through execution. Editing, repainting and
   Cancel wait for completion. Cancel additionally uses `run:in-flight`, a
   placeholder ID. Spec: “Drain messages without blocking the Qt event loop”
   (`DW4_DW5_DEVELOPER_HANDOFF.md:177`).

3. **P1 — Bind validation to the actual worker context.**
   `src/bh_sim/application/services.py:136–140` discards worker validation
   identities and uses the local context hash. Production worker metadata differs
   from composition metadata. The real child-process probe validates successfully
   but rejects Run with `execution context changed before snapshot`. Spec:
   “Validate in the selected worker context” (handoff line 185).

4. **P1 — Flush inspector edits before Validate/Run.**
   `src/bh_sim/uix/window.py:478–483` bypasses `flush_input_edits()`; refresh
   destroys modified fields. A validated heater's visible duty was changed from
   75,000 to 125,000 W, then Run succeeded with 75,000 W and discarded the edit.
   Spec: “send the current revision” (`PFD_SPECIFICATION.md:37`).

5. **P2 — Require explicit validation before enabling Run.**
   `src/bh_sim/uix/window.py:471–473` automatically validates when Run is pressed
   without a receipt; Run also stays enabled after engineering edits. Spec:
   “Validation and Run are explicit”; engineering changes “disables Run until
   revalidation” (`PFD_SPECIFICATION.md:43–44`).

6. **P1 — Preserve last-valid overlays after scientific failure.**
   `src/bh_sim/uix/workstation_editor.py:1427–1429` replaces the selected workbook
   and overlays for every completed `RunViewDto`, including failed convergence or
   validity. No native last-valid selector is wired to restore the accepted
   display. Spec: “Failed runs remain inspectable and never replace the last-valid
   overlay” (`PFD_SPECIFICATION.md:61`).

Spec: **6 findings; worst severity P1.**

## Verification performed in this review

Environment: macOS 26.6.2 arm64; Python 3.13.12; pytest 8.4.2; Ruff 0.16.4;
Pyright 1.1.411; PySide6-Essentials 6.11.2. Both frozen trees used the same existing
runtime via a `.venv` symlink. Commands ran from their respective isolated roots.

| Check | Selected baseline | Incoming candidate |
|---|---|---|
| `PYTHONPATH=src QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q` | Not rerun | **207 passed**, 1 Starlette deprecation warning, 23.26 s |
| `.venv/bin/ruff check src tests tools` | Passed | **111 errors** |
| `.venv/bin/ruff format --check src tests tools` | 97 files formatted | **18 files need formatting** |
| `PYTHONPATH=src .venv/bin/pyright --pythonpath .venv/bin/python` | 0 errors | **305 errors** |
| `.venv/bin/python tools/check_project.py` | Not rerun | Passed: 184 baseline objects, historical bytes unchanged, 338 links |
| `git diff --check <baseline>...HEAD` | Not applicable | Passed |

Full [pytest](evidence/dw4-dw5-review/pytest-final.log),
[lint](evidence/dw4-dw5-review/ruff.log),
[format](evidence/dw4-dw5-review/ruff-format.log) and
[type-check](evidence/dw4-dw5-review/pyright.log) outputs are retained.
The first temporary-checkout pytest run had 205 passes and two launcher failures
because `.venv` was absent there. After adding the runtime link, the complete
rerun passed. The [initial log](evidence/dw4-dw5-review/pytest.log) is retained;
those two environment failures are not candidate defects.

### Focused evidence beyond the supplied tests

- [Core probes](evidence/dw4-dw5-review/review-probes.log): real worker validation
  followed by context rejection; artifact/plot temperatures disagree; admitted
  run ID cannot retrieve its result; missing staged JSON falsely reported saved.
- [UI probe](evidence/dw4-dw5-review/ui-probe.log): a 125,000 W pending inspector
  value is lost and Run uses 75,000 W. With a deliberate 0.3 s engine delay, a
  20 ms Qt timer fires zero times during Run and fires after event processing
  resumes. The delay is a review fixture, not a performance measurement.
- [Stderr probe](evidence/dw4-dw5-review/stderr-probe.log): a child writing about
  1 MiB of diagnostics before handshake times out. The supervisor creates a
  stderr pipe but has no consumer; this contradicts DW4's claimed drain thread.
  The test ends by stopping its own child process.

Probe sources are retained beside their logs. To rerun them against the candidate,
set `PYTHONPATH=src:tests` and invoke `review_probes.py` with the environment's
Python; invoke `ui_probe.py` with `QT_QPA_PLATFORM=offscreen` and `PYTHONPATH=src`;
invoke `stderr_probe.py` with `PYTHONPATH=src`, keeping `stderr_worker.py` beside it.
All stores are temporary synthetic fixtures. Original case data was not used.

Passing tests do not establish native end-to-end acceptance: the new acceptance
fixture calls `create_supervised_gateway` without a supervisor, and its dedicated
child-process test uses a mock worker. Neither exercises the production worker's
context or the production desktop launch composition.

Browser tests/build, package build, native Cocoa witness, VoiceOver, cross-platform
execution and the PFD-plus-graph benchmark were not run here. The browser tree is
unchanged in this comparison, and the confirmed blockers already prevent
integration. These unperformed checks are not passing evidence.

## Open questions and suggestions

1. **Worker lifetime policy remains unresolved.** The existing handoff asks the
   owner/steward to settle UI crash survival, intentional Quit and reconnect
   ownership before freezing DW4. Implement the selected policy and demonstrate
   real-process cancellation, loss, recovery and failed writes. No answer is
   required merely to deliver this failed review.
2. **Correct the completion records before requesting acceptance.** DW4 claims
   magic bytes, CRC32, a 64 MB frame limit and a stderr drain thread. The actual
   framing uses a four-byte length prefix, a 10 MiB limit and no CRC; no stderr
   drain exists. Its startup status description also says `FAILED`, while code
   records `INTERRUPTED`. DW5's complete workflow/provenance claims exceed the
   verified production integration. Preserve historical test claims as such and
   add explicit corrections rather than rewriting earlier evidence.
3. **Close scientific display gaps with artifact-based fixtures.** Test heater,
   cooler, exchanger and missing-output plots against stored values; propagate
   failed/stale/extrapolated labels and full source provenance through exports.
   The Spec reviewer also found that workbook staleness follows `dirty` rather
   than engineering identity, so saving an engineering edit can clear the warning
   and presentation-only changes can incorrectly mark results stale.
4. **Keep next integration bounded.** Correct the twelve findings and required
   static checks in the harness folder, then review the new delta against this
   baseline. Add real production-launch/worker acceptance and explicit failure
   injection. Earlier DW3 work is still uncommitted in this project; any eventual
   GitHub integration must account for those dependencies without silently
   including runtime data or claiming that this review covered all earlier work.
5. **Issue-tracker setup is missing.** `docs/agents/issue-tracker.md` is absent.
   The invoked skill recommends `/setup-matt-pocock-skills`. The supplied specs
   were sufficient for this review, so this did not block the review itself.

Recovery: this review changes no implementation or runtime state in either source
project. Removing only this report and its evidence directory would remove the
review artifacts. The next acceptance gate is a corrected candidate with fresh
review and verification; the user's conditional commit/push authorization was not
exercised because this candidate failed.

**Summary: Standards 6 findings, worst P1; Spec 6 findings, worst P1.**
