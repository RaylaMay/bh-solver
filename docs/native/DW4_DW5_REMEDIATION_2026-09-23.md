# DW4/DW5 third-review remediation — 2026-09-23

Status: **Software remediation verified; independent Standards and Spec PASS.**
Project owner and implementation/review contributor: Rayla May. Implementation
execution and independent AI code review: Codex agents under Rayla May's direction.
The work repaired the Antigravity checkout against the supplied third review, then
integrated the reviewed delta into the owner-selected Codex main checkout. BH remains
concept-development software. This record does not claim scientific V&V, engineering
approval or release acceptance.

## Source and scope

The target was dirty `main` at `a0d3281aee909914cdf82a6f35ef4550f0b29604`, with
substantial DW3–DW5 source, tests and documentation modified/untracked. Nothing was
staged. Its GitHub origin was `git@github.com:RaylaMay/bh-solver.git`. The sibling
workspace carried newer DW1 review preparations, ADR-012 and the frozen DW6 handoff.
Those records were retained selectively; incoming DW4/DW5 code was not replaced
with the older sibling implementation. Runtime stores and local environments were
excluded from review snapshots and remain untouched.

The [intake manifest](evidence/dw4-dw5-remediation-2026-09-23/intake.json) hashes the
initial public files in both folders. Review-only commits in a temporary repository
pin the dirty target (`81cb8a239a3cb8b6ddb4d69c97d8876b8fdfa68c`) and first candidate
(`014de19e03f9b6a3ab3bd94e3d706d98f032ac97`). These are review artifacts, not commits
in either original repository. No original history was reset, cleaned or rewritten.
The guarded transfer creates `.bh/remediation-backup-2026-09-23/` in the target,
containing the original public files and a per-file before/after transfer manifest.
This backup is local and excluded from Git.

After the independent PASS, the owner selected the Codex checkout as the sole main
working folder. The unchanged 424-file Codex intake was checkpointed locally, and
65 reviewed files were copied from Antigravity without deleting Codex content. The
Codex-only continuation prompt was preserved exactly. The resulting tested source
inventory matches the reviewed Antigravity source hashes.

Authority read: the complete normative reading list and native action plan, current
contracts/failure policy, DW4/DW5 handoff, remediation plan, and
[third review](DW4_DW5_THIRD_REVIEW_2026-09-16.md). Requirement chain: CORE-009/010,
PFD-002/004/005, UIX-RUN-001, UIX-ARCH-001/002 and UIX-DOC-001 → ADR-005/009/010,
JSON-first recovery and terminal-disposition contracts → changes below → regression
suite and independent Standards/Spec review. Equations, coefficients, property
backends and model approval are outside this change.

## Corrections and rationale

| Review finding | Change | Regression evidence |
|---|---|---|
| Standards 1: index committed before attempt JSON | Resolve the durable winner under a writer reservation; fsync/replace JSON before index update; retry repairs an index-only failure; rejected identity and terminal changes leave JSON intact | Manifest-write failure/retry/index-loss, index-commit failure, rejected inputs and late persistence acknowledgement |
| Standards 2: dead worker silently became local execution | Execution mode follows configuration; unavailable configured worker rejects Validate/Run; replacement session requires validation | Real worker stop/restart with a local-run spy and fresh-session recovery |
| Standards 3: result-save failure left RUNNING | Record FAILED with terminal time/reason and exact known result hash; retain local result bytes and failed audit in memory if storage is unavailable | Failure before and after result publication; reopen without replay; failed attempt excluded from last-valid |
| Spec 1: cancelled local calculation published success | One lock decides cancellation versus publication on both paths; late completion cannot acquire persisted status or advance last-valid | Delayed local solve, Cancel, late result and concurrent-run rejection |
| Spec 2: ordinary worker cancellation unbounded | Read controls on the worker main loop while one execution thread runs; bounded escalation scoped to run/process/session; configured one-second grace | Real child safe-boundary cancellation, uncooperative backend kill, timer cleanup, busy rejection |
| Spec 3: Save cleared stale warning | Capture native engineering identity at submission; compare workbook and retained overlay sources with current/preview document | Engineering edit → Save → undo → redo, plus presentation movement |

The separate review found three additional defects in the first correction:
initial admission-write failure still lacked a terminal audit; a pre-dispatch
Cancel could miss worker registration; the first control-reader implementation
queued unbounded work. The revised candidate records admission failure before any
execution, checks an application cancellation event atomically with supervisor
dispatch, and has no pending worker request queue or accumulated cancel-ID set.
Additional tests exercise each boundary. See the retained
[initial review](evidence/dw4-dw5-remediation-2026-09-23/review-initial.md).

