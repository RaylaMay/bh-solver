# Milestone Backlog and Acceptance Gates

Work proceeds in order. A milestone starts only after the preceding gate passes,
except isolated research spikes that create no production dependency.

## M0 — Architecture gate and `v1alpha` freeze

Deliver the documents indexed in [docs/README.md](README.md), review all ADRs,
render diagrams, and mark `GATE-*` requirements `VERIFIED`.

**Accept when:** an engineer can describe data formats, dependency directions,
interfaces, UI actions, and failure behaviour without making a new architecture
decision. Any unresolved scientific coefficients remain explicit model-card work.

## M1 — Contract foundation and prototype adaptation

Implement common quantities/statuses, Pydantic schemas, registries, thermo/unit/
solver protocols, immutable audit values, and adapters for current prototype
equations. Generate JSON Schema and migration fixtures.

**Accept when:** `CORE-001`, `CORE-002`, `CORE-006` through `CORE-008`, and
`BOUND-001` pass; existing hand-check results remain reproducible; no flowsheet or
UI imports prototype concrete classes directly.

## M2 — Cases, revisions, artifacts, and graph compilation

Implement stable IDs, canonical hashing, atomic JSON repository, rebuildable SQLite
index, port validation, DOF analysis, topological execution, and compile diagnostics.

**Accept when:** `CORE-002` through `CORE-005`, `CORE-009`, and `CORE-010` pass;
source→heater→sink saves, reloads, compiles, and executes deterministically; a bad
connection or incomplete specification produces stable diagnostics.

## M3 — First vertical slice

Add FastAPI and React PFD for sources, sinks, heater/cooler, mixer, splitter,
counterflow exchanger, and solid radiator. Support explicit Validate/Run, overlays,
revision/run comparison, JSON import/export, and last-valid fallback.

**Accept when:** all `PFD-*` requirements pass and a user can draw, validate, solve,
save, reload, compare, audit, deliberately fail validation, deliberately fail a
solve, and swap the reference property backend without changing the case.

## M4 — Recycles and replaceable solving

Add variable scaling, initialization, strongly connected groups, explicit tear
streams, specifications, SciPy root/bounded least-squares adapters, and convergence
history. Do not add new phase physics here.

**Accept when:** recycle fixtures converge from documented initial guesses; bad
initialization and infeasibility remain diagnostic; solver-adapter substitution
does not change case, unit, or result schemas.

## M5 — Phase-aware equipment and properties

Add higher-fidelity adapters, mixtures/phase states, pressure drop, pumps, valves,
turbines, and phase-aware exchangers/radiators through approved model cards.

**Accept when:** phase and energy closure, flash-pair contracts, domain-boundary
tests, backend comparisons, and independent V&V pass for each promoted model.

## M6 — Heat integration and studies

Implement immutable-result consumers for pinch, exergy, exchanger-network targets,
parameter sweeps, uncertainty, and sensitivity. These services cannot call unit
execution except through the versioned run coordinator.

**Accept when:** published/hand-calculated benchmarks and provenance manifests pass;
studies reproduce from stored inputs and never mutate their baseline.

## M7 — Dynamics, control, combat surges, and damage

Add inventories, ODE/DAE adapter contracts, controllers, events, thermal buffers,
damage injection, emergency endothermic cooling, and battle-short policies.

**Accept when:** steady-state limits agree with M5, event ordering is deterministic,
mass/energy accumulate correctly, failed safeguards are visible, and mission-kill
crew-safety scenarios preserve traceable assumptions.

## M8 — HAZOP-style safe-envelope exploration and AI profiles

Add deviation libraries, designed experiments/Monte Carlo, causal traces, constraint
maps, review/exploration/narrative ChangeSet workflows, and bounded natural-language
explanations.

**Accept when:** all `AI-*` requirements pass; envelope results distinguish sampled
evidence from interpolation; AI cannot approve, overwrite, suppress diagnostics,
or change canon.

