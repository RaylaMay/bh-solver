# DW0 browser parity and compatibility inventory

Date: 2026-09-10. Status: **OBSERVED BASELINE / PROPOSED ACCEPTANCE CHECKLIST**.

This inventory distinguishes source observations, automated evidence and required
future behaviour. No browser walkthrough or native implementation was performed
in DW0. A passing code-level test does not verify an interactive workflow. The
reference equipment remains software-integration fixtures, not approved physics.

## Inspected implementation and tests

| Evidence key | Inspected source |
|---|---|
| UI | [App.tsx](../../web/src/App.tsx): `Studio`, editing/validation/run/save/load handlers and React Flow wiring |
| EDIT | [Inspector](../../web/src/components/Inspector.tsx), [Palette](../../web/src/components/Palette.tsx), [catalogue](../../web/src/catalog.ts) |
| VIEW | [EquipmentNode](../../web/src/components/EquipmentNode.tsx), [ResultsPanel](../../web/src/components/ResultsPanel.tsx), [types](../../web/src/types.ts) |
| CLIENT | [HTTP client](../../web/src/api/client.ts), [preflight](../../web/src/validation.ts), [client tests](../../web/src/api/client.test.ts), [preflight tests](../../web/src/validation.test.ts) |
| API | [app](../../src/bh_sim/api/app.py): `DraftRepository` and endpoints; [adapter](../../src/bh_sim/api/adapter.py); [schemas](../../src/bh_sim/api/schemas.py); [API tests](../../tests/test_api.py) |
| KERNEL | [runner](../../src/bh_sim/engine/runner.py), [compiler](../../src/bh_sim/engine/compiler.py), [engine tests](../../tests/test_engine.py), [contract tests](../../tests/test_contracts.py) |
| STORE | [store](../../src/bh_sim/persistence/store.py), [codec](../../src/bh_sim/core/json_codec.py), [persistence tests](../../tests/test_persistence.py) |
| BOUNDARY | [import checks](../../tests/test_boundaries.py), [core quantity](../../src/bh_sim/core/quantity.py), [CLI](../../src/bh_sim/cli.py), [project dependencies](../../pyproject.toml) |
| AI | [profile policy](../../src/bh_sim/core/ai.py), [profile tests](../../tests/test_ai_profiles.py), [model register](../MODEL_REGISTER.md) |

## Behaviour inventory

All rows have **native acceptance pending**. “Observed” describes source, not a
witnessed UI result. Phase assignments are proposals under ADR-010.

