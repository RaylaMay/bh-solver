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
  — staged plan; DW0 direction approved through ADR-010 with owner annotations;
  later technology/provider and release gates remain applicable.
- [Reusable project continuation prompt](PROJECT_CONTINUATION_PROMPT.md)
  — bootstrap context for a new BH development chat.
- [DW0 native workstation review package](native/DW0_REVIEW.md)
  — dated preparation evidence and browser parity inventory.
- [Accepted ADR-010](DECISIONS.md#adr-010--native-workstation-and-independent-uixsolver-boundary)
  — native direction accepted 2026-09-11 with owner annotations; ADR history retained.
- [DW0 owner disposition](native/DW0_OWNER_DISPOSITION.md)
  — BH solver platform direction, Qt LGPLv3 and DW1 authorization.
- [BH Non-Commercial Source-Available License](../LICENSE)
  — project-wide terms for BH-owned material; copyright © 2026 Rayla May.
- [DW1 neutral application boundary](native/DW1_BOUNDARY.md)
  — command schemas, validation identity, compatibility and failure limits.
- [DW1 change and verification record](native/DW1_CHANGE_RECORD.md)
  — implementation scope, evidence, remaining gates and rollback.
- [DW2 native shell guide](native/DW2_SHELL.md)
  — draft workflow, launcher, shortcuts, layout and mock-service limits.
- [DW2 change and verification record](native/DW2_CHANGE_RECORD.md)
  — historical implementation evidence and preserved baseline.
- [DW2 native macOS verification](native/DW2_MACOS_VERIFICATION.md)
  — launcher correction, witnessed draft workflow and remaining accessibility limits.
- [DW2 Qt development adoption](native/DW2_QT_ADOPTION.md)
  — exact optional dependencies and inventory; distribution compliance remains DW9.

## Governance

The architecture steward owns contract changes. Any incompatible change requires
an architecture-decision update, schema-version change, migration fixture, and
requirements-matrix update. Scientific model approval follows the separate model
lifecycle and never occurs merely because code passes tests.
