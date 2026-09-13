# DW2 change record — native shell and command system

Date: 2026-09-11. Author: Codex, single implementation agent.
Status: **IMPLEMENTED; SOFTWARE CHECKS RECORDED; NATIVE WITNESS OUTSTANDING**.

BH solver now has a Qt Widgets draft workspace over neutral application commands.
New/Open/Save, docking, menus, command palette, shortcut customization, themes and
layout persistence are implemented. Calculation ports report unavailable and
supply no results. The browser and scientific baseline remain available.

## Objective and authority

Owner instruction: “Right. Start work on this milestone then.” This continues
DW2 after DW1's completed extraction. The preceding owner decisions select the BH
solver working name, macOS/arm64 first with future Windows/BH Linux design,
Qt/PySide's LGPLv3 route, and the adopted non-commercial source-available BH
project license. They are not reopened in this work unit.
[Owner disposition](DW0_OWNER_DISPOSITION.md).

References: ADR-010; native action-plan DW2 and Appendix A;
UIX-ARCH-001/002, UIX-DIST-001, UIX-CMD-001, UIX-A11Y-001, UIX-DOC-001;
BOUND-001; PFD-002/003; CORE-008/009/010; DW1 neutral boundary and frozen
compatibility fixtures. No scientific-model change or new model approval is sought.

## Scope, boundaries and exclusions

Scope: optional desktop dependencies and local adoption evidence; GUI entry point
and local macOS developer wrapper; shell/commands/workspace settings; neutral
draft create/list additions; isolated legacy draft storage; automated keyboard,
recovery, failure, boundary and compatibility checks; current-state documentation.

UIX receives a neutral `CommandGateway`. Application policy stays independent of
Qt, scientific and storage implementations. A dedicated preview composition binds
the retained draft repository and explicitly unavailable mock engineering/result
ports. The scientific composition root is not loaded by the shell. Existing HTTP
and CLI peers retain their behavior.

Out of scope: editable PFD/renderer selection, worker/run control, new workbooks,
AI/speech, dynamics, scientific implementation/V&V,
standalone installers, platform minimums or browser retirement. The local `.app`
wrapper is a development convenience, not the DW9 distribution deliverable.

## Evidence, assumptions and constraints

Repository status was inspected before editing. There is still no initial commit;
source/docs/tests are untracked user-owned work. A pre-DW2 file snapshot and dated
DW1 integrity check supplied the review baseline. The governing document set had
been read in the preceding continuation; relevant DW2, boundary, licence, platform,
UIX and recovery sections, source and tests were re-inspected for this stage.

The owner's UI notes were read as design/research context, including quoted
third-party rendering claims. They were not edited, adopted as instructions, or
treated as proof of acceleration, frame rate, 4K performance, controls or HAZOP
capability. Those claims require the plan's later research/scientific gates.

The host reports macOS 26.4.1 / arm64, Python 3.13.12. Exact Qt wheel hashes and
primary licensing/module sources are in the [adoption record](DW2_QT_ADOPTION.md)
and [wheel inventory](evidence/dw2/qt-wheel-inventory.json). Testing this payload
does not establish Windows/Linux behavior or a BH minimum supported OS version.

Material code/document discrepancy: the previous composition imported scientific
artifact reconstruction together with draft storage. The native shell needed draft
persistence without that runtime coupling. The draft repository was mechanically
separated, with old imports retained and old browser/canonical/CLI fixtures checked.
DW1's commands also lacked create/list, so explicit additive neutral contracts were
required rather than placing those use cases inside widgets.

## Selected design and rationale

- PySide6 Essentials/Shiboken 6.11.2 is an optional pinned development extra. UI
  imports Core/Gui/Widgets only; tests add QtTest. Essentials has a smaller payload
  than full PySide Addons but still contains unused modules/tools requiring a
  release inventory. The complete downloaded wheel is not cleared for redistribution.
- The main window uses Qt docks and system typography with editable design tokens,
  three themes, optional compact density, visible focus and textual status labels.
  Native widgets supply the shell while the DW3 renderer remains undecided.
