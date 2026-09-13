# DW0 change record

Change title: Native workstation decision and baseline package.
Date and author: 2026-09-10, Rayla May. Rayla May directed the continuation request.
Status: **proposed** architecture/documentation changes; preparation and baseline
checks completed. DW0 acceptance remains pending.

## Objective and authority

Objective: make the first native-workstation decision gate concrete and reviewable
without beginning a production UI or solver migration.

Instruction from Rayla May addressed: continue the native action plan using the README and
repository authority; absent a narrower task, prepare DW0 and await its reviewed
gate before migration. References: action-plan Sections 2, 11–17 and Appendix A;
ADR-001–009 and proposed ADR-010; GATE-001–009, CORE-002/008/009/010, PFD-001–005,
BOUND-001 and reserved UIX requirements. Model cards were read for fixture status,
not changed or independently reverified.

## Scope, boundaries, assumptions and constraints

Scope: proposed ADR, native target diagram/dependencies, contract/versioning impact,
failure and dependency additions, requirement evidence corrections, milestone
cross-links, parity/retirement inventory and licence/platform brief.

Out of scope: production code changes, dependency installs/updates, Qt shell,
worker implementation, new equations, catalogue approval, migration of user
artifacts, audio/provider access, browser removal or industrial qualification.

Affected architectural boundaries: proposed interaction↔application↔worker and
application↔repository/provider contracts. Their running implementations are
unchanged. Assumptions: no approval absent a durable Rayla May/steward record; current
host is evidence, not a selected support target. Existing behaviour and desired
behaviour must remain distinct. Constraints: preserve user files and ADR history,
immutable hashes and independent statuses; keep typed text fully capable.

## Evidence and sources

Rayla May named all 13 governing documents; the review read each completely, plus root/web
READMEs, model register/cards, relevant source and tests listed in the
[parity inventory](BROWSER_PARITY.md). Repository status/tree inspection found an
unborn `main` branch with no commits and untracked content. No applicable nonempty
AGENTS instructions were found. No scientific-model skill or independent V&V
was invoked for this documentation-only task.

Primary Qt sources were checked on 2026-09-10 and linked at each supported claim
in [decision points](DECISION_POINTS.md). Only brief paraphrases and links are
retained; upstream content is not relicensed as project data. No AI/STT provider
was selected or researched as an adoption decision.

## Selected design and rationale

Append clearly marked proposals to accepted documents and add ADR-010, leaving
ADR-001–009 bodies intact. Keep executable code and current artifact schemas
unchanged. Correct unsupported browser test claims while retaining requirements
and their statuses. Reserve all 16 native requirements as PLANNED. Use a source-
and-test-based parity inventory with explicitly unwitnessed UI acceptance.

Alternatives considered: replacing the accepted architecture immediately would
imply approval not in evidence; keeping all impact only in chat would be hard to
review or hand off; a bulk Qt rewrite would cross DW0 and lose baseline evidence.
The selected approach leaves proposed and accepted sections together temporarily,
so their status labels and cross-links must be maintained until disposition.

## Files and contracts changed

Edited existing user-owned documents (12): `docs/README.md`, `VOCABULARY.md`,
`ARCHITECTURE.md`, `DECISIONS.md`, `CONTRACTS.md`, `PFD_SPECIFICATION.md`,
`FAILURE_RECOVERY.md`, `DEPENDENCY_REGISTER.md`, `REQUIREMENTS_VERIFICATION.md`,
`MILESTONES.md`, `INDUSTRY_DEVELOPMENT_STREAM.md`, `NATIVE_WORKSTATION_ACTION_PLAN.md`.
These are the only overlapping pre-existing files changed by this work.
The final hash audit also detected a change to `.obsidian/workspace.json` during
the task. This task did not write that file; it remains untouched and is excluded
from the documentation patch and unchanged-file assertion. All other pre-existing
files outside the 12 edited documents retain their captured byte hashes.

Added: [DW0 review](DW0_REVIEW.md), [parity inventory](BROWSER_PARITY.md),
[decision points](DECISION_POINTS.md), this record, and the evidence files below.

- [Baseline byte hashes and accepted-ADR hashes](evidence/baseline.json).
- [Patch for the 12 existing documents](evidence/existing-documents.patch).
- [Observed verification output](evidence/verification.txt).
- [Temporary-store observation probe](evidence/probe_baseline.py).
- [Document and baseline integrity checker](evidence/check_review.py).