| ID / requirement | Current behaviour and available evidence | Required acceptance / phase |
|---|---|---|
| PAR-01 / PFD-001 | UI starts with source→heater→radiator→sink and a fixed draft ID. EDIT exposes seven kinds including signed-duty heater/cooler; add copies defaults. API integration fixture runs all four initial units. | Preserve model/parameter mapping; add explicit case/draft navigation; test every palette kind, DW2/DW3 |
| PAR-02 / PFD-001 | React Flow owns pan/zoom/minimap/selection/movement. Move completion calls `markChanged`. No interaction tests present. | Native navigation/hit-testing and presentation-only movement with unchanged validation; measured renderer, DW3 |
| PAR-03 / CORE-003, PFD-001 | Handles use `in-N`/`out-N`; CLIENT counts total incident edges. API maps handles to kernel ports; compiler validates connections. Two preflight tests cover connected source/sink and missing heater ports. | Preserve IDs/handles on import; test kind/direction/multiplicity and nonexistent handles; only server compiler reports authoritative DOF, DW1/DW3 |
| PAR-04 / PFD-001 | Inspector edits label, numeric value and free-text unit. Editing unit text does not convert the value. Defaults are populated; blank number input becomes `Number('')`, i.e. zero. | Explicit unset/invalid input, reviewed display-unit conversion and engineering-edit classification, DW1/DW3 |
| PAR-05 / PFD-001 | Delete handler removes node and attached edges immediately; Inspector delete has no confirmation. No undo/redo command registry. | Confirm connected deletion; new draft edit with undo/redo and preserved identity, DW3 |
| PAR-06 / PFD-002 | Validate is explicit; local checks precede API compile. Server endpoint does not save. API test verifies subject-specific missing-input diagnostic. | Validate exact engineering hash without implicit save; stale responses cannot validate newer inputs, DW1/DW3 |
| PAR-07 / PFD-002 | Run is disabled only by `busy`, performs local checks and calls API without any prior-validation receipt. Isolated temporary-store probe confirms HTTP 200 without prior Validate. | Guard exact current hash and configuration, explicit run admission, no autosolve or stale-reply acceptance, DW1/DW4 |
| PAR-08 / CORE-010, PFD-003 | PUT saves normalized PFD revisions and GET loads latest. Three API tests include immutable/idempotent saves, repeated run revision and failed validation. Runtime status/metrics are stripped on save. | Preserve API behaviour and immutable revision identities; test incomplete drafts, save failure and explicit load selection, DW1/DW3 |
| PAR-09 / PFD-003 | Node positions and allowed node/edge extension fields are persisted. Top-level draft schema has no viewport field; no standalone canonical `PfdDocument` or UI file import/export command. | Versioned presentation round-trip including viewport/routes/extensions; canonical engineering import/export without UI leakage, DW1/DW3/DW5 |
| PAR-10 / PFD-004, CORE-008 | API emits convergence/closure booleans, per-node validity and formatted strings. Nodes display first two metrics and an extrapolation chip. Core retains all four scientific dimensions. | Transport and display all four independent run statuses, quantities and diagnostics without inferring missing status; full state matrix, DW1/DW5 |
| PAR-11 / CORE-009, PFD-005 | STORE last-valid SQL filters all four dimensions and has a failed-run test. UI retains `lastRun` only when convergence and closure pass, but applies every returned run's node overlays. | Distinct active, failed and last-valid selectors; preserve acceptable canvas and use application last-valid policy, DW4/DW5 |
| PAR-12 / PFD-005 | ResultsPanel compares displayed metric strings against one in-memory `previousRun`, up to eight changes. No persisted revision/run picker or structural case diff. | Select two immutable artifacts, distinguish parameter/topology/status changes and returned quantities; no UI engineering calculations, DW5 |
| PAR-13 / PFD-004 | Diagnostics render text. `subjectId` is transported but ResultsPanel has no object/field focus callback. Status text includes unqualified “Valid”. | Diagnostic navigation and qualified status labels with keyboard/focus and colour-independent evidence, DW3/DW5 |
| PAR-14 / CORE-009 | Client reports service unavailable/version mismatch; fetch supports AbortSignal but Studio supplies none. UI keeps editing state in memory; no reconnect reconciliation/cancel UI or disk recovery. | Disconnect state disables Validate/Run; explicit reconciliation, cancel, bounded worker faults and layout-only recovery; no replay, DW4/DW5 |
| PAR-15 / CORE-002, CORE-010 | STORE tests cover canonical four-state round-trip, field rejection, hash corruption and immutable indexing. Core artifact writes use fsync plus atomic hard link; PFD draft files use direct `write_text`. | Compatibility/migration fixtures and fault injection for both repositories; rebuild index without changing artifacts, DW1/DW4/DW9 |
| PAR-16 / UIX-A11Y-001 | Buttons and Inspector use native HTML controls; React Flow provides interactions. No recorded keyboard-only, focus, screen-reader, high-DPI or full status-matrix acceptance. | Witnessed essential workflows on supported targets, including connections/deletion/diagnostics; DW2/DW3/DW5/DW9 |
| PAR-17 / AI-001–003 | Core ChangeSet/profile tests exist; browser offers no AI/speech/session UI and API adapter chooses REVIEW. | Preserve existing authority; provider/session/voice/participant work is new DW6–DW8 scope, not an existing parity claim |
| PAR-18 / BOUND-001, UIX-ARCH-001 | Two static tests prohibit selected imports/text. FastAPI constructs concrete engine/store; adapter imports model ports/property fixture. CLI executes three prototype demonstrations. | Thin adapters over services, neutral imports and independent environments; preserve legacy CLI outputs and arguments without promoting models, DW1/DW4 |

## Material discrepancies and follow-up work

These are review findings, not repairs or new scientific approvals. Rayla May may
sequence fixes, but accepted requirements cannot be silently waived.

