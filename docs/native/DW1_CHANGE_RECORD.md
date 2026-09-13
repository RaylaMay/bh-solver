# DW1 change record — neutral application boundary

Date: 2026-09-11. Author: Rayla May. Rayla May directed this implementation.
Status: **IMPLEMENTED; DW1 SOFTWARE CHECKS PASSED**.

DW1 now routes the retained browser and CLI behavior through application use
cases, with a neutral command boundary available for the later native shell.
This is software-boundary evidence, not scientific V&V or native release acceptance.

## Objective and authority

Continue the approved native plan's DW1 stage by separating use-case orchestration
from FastAPI/CLI ownership, preserving the current browser and scientific outputs.
Rayla May approved DW0 with annotations and requested open questions/suggestions
before building. The licence ambiguity was raised and clarified; the resulting
[disposition by Rayla May](DW0_OWNER_DISPOSITION.md) records names, platforms, Qt LGPLv3,
the adopted BH non-commercial license and DW1 authorization.

References: ADR-010; action-plan DW1 and Appendix A; UIX-ARCH-001/002,
UIX-CMD-001, UIX-DOC-001/002; BOUND-001; CORE-002/008/009/010;
PFD-002/003/004/005; DW0 GAP-01/02/03/08/09.

## Scope and architectural boundaries

Implement neutral immutable DTOs, versioned synchronous command requests/outcomes/
events, application use cases through declared ports, concrete in-process
engineering/storage/demo adapters, composition wiring, thin HTTP/CLI adapters,
golden compatibility fixtures and boundary/admission/result tests.

Record the BH solver working name and Rayla May's decisions in documentation. Product
names do not rename `bh_sim`, existing executables, models or schemas.

Out of scope: Qt installation/shell, worker supervision/cancellation, binary
trajectories, rendering benchmarks, native accessibility/workbooks, AI/speech
providers, release packaging, browser retirement,
new equations or model/industrial approval.

## Assumptions, constraints and evidence

The baseline repository remains uncommitted/untracked. All pre-existing work is
preserved; changes are reviewed against a pre-DW1 file snapshot rather than an
unavailable commit. No Git stage/commit/reset/clean is part of this work.
Live external changes were observed in `.obsidian/workspace.json` and
`Project leader's notes/User Interface/UI.md`; neither file was edited by this
workstream, and both are excluded from its patch/integrity assertions.

Previously read governing documents and DW0 evidence remain the authority, updated
only by the explicit decisions Rayla May made on 2026-09-11. Source/test inspection identified
endpoint-owned orchestration, eager root-package imports and a presentation versus
engineering identity conflict. [DW1 contracts](DW1_BOUNDARY.md) explain the selected
scope. The code implementation and compatibility-fixture work were delegated to
separate agents with file ownership; the primary agent integrates documentation
and reviews the outcome. No independent scientific V&V is claimed.

The actual release/testing target is macOS/arm64. Neutral contracts avoid platform
APIs; eventual Windows/x86_64 and BH Linux support remain testable obligations,
not capabilities demonstrated on the current host. Minimum platform versions
are deliberately deferred by instruction from Rayla May.

## Selected design, alternatives and tradeoffs

- Neutral types carry values rather than kernel/UI runtime objects. Public
  prototype exports remain compatible while avoiding eager scientific imports
  when the neutral boundary is imported.
- The application uses ports; one composition root wires concrete reference
  engineering, artifact, draft and demonstration adapters. This allows mock-only
  application tests and later worker replacement.
- New `draft.validate`/`run.start` commands use service-retained receipts, exact
  engineering identity and live execution-context identity. The engineering
  projection omits only presentation names from the canonical case primitive;
  canonical artifact hashes retain their existing meaning.
- Legacy HTTP Run retains its old explicit compatibility use case. Silently
  requiring a new receipt on the old endpoint would break the approved baseline.
  Keeping that path means existing browser enablement/display gaps remain visible
  follow-up work; the stricter new command path does not retroactively fix the UI.
- Comparison reports before/after stored quantities and independent statuses,
  without re-solving or inventing cross-unit numerical deltas. Full structural
  revision comparison belongs to later work.
- Qt-free DW1 proceeds under the adopted BH Non-Commercial Source-Available
  License. Applying LGPLv3 to BH-owned code would misstate the selected route;
  Qt/PySide remains separately governed by LGPLv3.

Alternatives rejected: broad source-directory rewrite, importing existing
Pint-backed core values as the neutral UI contract, promoting prototype CLI models,
silently changing old hashes or HTTP behaviour, and treating Qt licence-route
selection as installer compliance approval.

## Files, compatibility and other impacts

The [dated file inventory](evidence/dw1-file-inventory.json) records before/after
hashes; the [review patch](evidence/dw1-changes.patch) contains modified and added
workstream files against the pre-DW1 snapshot. The inventory, verification log
and patch itself are excluded from patch contents to avoid recursive evidence.
The review units are:

| Files | Purpose |
|---|---|
| `src/bh_sim/boundary/` | Immutable neutral DTOs, typed command outcomes/events and strict JSON encoding |
| `src/bh_sim/application/` | Port contracts, registry, validation receipts and use-case orchestration |
| `src/bh_sim/adapters/`, `composition.py` | Concrete reference-engine, retained storage and prototype adapters; explicit wiring |
| Package/API `__init__.py`, `api/adapter.py`, `api/app.py`, `cli.py` | Lazy compatible exports and thin existing interaction adapters |
| `tests/test_boundaries.py`, `tests/test_application.py`, `tests/test_dw1_compatibility.py` and DW1 fixture directories | Isolation, admission/failure, regression and frozen legacy/neutral command compatibility evidence |
| Root README, governing docs and `docs/native/` records | Annotations from Rayla May, adopted direction, exact DW1 scope and dated review evidence |

Changes are confined to these source/test families and governing documentation;
unrelated Rayla May files remain outside the patch. Adapter conversion/demo fixture
code is a mechanical relocation with compatibility wrappers, not new equations.

Canonical `v1alpha` artifacts/codec and old HTTP envelopes are preserved. The new
command/presentation/hash versions are explicitly separate. No migration of user
artifacts or new authoritative binary format occurs. Receipt state is process-local
and does not claim durable request deduplication, run admission or crash recovery.

Dependencies/licensing: no new dependencies or lock-file changes;
`LICENSE` and `pyproject.toml` identify Rayla May and the adopted BH
Non-Commercial Source-Available License. No proprietary package is added.
Privacy/security: no network provider, speech,
data upload, retention policy or new industrial permissions. Scientific impact:
existing equations, coefficient data, core statuses and model cards remain intact;
fixture-only warnings are preserved.

## Tests and checks

Final commands and observed results are recorded in the
[verification log](evidence/dw1-verification.txt). Commands below run from the
repository root except the three browser commands, which run from `web/`.

| Command | Observed result |
|---|---|
| `.venv/bin/python -m pytest -q` | 82 passed; one existing Starlette/httpx deprecation warning |
| `.venv/bin/python -m ruff check src tests` | Passed |
| `.venv/bin/python -m pyright --pythonpath .venv/bin/python` | 0 errors, 0 warnings |
| `npm run test` | 5 passed in 2 test files |
| `npm run lint` | Passed |
| `npm run build` | TypeScript and Vite production build passed |
| `.venv/bin/ruff check docs/native/evidence/check_dw1_review.py` | Passed |
| `.venv/bin/python docs/native/evidence/check_dw1_review.py` | Dated hashes, local links/anchors/fences, accepted ADR-001–009 bodies, ADR-010 status and unique requirement IDs passed |

The Python suite includes frozen pre-extraction HTTP/canonical/CLI artifacts,
fixed new command/outcome JSON, immutable/malformed/version rejection, request
deduplication, missing/stale/cross-draft/invalid receipts, label/layout versus
engineering changes, live context changes, execution snapshot isolation, failed
attempt retention, last-valid selection and comparison. Fake ports check rejection
before execution and expose context changes during input persistence. Six accepted
legacy draft edge cases test lossless conversion, including duplicate IDs.

Independent read-only software review found and re-probed fixes for malformed
request rejection, oversized/non-finite numbers, the context/persistence race,
SQLite error sanitization and loss of legacy presentation/parameter fields.
No confirmed review defect remained at handoff. This reviewer did not repair
source or conduct scientific V&V. A separate documentation review identified
stale platform/licence approval wording, now corrected to Rayla May's decision.

Intermediate checks were not all green: initial compatibility testing caught a
CLI Python-helper return-type regression, resolved while preserving command
dispatch; Pyright narrowing/export issues and Ruff formatting were corrected.
The document check caught the old `proposed-native-requirements` anchor after the
section was adopted; its link was updated. The audit helper's initial line-length
failures were corrected. Final evidence supersedes those intermediate failures;
the original DW0 verification record remains historical and unchanged.

Not part of DW1 verification: real worker/cancel/crash or native UI tests,
Windows/Linux execution, clean-machine packaging, full scientific V&V, licence
ownership audit and installer compliance. Those remain at their named gates.

## Risks, rollback and remaining work

Risks: legacy UI gaps remain; process-local receipts require revalidation after
restart; source-based execution fingerprints need a distribution manifest plan;
current prototype fixture semantics are not scientific approval; final distribution
compliance and provenance review remain required before publication.

Rollback will restore only the changed baseline files and remove only this work
unit's added files after checking for newer edits by Rayla May. Do not use broad Git
clean/reset against this untracked repository. Canonical user artifacts are not
migrated, so no engineering-artifact rollback should be necessary.

Remaining decisions for Rayla May: ownership and prior-distribution facts for any
externally sourced material, contribution/reuse rights, and final distribution
compliance. They do not reopen DW0 or block Qt-free DW1.
Later renderer, AI/speech, participant-budget, packaging/signing and platform
minimum decisions retain the plan's separate gates.