Schema/migration impact: none deployed; new envelope versions, engineering-hash
semantics and run lifecycle/manifest require review at named gates. Existing strict
canonical codecs and HTTP aliases remain unchanged. Dependency/licence impact:
no package/lock change; proposed desktop exception and exact payload review pending.
Security/privacy impact: no capture, provider, upload or retention policy selected.
Scientific/validity impact: no equations, coefficients, model statuses or approvals
changed; fixture limitations and governance discrepancies explicitly retained.

## Verification performed

Commands below ran from the repository root unless a working directory is stated.
Installed dependencies were used directly to avoid changing the existing environment.

| Exact command | Observed result |
|---|---|
| `git status --short`; `rg --files`; `git log -1 --format='%H %s'` | Content untracked; no commit exists, so no Git diff baseline |
| `.venv/bin/python -m pytest -q` | 41 passed; one Starlette TestClient/httpx deprecation warning |
| `.venv/bin/ruff check src tests` | Passed |
| `.venv/bin/pyright` | Initial invocation: 8 missing-import errors and 1 warning due to interpreter selection |
| `.venv/bin/pyright --pythonpath .venv/bin/python` | 0 errors, 0 warnings; no source/config repair needed |
| `npm run test` in `web/` | 5 tests passed across 2 files: client and topology preflight |
| `npm run lint` in `web/` | Passed |
| `npm run build` in `web/` | TypeScript and Vite build passed |
| `.venv/bin/python -m bh_sim --help` | Lists the 3 legacy prototype demonstration commands; execution outputs not checked here |
| `.venv/bin/python -m docs.native.evidence.probe_baseline` | See dated output: movement does not change case hash; label does; Run without prior Validate returns 200; response omits separate run-level physical/correlation fields; unadaptable input returns 422 without new core artifacts |
| `.venv/bin/ruff check docs/native/evidence` | Initial 4 helper-style findings corrected; final result in verification output |
| `.venv/bin/python docs/native/evidence/check_review.py` | Local links/heading fragments/fences, unique requirement IDs, proposed states, unchanged inputs and accepted ADR bodies; exact counts in verification output |
| `git apply --reverse --check docs/native/evidence/existing-documents.patch` | Read-only reverse-patch applicability check; no rollback performed |

No production changes followed the baseline test run, so repeated full suites
were unnecessary; file hashes check that boundary. This is software/document
evidence, not model V&V or approval. The retained helpers are review tools outside
the production package and test suite, and do not invent new engineering results.

Checks not run: native/worker, renderer/performance, clean-machine install,
cross-platform, migration/fault-injection and AI/speech tests (unimplemented and
unapproved phases); UI component/accessibility walkthroughs (no current suite or
witnessed session); scientific V&V (no model change and independent review needed).
Mermaid sources were checked as fenced documentation but not rendered; diagram
render/witness evidence remains part of the architecture review. No full licence
audit/SBOM of a native payload is possible before selecting that payload.

## Risks, rollback and remaining decisions

Risks: a proposed section could be mistaken for accepted authority; existing
browser gaps and scientific governance labels remain unresolved; a no-commit tree
cannot supply a release rollback point. Tests cover only the current slice and
do not imply full advertised behaviour.

Rollback of this work: the patch records only changes to the 12 existing documents
and can be reversed after checking for later edits; the nine newly added files in
`docs/native/` can be removed only after confirming they contain no later Rayla May
work. Do not use a broad clean/reset on this untracked repository. The original
pre-edit hashes make exact review possible; a temporary local snapshot is an aid,
not a durable project backup. Native-product rollback is separately specified in
the parity checklist and remains untested.

Known limitations: no new schema implementation or golden native fixtures; some
documentation/implementation discrepancies require steward choices; Qt source
pages are time-sensitive and must be checked against the selected version.

Required decisions from Rayla May now: primary development and first-release platforms
(P-01), licence route and distribution posture (L-01), and DW0 boundary/versioning/
parity disposition including outstanding historical gate records. Later provider,
retention, participant, rendering and packaging choices have separate due gates
in [decision points](DECISION_POINTS.md). DW1 is remaining implementation work;
approval is a decision for Rayla May, not a task silently completed by this record.