| Gap | Evidence and implication | Proposed Rayla May decision / next gate |
|---|---|---|
| GAP-01 — Validation identity | UI Run ignores `validation`; no engineering hash/receipt in HTTP. Local preflight can pass while server validation fails; no response/current-draft identity check. Contradicts PFD-002's enablement rule. | Application/UI maintainer; DW1 identity contract then DW3/DW4 workflow tests |
| GAP-02 — Presentation separation | UI movement clears validation; adapter copies label into `UnitDefinition.name`, so renaming changes canonical case hash. Probe: movement hash unchanged, label hash changed. Do not silently redefine canonical hashing. | Contract steward; DW1 hash/presentation design, DW3 mapping |
| GAP-03 — Status and failed-result visibility | HTTP lacks run-level physical/correlation fields. UI replaces node overlays on failed result, keeps no separate failed-run record, and comparison is in-memory strings. Requirements evidence previously overstated UI fallback/status testing. | Contract/UI maintainer; DW1 compatibility design, DW5 full status/history views |
| GAP-04 — Edit semantics | Numeric defaults, empty→zero, unit relabelling and connected deletion differ from PFD specification. Neither corrected behaviour nor undo/redo is tested in current browser suite. | Application/UI maintainer; DW3 command and input fixtures |
| GAP-05 — Local versus authoritative validation | CLIENT's incident-edge count is not port compatibility or solver DOF. No `isValidConnection` callback enforces application port kinds in App. Compiler/API checks provide authoritative diagnostics. | Application/UI maintainer; DW1 descriptor DTOs, DW3 local compatibility checks |
| GAP-06 — Run admission and recovery | Runner allocates run ID at return construction after compilation/evaluation; no persisted admission manifest, worker/cancel protocol or startup index-rebuild routine. Browser draft writes are direct. Adaptation rejection returns 422 before a core attempt artifact; probe confirms zero new core artifacts. Failure policy's complete coverage is not implemented. | Application/persistence maintainer and contract steward; DW1 contracts, DW4 fault/admission/persistence work |
| GAP-07 — Complete interchange/history | No UI import/export, persisted history picker, canonical case→PFD exporter, standalone PFD domain document or top-level viewport. API only loads latest PFD draft. | Contract/UI maintainer; DW1/DW3/DW5 compatibility work |
| GAP-08 — Neutral services and independent imports | `core.Quantity` imports Pint and `core` re-exports it; FastAPI owns concrete construction/orchestration; CLI bypasses services. Static tests scan selected top-level Python files/import strings and do not establish recursive/relative-import or separate-environment isolation. | Architecture maintainer; DW1 services/composition and import-fixture coverage |
| GAP-09 — Contract/document coverage | ADR-002 says every top-level artifact has schema version, but `DraftRevision` lacks a field; a full `RunManifest` is described in vocabulary/failure policy without an implementation. `ThermoProvider` terminology differs from implemented `PropertyPackage`. | Contract steward; DW1 explicit correction/migration decision, not a silent field addition |
| GAP-10 — Scientific governance labels | Register/cards mark reference models BLOCKED_EVIDENCE while the lifecycle's status list does not include that label. API executes fixtures under REVIEW with a warning; catalogue promotion/profile restrictions are not demonstrated by software tests. | Model/architecture steward; separate lifecycle/catalogue reconciliation before non-fixture use; no equation or approval changes in DW0 |
| GAP-11 — Evidence and historical gates | All GATE rows remain IMPLEMENTED; no approval signatures found. Browser matrix mentioned component/fallback tests but only five client/preflight tests exist. Pyright initially used the wrong interpreter; explicit repository interpreter passes. | Steward/reviewer; evidence claims corrected in DW0, M0 disposition remains required |

## Compatibility fixtures to freeze at DW1

Use the existing `tests/test_api.py::draft_payload`, contract sample cases,
four-state JSON fixtures and prototype CLI commands as inputs. Store golden
fixtures with their originating hashes before changing adapters. Include material
and model ID mappings, display units (including offset temperatures), extension
fields, missing/unknown data, failed runs and multiple immutable revisions.

The unchanged existing suite is a regression baseline. It does not yet contain
golden native/protocol fixtures, migration versions or UI interaction tests.
Generated run IDs/timestamps differ per attempt; compare deterministic engineering
content separately without modifying stored artifacts or hiding nondeterminism.

## Browser retirement and rollback checklist

All items below are **pending**. DW0 may approve the checklist; only DW9 can record
its completion and authorize retirement.

- Preserve the current browser/API launch path, schemas and source during migration.
  Establish a versioned reference release and reproducible environment before
  retirement; this no-commit working tree is not a release rollback point.
- Exercise PAR-01–PAR-18 on each approved native platform, with every gap resolved
  or explicitly re-scoped through its governing requirement/ADR process. Preserve
  the fixture-only labels; never make scientific promotion a side effect of parity.
- Witness draw/connect/edit/validate/run/save/reopen/compare/export; deliberate
  validation failure, solve failure and disconnected/worker-fault recovery; active
  versus failed versus last-valid results; keyboard-only essential actions.
- Verify old canonical artifacts retain their bytes/hashes and remain readable.
  Test old-browser→native→compatible-browser presentation/case round-trip or
  explicit loss diagnostics. Unsupported new features must fail visibly; no silent
  stripping or overwriting to make an old reader accept new state.
- Migrations create new artifacts with provenance, preserve originals and rebuild
  indexes. Test interrupted migration, corrupted input, disk/index failure and
  restoration against a copy of the pre-migration store without rerunning cases.
- Test native update/rollback on clean supported machines with installers and
  manifests. Returning to the retained browser/API must recover the last compatible
  immutable revision/run; newer incompatible artifacts remain retained separately.
- Record Rayla May's decisions on HTTP's installed role, signing/update/rollback policy,
  renderer targets, acceptance evidence and exact releasable source/build hashes.
- Only after Rayla May and the steward sign that evidence may browser retirement be
  proposed as a separate reviewable change. No automatic deletion follows from
  installing the native application.