## M9 — P&ID semantics and instrumentation

Add signal ports, instrumentation, alarms/interlocks, and P&ID presentation only
after dynamic contracts stabilize. Define the required validation, security,
release, and quality controls alongside the implementation.

**Accept when:** process and signal semantics are unambiguous, control diagrams
round-trip, and the applicable V&V, security, release, and quality plans are
independently approved. This milestone does not itself certify any operational use.

## Backlog control

Each work item records requirement IDs, model-card IDs, owner, evidence inputs,
files owned, dependency changes, tests, and rollback plan. New features cannot be
smuggled into a refactor milestone; architecture-affecting discoveries create an
ADR proposal before implementation.

## Proposed desktop workstream and DW0 handoff

The [native action plan](NATIVE_WORKSTATION_ACTION_PLAN.md#12-phased-execution-plan)
complements M0–M9; it does not renumber or approve scientific milestones.
[DW0's review package](native/DW0_REVIEW.md) was approved with
[owner annotations](native/DW0_OWNER_DISPOSITION.md) on 2026-09-11, authorizing
DW1. Later DW gates and software verification remain evidence-dependent.

DW1's neutral application extraction is implemented as of 2026-09-11, with
[software verification and compatibility evidence](native/DW1_CHANGE_RECORD.md).
DW2's [mock-service shell](native/DW2_SHELL.md) is implemented with
[software verification](native/DW2_CHANGE_RECORD.md), following the owner's
instruction to start the milestone and the
[exact local toolkit review](native/DW2_QT_ADOPTION.md). A
[native macOS follow-up](native/DW2_MACOS_VERIFICATION.md) corrects the local
launcher and witnesses the keyboard draft workflow, unavailable calculation
controls, panel recovery and theme/layout persistence across restart. Full
assistive-technology and installer acceptance remain. The next implementation
phase is DW3's renderer research/PFD slice after review of DW2 evidence; no worker,
cross-platform execution or release acceptance is inferred from the shell tests.

| Phase | Dependency and required exit evidence |
|---|---|
| DW0 | Review ADR-010, licence/platform posture, boundary versioning and browser parity/retirement checklist; record owner/steward disposition |
| DW1 | After DW0: neutral commands/services, thin HTTP/CLI adapters, golden compatibility fixtures and import tests; preserve legacy demo CLI behaviour |
| DW2 | After DW1 and toolkit approval: native shell/shared commands, mock run port and keyboard-accessible draft workflow |
| DW3 | After DW2: renderer evidence, native PFD, presentation round-trip, undo/redo and PFD acceptance; reconcile full run tests with DW4/DW5 integration |
| DW4 | After DW3: worker negotiation/supervision, crash/cancel/timeout/malformed-message tests, full artifact and telemetry separation; no new phase physics |
| DW5 | After DW4: workbooks, independent statuses, failed/last-valid/result comparison and complete draw-to-export acceptance |
| DW6 | After DW5 and AI context/provider policy: text workspace and attributable ChangeSet review/authority tests |
| DW7 | After DW6 and speech/retention policy: optional conversation/transcript-first workflows and failure/privacy tests |
| DW8 | After DW7: bounded independent participants, dissent and audit reconstruction; engineered scenarios depend on M8's governed study contracts |
| DW9 | After DW8: approved-platform installers, compatibility/migration/rollback and witnessed parity; browser retirement only on explicit acceptance |

DW3 can verify PFD commands using mock services; final end-to-end run parity is
repeated at DW5/DW9 with the worker. This proposed staging resolves the plan's DW3
PFD acceptance dependency on later run/result work without claiming early parity.
Dynamics, binary trajectories, controls and signal diagrams remain gated by M7/M9
and ADR-009 regardless of desktop progress. M0's existing `GATE-*` review records
remain outstanding and are not silently completed by DW0 preparation.
