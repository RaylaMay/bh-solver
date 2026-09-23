# GitHub sync record — 2026-09-23

Status: reviewed delta integrated in the Codex checkout; branch publication and
hosted verification are commit-specific GitHub state and must be checked there.
Project owner and implementation/review contributor: Rayla May. Implementation
execution and independent AI code review: Codex agents under Rayla May's direction.

The Codex checkout is the sole main working folder selected by the owner. The
Antigravity checkout and its rollback backup are retained as recovery evidence at
least until the branch and main hosted checks pass. Newer DW1/DW6 authority and its
frozen handoff remain in the Codex checkout alongside the corrected DW4/DW5
implementation. See the
[remediation record](DW4_DW5_REMEDIATION_2026-09-23.md) for scope and open gates.

The guarded integration compared both folders with their recorded manifests. All
424 Codex intake files matched their original hashes, and all 192 Antigravity
transfer files matched the reviewed transfer manifest. It copied 65 named project
files, made no deletion, and preserved the Codex continuation prompt byte-for-byte.
The local rollback checkpoint is `.bh/codex-integration-backup-2026-09-23/` and is
excluded from Git.

## Remote and account checks

- Existing origin: `git@github.com:RaylaMay/bh-solver.git`.
- Authenticated GitHub connector account: `RaylaMay`.
- `git ls-remote origin HEAD refs/heads/main` returned
  `a0d3281aee909914cdf82a6f35ef4550f0b29604` for both, matching local HEAD.
- The configured CI workflow uses official `actions/checkout`, `setup-python` and
  `setup-node` v7 tags. All three were verified against upstream tag refs.
- The workflow tests Python on macOS, Windows and Linux and builds/tests the retained
  browser. A passing local run does not substitute for the hosted result attached to
  the final branch or main commit.
- The authorized commit author is
  `Rayla May <328618396+RaylaMay@users.noreply.github.com>`. Records distinguish her
  owner/contributor role from checks and implementation execution performed by Codex.

Read and write access checks do not change the repository. A push dry run, where
recorded in verification evidence, checks only branch write access using the old
base commit; it does not publish the remediated candidate or validate hosted CI.

## Codex-checkout verification

Fresh verification after the guarded integration produced these results:

- `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q`: 228 passed in
  39.19 seconds after the hosted-CI repair; one upstream Starlette/httpx
  deprecation warning.
- `.venv/bin/ruff check src tests tools`: passed.
- `.venv/bin/ruff format --check src tests tools`: 114 files already formatted.
- `.venv/bin/pyright`: zero errors, warnings or information messages.
- `.venv/bin/python tools/check_project.py`: 184 baseline Git objects unchanged and
  465 public file links valid.
- `npm test`, `npm run lint`, `npm run build` in `web/`: five tests passed; lint and
  production build passed.
- `uv build --offline --out-dir <temporary-output>`: source distribution and wheel
  built successfully from the existing locked environment.
- The scoped current source/tests/docs diff check passed. The full staged check
  reports only whitespace retained in historical evidence logs/Markdown and PDF
  cross-reference syntax; those evidence bytes remain unchanged. The bounded
  credential-pattern scan found no token or private-key candidate in the Git-visible
  source set.

The 171-file tested source manifest matched after integration. These are software
checks. They do not close the native witness, ownership/reconnection, release,
scientific V&V or engineering-approval gates listed in the remediation record.

The first hosted branch run exposed two environment prerequisites: Ubuntu lacked
`libEGL.so.1`, and the GitHub macOS Python toolcache did not provide the dynamic
CPython library required by the checkout-bound developer launcher. The workflow now
installs `libegl1` on Linux. The macOS launcher module skips when Apple's developer
tools are absent; its startup test additionally skips when the exact checkout Python
has no dynamic runtime. The ownership-protection test still runs in the hosted macOS
environment, and supported local environments execute both tests. That skip does not
count as a native workstation witness or close the DW9 packaging gate.

The next hosted run passed those three jobs and exposed a Windows portability bug:
colon-bearing attempt and run IDs had been used directly as manifest and staging
filenames. The adapter now derives deterministic SHA-256 filenames and keeps the
stable ID authoritative inside JSON. A compatibility path reads legacy raw-ID
attempt manifests where the filesystem permits them. This is a storage naming
change only; it does not alter public IDs, wire schemas or artifact hashes.
The independent [follow-up review](evidence/dw4-dw5-github-sync-2026-09-23/windows-portability-review.md)
reports Standards PASS and Spec PASS with zero remaining findings. Hosted Windows
execution remains the platform confirmation gate for this correction.
The final local suite after that correction passed 230 tests with the same upstream
Starlette/httpx warning. Ruff, formatting, Pyright, the project authority/link
check, and the scoped diff check passed. Offline source and wheel builds included
the new portable filename module.

## Authorized sync operation

Use `codex/dw4-dw5-remediation` from the existing main history, commit the reviewed
integration with the attribution above, and push the branch to origin. Review its
hosted checks before fast-forwarding main, then verify the hosted checks for main.
Recheck remote main immediately before integration. No force push, reset, clean or
history rewrite is needed.

The owner explicitly authorized commit, push, hosted-check verification and merge
to main after the review passed. Review-only commits live in the temporary review
repository and must not be pushed as project history. This source record captures
the authorized procedure and local evidence; it does not assert a remote outcome
for its own commit. Git and GitHub Actions are the authority for publication state.

Runtime directories, local environments, personal skills, node_modules, build
outputs and local backups are excluded. The portable inventory includes the
existing licensed source, tests, required documentation, preserved reviewer evidence
and the frozen DW6 handoff. A pattern scan found no token/private-key candidates;
that is a bounded scan, not proof that arbitrary text is free of sensitive data.
Historical evidence containing local path spellings remains unchanged under the
[public baseline qualification](PUBLIC_BASELINE_TRANSITION.md).

The Antigravity backup and transfer manifest support recovery of its dirty intake.
The Codex integration backup supports recovery of the chosen main checkout. Restore
only files from the applicable manifest and preserve later edits and runtime stores.