Alternatives rejected: index-first authority contradicts ADR-009; holding the
application lock during execution prevents Cancel; publishing then undoing a
cancelled result exposes an incorrect last-valid result; using document dirtiness
confuses Save with scientific source identity. A one-second default reuses the
prior force-cancel grace and remains configurable, not a scientific deadline or
new owner-approved performance target.

## Changed boundaries and impact

Source changes are in application services, attempt persistence, worker supervisor,
worker entry, workstation result staleness and canvas labels. Tests add real-child
and fault fixtures. The JSON/DTO/wire schema and hash meanings remain unchanged;
`execute_job` gains an optional in-process cancellation predicate. Existing strict
codecs and old artifacts retain their bytes. No dependency, licence, scientific
model, browser source or lockfile changes are required. Current public documentation
supersedes inherited blanket PASS claims without altering historical evidence.

The portable source set also ignores `.bound-horizons/`, alongside existing `.bh/`,
virtual environment and build exclusions. No runtime cases, credentials or private
personal skills are added. The old remediation handoff's identifying local root
was normalized to `<checkout>`; its original bytes remain in the intake backup.

Hosted Windows verification exposed a remaining adapter defect: attempt and staged
result filenames embedded colon-bearing stable IDs. Adapter-private filenames now
use a deterministic SHA-256 name while the authoritative ID remains unchanged in
the JSON contract. Persistence still reads legacy raw-ID manifests on filesystems
that support them. Wire schemas, stable IDs and artifact hashes remain unchanged.
The independent [Windows portability review](evidence/dw4-dw5-github-sync-2026-09-23/windows-portability-review.md)
reports zero remaining Standards or Spec findings after its compatibility probe.

## Verification and review

Fresh commands, environment, outcomes and source hashes are recorded in
[evidence](evidence/dw4-dw5-remediation-2026-09-23/verification.json).
The first candidate passed 225 Python tests, Ruff and Pyright. Its five browser
tests, browser lint/build and Python source/wheel build also passed. Subsequent
review fixes require the final runs recorded there; inherited counts do not verify
the final candidate. Initial failures were a malformed move test fixture, a test
double missing the additive cancellation argument, and a test that expected a safe
boundary at exactly the configured kill deadline. These fixtures were corrected;
product fault probes remain in the regression suite.

Environment restrictions initially blocked the shared Vitest cache and uv cache.
The browser check used a writable dependency copy; the offline package build used
the existing uv cache with approved access. No package download was required.
The code-review skill found no issue-tracker configuration; it recommends
`/setup-matt-pocock-skills` for future issue-linked reviews. The supplied review
and repository contracts provided this task's specification without blocking it.

Separate review is software review by AI agents, not qualified independent
scientific or engineering V&V. The [final review](evidence/dw4-dw5-remediation-2026-09-23/review-final.md) reports
zero remaining findings on either axis against `d8bad6ef39c706cb1f964f59bddacd0ffbf95815`.
The final full suite passed **228 tests**; Ruff, Pyright, source/wheel build and the
scoped diff check passed. Independent reviewers ran 25 focused tests and race probes.
Raw diff whitespace findings are confined to preserved historical evidence and PDF
cross-reference syntax; current source/tests/docs pass the scoped check.

## Remaining gates, recovery and next developer

- Full native Cocoa/VoiceOver witness, approved-platform CI, PFD-plus-graph benchmark,
  UI-crash survivor/reconnect ownership, package distribution and full DW5-C witness
  remain open. Tests do not authorize browser retirement or close DW4/DW5 globally.
- One local child executes one job. Current backend interruption is before/after
  evaluation, followed by a kill at the configured grace if needed; no claim of
  mid-equation cooperative interruption. Restart/reopen requires fresh validation.
- A complete storage outage retains failed audit/results only in the live service;
  a subsequent process crash can lose those unsaved bytes. Never present them as saved.
- For older split JSON/index state, preserve the index as evidence and rebuild a
  fresh index explicitly. The existing rebuild routine does not clear populated
  tables. Preserve canonical and staged artifacts; never replay Run as recovery.
- Unknown reloaded result source identity remains conservatively stale. This work
  does not introduce a persistent per-run native-history identity schema.
- DW1 review batches and DW6 frozen tests remain future work with their original
  gates. No AI provider call or DW6 acceptance execution occurred here.

Rollback restores only changed files from the applicable pre-transfer or Codex
integration backup and removes only new files listed by its manifest. Preserve
subsequent owner edits and every runtime store. The authorized repository operation
is recorded in [the GitHub sync record](GITHUB_SYNC_PREPARATION_2026-09-23.md): publish
the reviewed branch, require its hosted checks, fast-forward main, and verify main.
A receiving session must compare the evidence manifest with current files first.
