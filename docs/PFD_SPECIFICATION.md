# PFD Interaction Specification

The first PFD is a local engineering editor, not an illustration tool and not a
P&ID. It edits a `DraftRevision` through FastAPI and contains no equations.

## Screen layout

```text
+---------------- Project / revision / profile -------------------+
| Equipment |                 Canvas                 | Inspector   |
| Source    |  [Source]--s1-->[Heater]--s2-->[Sink] | Parameters  |
| Sink      |                         ! warning       | Units       |
| Heater    |                                         | Evidence    |
| Mixer     |                                         | Diagnostics |
| Splitter  |                                         |             |
| HX        |                                         |             |
| Radiator  |                                         |             |
+------------------------------------------------------------------+
| Draft changed | Validate | Run | Compare | Save revision          |
+---------------- diagnostics / run summary -----------------------+
```

Canvas nodes use stable unit IDs and edges use stable connection IDs. Positions,
edge routes, viewport, and collapsed panels live in `PfdDocument`; equations and
process state do not. Deleting a visual node proposes deletion of its unit and
connections and requires confirmation when connected.

## User actions

| Action | Required behaviour |
|---|---|
| Add equipment | Create unit from registered model definition with required ports and unset required parameters. |
| Connect | Permit outlet-to-inlet drag only; reject incompatible kinds immediately; multiplicity errors remain visible. |
| Edit | Display parameter value and unit separately; convert compatible display units without changing physical value. |
| Move/route | Change PFD presentation only; does not invalidate a solved engineering revision. |
| Validate | Save no changes implicitly; send the current revision and show schema, port, range, DOF, and compile diagnostics. |
| Run | Enabled only after validation of the exact current content hash; creates a new immutable run. |
| Compare | Select two revisions or runs and show additions/removals, parameter changes, state deltas, and status changes. |
| Remove | Confirm connected-unit removal; resulting edit is a new draft revision. |
| Save revision | Persist an immutable revision even when incomplete; never approve it automatically. |

Validation and Run are explicit. Any engineering edit changes the content hash,
marks prior validation stale, and disables Run until revalidation. Presentation-only
edits do not stale engineering validation.

## First-slice equipment and overlays

The palette contains source, sink, heater/cooler, mixer, splitter, counterflow heat
exchanger, and solid radiator. Open-droplet radiator may be displayed as a prototype
only if its model card permits the active profile.

After a run, selectable overlays show temperature, pressure, mass flow, duty,
convergence, closure, physical status, and correlation status. Values always show
units. `EXTRAPOLATED`, `INVALID`, unconverged, stale, and narrative-profile states
use text/icon labels in addition to colour.

## Failure and recovery UX

- Validation errors select and focus the affected object and field.
- Failed runs remain inspectable and never replace the last-valid overlay.
- The user can toggle between failed-attempt diagnostics and the last-valid result.
- API loss keeps unsaved edits in local draft memory, disables Run, and offers retry
  or JSON export; reconnect never silently submits changes.
- Autosave may store local presentation recovery data, but no autosolve or automatic
  approval is permitted.

## Accessibility and acceptance

All operations are keyboard reachable; ports and statuses have text labels; focus
is visible; colour is never the only signal. Acceptance requires draw, connect,
edit, validate, run, save/reload, compare, deliberate validation failure, deliberate
solve failure, and preservation of the last valid result.

## DW0 proposed native interpretation

Status: **ACCEPTED TARGET DIRECTION**, under ADR-010 and the 2026-09-11 owner
disposition. The action, state and accessibility
requirements above are the behaviour baseline for either client. The current
FastAPI/React implementation is retained. Native-specific presentation shall use
a dockable navigator/catalogue, flowsheet, inspector, workbooks, diagnostics and
separate active/failed/last-valid result views, through shared application commands.
Menus, buttons, context menus, command palette and keyboard bindings invoke the
same command and share its enablement/authority rules.

The [browser parity inventory](native/BROWSER_PARITY.md) separates implemented
features from missing evidence and noncompliant behaviour. In particular, native
acceptance requires exact-content validation, presentation edit classification,
unit-preserving display changes, connected-delete confirmation, four independent
result statuses and inspectable failed attempts. Reproducing current gaps does not
satisfy parity. Add undo/redo, keyboard-only acceptance and layout recovery in DW3;
rendering choice and performance remain subject to the DW3 benchmark gate.

Full dynamics, controls, signal diagrams and HAZOP overlays stay unavailable until
their underlying contracts and scientific milestones pass. AI/speech panels use
the same proposal authority as typed commands and cannot fabricate overlays.