- One presentation action registry supplies menus, toolbar, hotkeys, context menu
  and palette. Draft actions dispatch once through the shared application registry;
  dock/focus/appearance actions remain private presentation behavior. Applying
  shortcuts checks conflicts; restoring a complete map supports valid swaps.
- New drafts are unsaved, empty and visibly unvalidated. Opening reads saved work;
  Save acknowledges only a completed response. Save/Discard/Cancel protects unsaved
  drafts. Unsupported engineering commands fail before any mock execution.
- Workspace INI data is versioned, bounded presentation metadata. Restoring it
  never restores validation, opens cases or replays calculations. Corrupt/unknown
  state returns to default or the preceding layout; focus actions recover hidden docks.
- The GUI entry point and local `.app` wrapper require no browser/server. The wrapper
  references the existing checkout/environment and bundles no libraries. Full
  installer, signing and replacement/relink compliance remains DW9.

Alternatives considered: importing the real composition for draft access would
load scientific modules into the preview; manufacturing mock numeric results
would blur scientific authority; implementing use cases directly in Qt would
break replaceability. A full Addons dependency, production packager or PFD renderer
would broaden this milestone before its own evidence gate. None was selected.

Tradeoffs: draft operations remain synchronous with the legacy repository, so a
large/slow or damaged directory can block/fail discovery; this is not a scalable
worker/storage design. Multiple concurrent writers are not protected by a process
lock. The preview uses local session attribution (`local-user`), not authentication
or engineering approval. Activity messages are session feedback, not a durable ledger.

## Files, schemas and impacts

The [dated inventory](evidence/dw2/file-inventory.json) records before/after hashes;
the [text review patch](evidence/dw2/changes.patch) is relative to the pre-DW2
snapshot. PNG captures are separately hashed binary review assets, outside the
text patch. Old DW0/DW1 evidence is preserved as historical evidence, not regenerated
to claim it describes the new tree. Generated environment metadata, runtime/build
files and unrelated owner notes are excluded from the patch.

| Files/contracts | Change |
|---|---|
| `uix/` | Shell, shared presentation actions, design tokens and layout settings |
| `desktop_launcher.py`, `tools/make_macos_launcher.py` | Optional entry point and bounded local macOS launcher |
| `adapters/desktop_preview.py`, `adapters/drafts.py`, `adapters/storage.py` | Mock composition and mechanical draft-store separation with compatibility exports |
| `boundary/contracts.py`, `boundary/ports.py` | Immutable create/list DTO additions and neutral command gateway |
| `application/commands.py`, `application/ports.py`, `application/services.py` | Capability filtering, draft create/list policy and repository discovery port |
| `pyproject.toml`, `uv.lock` | Optional desktop extra, GUI entry; two package names added, no existing version changes |
| Desktop/boundary/contract tests, fixed DW2 fixtures | Keyboard, persistence/rejection, isolation and additive codec evidence |
| README, architecture/contracts/dependencies/requirements/milestones, native records/evidence | Implemented scope, launch guidance, tests, limits and rollback |

Schema/migration: additions retain `bh-command-v1alpha` because existing envelope
fields/tags/semantics are unchanged. Older strict codecs reject the new command
parameter tags; callers must inspect advertised capabilities. This is not a worker
negotiation protocol. Existing draft/canonical/HTTP formats and hashes remain
unchanged. No engineering-artifact migration or ad hoc binary authority is added.
Qt layout version 1 is separate presentation-only data. The precise additions and
recovery semantics are in the [shell guide](DW2_SHELL.md).

Dependency/licence: LGPLv3 is the selected Qt route under the existing owner
instruction. The actual wheel inventory does not supply a complete binary SBOM or
standalone notice/source bundle. Distribution closure remains an explicit DW9
obligation. `LICENSE` and package metadata identify Rayla May and the adopted BH
Non-Commercial Source-Available License. No paid/proprietary library is added.

Security/privacy: no server, provider, audio capture, telemetry service or data
upload is introduced. Package metadata/wheels were fetched from public upstream
sources for the authorized dependency. No cases or results were transmitted.
UI labels render as plain text; errors are sanitized by the existing registry.
The preview does not claim authenticated multi-user operation or industrial controls.

