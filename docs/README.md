# Architecture Preparation Package

This directory is the reviewed design input for the BH simulator.
The documents define a `v1alpha` contract baseline; they do not assert scientific
validation or industrial fitness.

## Reading order

1. [Vocabulary](VOCABULARY.md)
2. [Architecture and dependency plan](ARCHITECTURE.md)
3. [Architecture decisions](DECISIONS.md)
4. [Public contracts](CONTRACTS.md)
5. [Model lifecycle](MODEL_LIFECYCLE.md)
6. [PFD interaction specification](PFD_SPECIFICATION.md)
7. [Failure containment and recovery](FAILURE_RECOVERY.md)
8. [Dependency and licence register](DEPENDENCY_REGISTER.md)
9. [Requirements and verification matrix](REQUIREMENTS_VERIFICATION.md)
10. [Milestone backlog](MILESTONES.md)

Supporting records:

- [Model register](MODEL_REGISTER.md)
- [Native workstation and auditable AI action plan](NATIVE_WORKSTATION_ACTION_PLAN.md)
  — staged plan; DW0 direction approved through ADR-010 with annotations from Rayla May;
  later technology/provider and release gates remain applicable.
- [Reusable project continuation prompt](PROJECT_CONTINUATION_PROMPT.md)
  — bootstrap context for a new BH development chat.
- [DW0 native workstation review package](native/DW0_REVIEW.md)
  — dated preparation evidence and browser parity inventory.
- [Accepted ADR-010](DECISIONS.md#adr-010--native-workstation-and-independent-uixsolver-boundary)
  — native direction accepted 2026-09-11 with annotations from Rayla May; ADR history retained.
- [DW0 disposition by Rayla May](native/DW0_OWNER_DISPOSITION.md)
  — BH solver platform direction, Qt LGPLv3 and DW1 authorization.
- [BH Non-Commercial Source-Available License](../LICENSE)
  — project-wide terms for BH-owned material; copyright © 2026 Rayla May.
- [DW1 neutral application boundary](native/DW1_BOUNDARY.md)
  — command schemas, validation identity, compatibility and failure limits.
- [DW1 change and verification record](native/DW1_CHANGE_RECORD.md)
  — implementation scope, evidence, remaining gates and rollback.
- [DW1 documentation-derived review test batch](native/DW1_REVIEW_TEST_BATCH.md)
  — 80 proposed test families and evidence requirements; not yet executed.
- [DW1 rework batch](native/DW1_REWORK_BATCH.md)
  — failure-driven correction sequence and acceptance gates.
- [DW1 review preparation record](native/DW1_REVIEW_PREPARATION_RECORD.md)
  — documentation-only scope, source identity, verification and next work unit.
- [DW2 native shell guide](native/DW2_SHELL.md)
  — draft workflow, launcher, shortcuts, layout and mock-service limits.
- [DW2 change and verification record](native/DW2_CHANGE_RECORD.md)
  — historical implementation evidence and preserved baseline.
- [DW2 native macOS verification](native/DW2_MACOS_VERIFICATION.md)
  — launcher correction, witnessed draft workflow and remaining accessibility limits.
- [DW2 Qt development adoption](native/DW2_QT_ADOPTION.md)
  — exact optional dependencies and inventory; distribution compliance remains DW9.

- [2026-09-13 public verification baseline](native/PUBLIC_BASELINE_TRANSITION.md)
  — renamed root tree and qualification of sanitized historical evidence.
- [DW3 native PFD editor](native/DW3_PFD.md)
  — editing, stream naming, units, settings/templates and immutable native snapshots.
- [DW3 renderer measurements](native/DW3_BENCHMARK.md)
  — P-02 targets accepted by Rayla May; raster selected for the measured Mac reference.
- [DW3 native walkthrough](native/DW3_NATIVE_VERIFICATION.md)
  — observed native editing/save/reopen and remaining witness limitations.
- [DW3 change record](native/DW3_CHANGE_RECORD.md)
  — command/contract scope, verification, CI, risks and rollback.
- [DW3.1 UI layers, workspaces and extension record](native/DW3_1_CHANGE_RECORD.md)
  — visual groups, subsystem hashing, artifact-gated motion, workspace/control and
  plugin foundation with native animation evidence.
- [Extension foundation](extensions/README.md)
  — execution tiers, isolated protocol, proposed C ABI and scientific authority.

## Governance

The architecture steward owns contract changes. Any incompatible change requires
an architecture-decision update, schema-version change, migration fixture, and
requirements-matrix update. Scientific model approval follows the separate model
lifecycle and never occurs merely because code passes tests.

## Latest workstation work

- [DW4/DW5 senior-developer handoff](native/DW4_DW5_DEVELOPER_HANDOFF.md): proposed
  drag-and-drop follow-up, supervised solver, workbooks, docked/floating graphs,
  verification gates and mandatory documentation/onward handoff.
- [DW3.2 workstation guide](native/DW3_2_WORKSTATION.md): layout, persistent history,
  snapshots, alternatives, structural comparison, commands and workspace templates.
- [DW3.2 change and verification record](native/DW3_2_CHANGE_RECORD.md): exact scope,
  measured performance, compatibility, failures and remaining gates.
- [Following collaboration milestone](native/DW3_3_COLLABORATION.md): LAN/VPN shared
  editing direction and the protocol/failure gate required before enabling it.

## DW6 test-first handoff

- [DW6 developer handoff](native/DW6_DEVELOPER_HANDOFF.md): bounded implementation
  sequence, prerequisites, review and onward handoff.
- [DW6 acceptance specification](native/DW6_ACCEPTANCE_SPEC.md): owner-selected
  behavior, neutral interfaces, isolation, budgets, provider and audit policy.
- [Reviewer-controlled test package](../handoffs/dw6/README.md): executable tests,
  synthetic fixtures, integrity-enforcing runner and blank witness form.
- [DW6 preparation record](native/DW6_HANDOFF_RECORD.md): actual checks, expected
  initial failures, source identity, freeze digest and remaining acceptance work.

## Current DW4/DW5 remediation and repository handoff

- [2026-09-23 remediation record](native/DW4_DW5_REMEDIATION_2026-09-23.md): six
  third-review findings, follow-up fixes, exact checks and remaining gates.
- [GitHub sync record](native/GITHUB_SYNC_PREPARATION_2026-09-23.md): main-checkout
  selection, guarded integration, attribution, remote readiness and authorized sync.
- [Third review](native/DW4_DW5_THIRD_REVIEW_2026-09-16.md): retained rejection and
  historical evidence; its PASS conditions cannot be inferred from older test counts.
