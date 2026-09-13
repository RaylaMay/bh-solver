# DW0 — Native workstation decision and baseline review

Prepared: 2026-09-10. Disposition: **OWNER APPROVED WITH ANNOTATIONS, 2026-09-11**.

The [owner disposition](DW0_OWNER_DISPOSITION.md) records approval of the BH solver
name, macOS-first cross-platform direction, Qt LGPLv3 and the adopted BH
non-commercial source-available license. DW1 is authorized. The preparation
inventory below records the state submitted on 2026-09-10; its pending-decision
entries are historical and superseded by that disposition.

At submission, DW0's proposal package was prepared. No production migration had started, no Qt
dependency has been installed, and no scientific model or architecture gate has
been approved by that preparation work. Subsequent DW1 implementation/evidence is
recorded in the [DW1 change record](DW1_CHANGE_RECORD.md).

## Current boundary and task

The running baseline is a local Python kernel for acyclic, pure, single-phase
steady flowsheets, immutable domain JSON, a SQLite lookup index, FastAPI and a
React PFD. Prototype CLI demonstrations remain separate. Reference liquid and
radiator cards are `BLOCKED_EVIDENCE / TEST FIXTURE ONLY`; software checks are not
model approval or industrial qualification.

The owner requested continuation of the native action plan using the repository
as authority. No narrower approved implementation task or completed DW0 record
was found. This work therefore prepares DW0: proposed superseding ADR, document
and requirement impacts, licence/platform choices, browser parity and retirement
criteria. Owner intent for a native product is distinct from approval of a toolkit,
licence, platform matrix or new wire contract.

At inspection, `main` had no commits and all repository content was untracked.
No files were staged, committed, reset or removed. Existing documentation changes
overlap user-owned files and are enumerated in the [change record](CHANGE_RECORD.md).
The [baseline hashes](evidence/baseline.json) identify the inspected source/test/
configuration/document bytes without relying on a nonexistent commit.

## Review package

| Deliverable | Artifact | Disposition |
|---|---|---|
| Superseding decision | [ADR-010](../DECISIONS.md#adr-010--native-workstation-and-independent-uixsolver-boundary) | Proposed; ADR-008 and ADR-006 remain in force |
| Current behaviour and acceptance debt | [Browser parity inventory](BROWSER_PARITY.md) | Source/test evidence recorded; no witnessed UI acceptance |
| Licence/platform choices | [Decision points](DECISION_POINTS.md) | Primary-source review prepared; owner selections pending |
| Architecture and contract impact | Proposed sections in [architecture](../ARCHITECTURE.md#dw0-proposed-native-architecture) and [contracts](../CONTRACTS.md#dw0-proposed-boundary-contract-work) | No deployed schema change |
| Requirements | [Matrix](../REQUIREMENTS_VERIFICATION.md#native-requirements) | 16 plan IDs reserved as PLANNED at submission; evidence claims corrected |
| Verification/rollback of this work | [Appendix A record](CHANGE_RECORD.md) and [documentation patch](evidence/existing-documents.patch) | Review evidence; not an approval signature |

## Documentation impact set

Each target addition is explicitly proposed so the accepted baseline is not
silently replaced. Upon acceptance, record the disposition and make the approved
target normative with explicit migration notes; retain ADR history and the
browser implementation through DW9.

| File | Prepared change and later implementation dependency |
|---|---|
| [README](../README.md) | Index proposed ADR and DW0 package separately from accepted baseline |
| [Vocabulary](../VOCABULARY.md) | Define proposed UIX, command, worker, engineering hash, telemetry and lifecycle terms |
| [Architecture](../ARCHITECTURE.md) | Target runtime diagram, dependency matrix and composition-root exception |
| [Decisions](../DECISIONS.md) | Propose ADR-010; preserve all accepted ADR bodies |
| [Contracts](../CONTRACTS.md) | Command/event/worker/AI/transcript inventory, versioning and fixture plan; exact schemas freeze at implementation gates |
| [Model lifecycle](../MODEL_LIFECYCLE.md) | Read completely; unchanged. Scientific approval remains independently governed |
| [PFD specification](../PFD_SPECIFICATION.md) | Toolkit-neutral behavioural interpretation and native command/layout requirements |
| [Failure recovery](../FAILURE_RECOVERY.md) | Proposed worker/IPC, cancellation, artifact, desktop, AI/audio/transcription containment |
| [Dependencies](../DEPENDENCY_REGISTER.md) | Candidate desktop/build/provider entries and explicit ADR-006 distribution impact |
| [Requirements](../REQUIREMENTS_VERIFICATION.md) | Correct unsupported browser evidence and add proposed UIX rows; no VERIFIED promotions |
| [Milestones](../MILESTONES.md) | DW0–DW9 cross-links and DW3 mock versus DW5 integrated acceptance |
| [Action plan](../NATIVE_WORKSTATION_ACTION_PLAN.md) | Link this preparation record; phase and owner constraints retained |

## Gate review checklist

Preparation is complete when the linked artifacts are reviewable. **DW0 passes
only when the owner/steward records decisions and approval**, not when this table
exists or software tests pass.

| Gate item | Prepared evidence | Required disposition |
|---|---|---|
| Boundary and interaction direction | ADR-010; source/runtime distinctions; current implementation gaps | Owner/steward approve or amend |
| Licence posture | Decision L-01 with upstream sources, obligations and desktop policy impact | Select licence route; review exact adoption scope and compliance ownership; no production Qt while unresolved |
| Primary development and release platforms | Decision P-01; observed host distinguished from product support | Owner specify OS versions/architectures and first-release targets |
| Contract versioning and migration plan | Proposed contract inventory, identity gap, lifecycle/manifest choice and fixture plan | Steward approve staged plan; exact new schemas still require their own review |
| Browser parity and retirement/rollback | PAR-01–PAR-18; GAP-01–GAP-11; acceptance checklist | Steward adopt checklist and disposition of known gaps; no requirement waived by silence |
| Historical architecture gate | GATE-001–GATE-009 still IMPLEMENTED | Record existing M0 review disposition; DW0 is not a substitute for missing approval |

Approval record to complete: reviewer/role, date, exact package/ADR revision or
hashes, accepted/amended/rejected decision, chosen platform/licence options,
conditions, and approved follow-up scope. **Current record: pending, no approver.**

## Next work after approval

DW1 should begin with compatibility fixtures around the current HTTP payloads,
canonical artifacts and three legacy CLI demonstrations. Create neutral DTOs and
application ports, then move use-case orchestration out of endpoint ownership in
small steps. Use an in-process run-port adapter to preserve browser behaviour
until DW4, and keep existing module paths where compatibility requires them.
Do not turn the illustrative CLI calculations into promoted flowsheet models.

The first identity work must resolve exact engineering-hash validation and
presentation-only changes (GAP-01/GAP-02). Status/failed-result exposure and attempt
retention need contract analysis (GAP-03/GAP-06), rather than adding undocumented
fields to strict `v1alpha` artifacts. Fixtures must expose the current limitations
and require the intended behaviour when its approved change is implemented.

DW2 uses a mock run port; DW3 benchmarks and implements the PFD; DW4 supplies real
worker supervision; DW5 closes integrated run/results parity. DW6–DW9 remain
subject to their own provider, privacy, resource, packaging and release choices.
No high-refresh rendering, full dynamics, signal/control or industrial capability
is inferred from this sequence.