Scientific/validity: no numerical equations, coefficients, property data, catalogue
approvals or scientific contracts change. The four scientific dimensions remain
separate and unevaluated in the preview. Passing software tests is not V&V.

## Verification and observed limits

Exact commands and results are in the [verification log](evidence/dw2/verification.txt).
Final source checks: **98 Python tests passed** (one existing Starlette/httpx
deprecation warning); Ruff lint/format checks passed; Pyright reported zero errors
or warnings. Retained browser checks passed: five tests, lint and TypeScript/Vite
build. The checks include frozen HTTP/canonical/CLI behavior, Qt widget rendering,
neutral/UI import isolation, new command fixtures and document/inventory checks.

Qt tests exercise keyboard New with its real input dialog, Save, keyboard Open,
palette Close, focus recovery, shortcut conflict/swap restore, light/high-contrast
controls, layout restore/corruption, unsaved Cancel/Save protection, failed Save,
rejected payloads, name collisions and explicitly unavailable Run/Validate. A fresh
process performs New/Save/Open with scientific, artifact-store and FastAPI imports
blocked. Missing Qt yields an explicit capability diagnostic. The old 82 tests
continue to pass with the new desktop suite present.

Four [widget captures](DW2_SHELL.md#visual-evidence-and-remaining-gates) were rendered
and inspected. They use Qt's offscreen platform and the retained fixture's input
values; no solver or user case supplied those views. The full console log records
software counts. No UIX requirement is marked VERIFIED merely from these records.

Intermediate failures were resolved rather than hidden: a `QMainWindow.actions`
name collision and missing fake-port typing caused Pyright errors; a platform
plugin omitted the standard Quit binding; shortcut-map restore required atomic
validation; offscreen focus needed to settle after modal dialogs in the keyboard
test; corrupt-layout rollback exposed Qt's screen-clamping behavior and now restores
prior geometry explicitly. Ruff formatting/type issues were corrected. These
intermediate failures are superseded only by the final recorded passing checks.

Native interaction: computer-use `getApp` selection by the generated `.app` path
and then bundle ID returned `timeoutReached`, without an app view or accessibility
state. A first call remained blocked unusually long; bounded follow-ups also
failed. This is a tool failure and **not evidence that the app launched or failed
to launch**. The wrapper's `--help` path executes successfully, but no native macOS
walkthrough, assistive-technology check or terminal-free launch is claimed as
witnessed. Shell behavior is verified with Qt offscreen tests; the OS witness remains.

Checks not run: Windows/Linux execution, native screen-reader/focus/OS scaling
matrix, clean-machine installation, signing/notarization, Qt replacement/relink
verification, full SBOM/notice/source reconciliation, renderer benchmarks,
worker crash/cancel/timeout tests, full native PFD parity and scientific V&V.
They require later implementations, hardware/review or unavailable UI witness.

## Risks, rollback and remaining decisions

Known limits: no editable PFD or calculations in this preview; synchronous legacy
draft I/O and cross-process races remain; crash-durable autosave is not introduced;
local wrapper is tied to the checkout; native OS behavior and release packaging
remain unwitnessed. The optional desktop dependency is now installed in the local
development environment; the source import boundary is independently enforced.

Rollback: inspect the DW2 inventory and newer owner edits first, then reverse only
this work unit's text patch (binary captures may be removed only if their hashes
still match). Restore only the original modified files and remove only DW2-added
files that have no newer changes. Regenerate the environment from the restored
lock if needed. The generated wrapper and presentation settings can be set aside;
preserve every saved draft. Do not use broad Git reset/clean in this untracked tree.
No canonical case/run migration needs reversal; browser/CLI paths remain available.

Remaining work: native macOS interaction witness and review of this DW2 evidence;
then DW3 renderer research/PFD implementation, DW4 worker and DW5 workbooks before
full application parity. Outstanding owner decisions remain ownership/provenance
review for externally sourced material, contribution/reuse questions, later
benchmark fixture and target approval, final platform minimums, and later provider/privacy/release
choices. No new owner decision is needed to review this implemented mock shell;
the existing Qt route and platform direction stand.
