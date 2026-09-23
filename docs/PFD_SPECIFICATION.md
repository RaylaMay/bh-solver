# PFD Interaction Specification

The first PFD is a local engineering editor, not an illustration tool and not a
P&ID. It edits a draft through application commands (the retained browser uses FastAPI)
and contains no equations.

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

Status: **ACCEPTED TARGET DIRECTION**, under ADR-010 and the disposition Rayla May
made on 2026-09-11. The action, state and accessibility
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

## DW3 implemented native editor

The [native editor guide](native/DW3_PFD.md) records the decisions Rayla May made
on 2026-09-13
and implemented interaction defaults. Orthogonal routes, vertical-gap/bridge
crossings, adjustable snapping, unique editable stream tags and explicit splitters
are presentation/application behavior. Original input notation is preserved alongside
quantities; case units and individual display overrides do not round calculation
inputs. Copy/paste defaults to equipment and parameters without connections.
Preferences can be previewed, edited and imported/exported as local templates.

The [benchmark](native/DW3_BENCHMARK.md) uses the accepted 50-equipment reference
and p95 targets. [Native witness](native/DW3_NATIVE_VERIFICATION.md) and automated
widget tests cover the implemented editor slice. Complete run/results parity
remains at DW4/DW5; these records do not mark every PFD acceptance requirement complete.

## DW3.1 layers, groups and workspaces

The native editor now exposes common PFD actions in a compact toolbar and keeps a
persistent **Layers & Groups** dock in the normal panel layout. Visual stream groups
may overlap and live with presentation state. Clicking a group applies its halo
without changing engineering selection; **Select members** is the explicit editing
action. Engineering subsystems use separate stable identities and participate in a
project engineering-content hash.

Stream drawing follows base colour, active-group halo, selected quantitative layer,
diagnostic pattern, focus/selection and animation-marker precedence. Labels,
patterns, tooltips and the scale/source legend preserve non-colour communication.
Before an attributable run or telemetry frame exists, streams remain static and
show direction arrows only. A typed frame supplies signed flow, units, source and
status. Reverse values reverse marker travel, zero values remain stationary, and
unavailable/failed values pause. Motion defaults to 30 fps, offers Off/15/30 and an
exploratory 60 setting, and obeys manual or system reduced-motion preference.

Flowsheet, Dynamics and Controls appear in a prominent switcher. Flowsheet is the
only enabled document today. The other buttons identify their missing M7/M9
capabilities rather than displaying placeholder calculations. See the
[DW3.1 change record](native/DW3_1_CHANGE_RECORD.md).

## DW3.2 modular workstation and history

Rayla May selected compact contextual controls by default, an optional ribbon,
independent case tabs, restorable named snapshots and continuous local recovery.
The [workstation guide](native/DW3_2_WORKSTATION.md) defines the implemented layout,
command grammar, version/undo semantics, templates and structural comparisons.
History, Diagnostics, Workbooks, Commands and Compare remain available through a
compact bottom access strip. The canvas replaces the earlier large page heading and
always-visible equipment table.

Personal selection, viewport, temporary group highlighting and isolation do not
create document undo entries. Shared presentation edits remain undoable without
changing engineering identity. Historical views are read-only; users explicitly
continue an alternative to edit them. Numerical workspaces and HAZOP execution keep
their existing gates. Live collaboration is the following separate milestone.

## DW6 AI workspace and source isolation — 2026-09-16

The [DW6 handoff](native/DW6_DEVELOPER_HANDOFF.md) specifies a dockable multiline AI
workspace, technical spelling, explicit selected-context preview, proposal review
and bounded exploration controls. Flush pending inspector edits before preview.
Tab changes cannot retarget a submitted question or an arriving proposal.

Exploration trials use separate case/result identities and cannot move the normal
history head, active overlay or last-valid result. Show source mismatch when the
original draft changes. Review adoption against the current target. Keep numerical
status displays authoritative over AI prose. Native implementation remains pending.

## DW5 stale-result correction — 2026-09-23

Workbooks and canvas badges carry the run's submitted native engineering identity.
Engineering edits keep them stale after Save. Undo to that source removes the stale
label; redo restores it. Movement, routing and other presentation-only edits do not
stale matching results. Failed attempts keep the previous acceptable overlay with
its own source identity. Unknown historical run identity is conservatively stale.
The [remediation tests](../tests/test_dw5_acceptance.py) supplement the existing
originating-tab, four-status retention and explicit-validation checks.
