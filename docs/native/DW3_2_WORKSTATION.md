# DW3.2 workstation and persistent history

Date: 2026-09-14. Rayla May authorized this work through the interface and
persistent-history implementation plan. This guide describes implemented local
behaviour; it does not approve a scientific model or a release.

## Working with the interface

The desktop launcher opens the canvas-centred workstation. The project toolbar
provides New, Open, Save, Undo, Redo and Snapshot. The contextual toolbar provides
Flowsheet/Dynamics/Controls navigation and editing actions. Ribbon replaces that
contextual toolbar when enabled; both surfaces invoke the same QAction handlers.
Dynamics and Controls still explain their M7/M9 capability gates.

Case tabs retain independent selection, viewport and history. The left docks hold
a searchable project browser, equipment and Layers & Groups. The inspector shows
submitted quantities and their units, with expandable identity/model details.
The equipment table lives in Workbooks. A bottom access strip keeps History,
Diagnostics, Workbooks, Commands and Compare reachable when their docks collapse.
The View menu retains full panel management.

Design maximizes the canvas; Compare opens checkpoint selectors and structural
changes; Review exposes the history browser for selecting a baseline. These are
layout presets, not scientific workspaces. Users can resize, float, hide and restore
docks. Workspace templates include layout, theme, density, ribbon and shortcuts;
import previews those preferences and rejects invalid templates before applying
changes. Templates exclude case data, command recall and personal identity.

A visual-group click highlights streams without changing editing selection or
history. Isolate toggles a temporary personal view, including hiding ungrouped
streams; clicking Isolate again restores visibility. Group definitions, persistent
visibility and case styling remain undoable presentation edits. Engineering
subsystems remain separate engineering edits. Selecting, panning and zooming do not
create document-history entries.

## History terms and behaviour

| Action or record | Meaning |
|---|---|
| Recovery history | The application durably records each completed logical edit locally. Closing a tab does not discard it. |
| Save version | The application publishes a native immutable revision and records the acknowledgement in history. Undo/redo survive Save. |
| Named snapshot | A named immutable checkpoint of the current engineering document and shared presentation. It can capture incomplete work. It does not run or approve the case. |
| View selected | Opens an exact historical checkpoint read-only. Return to current restores the active working state. |
| Continue as alternative | Starts a named editing path from the chosen checkpoint, retaining the current path and all previous records. |
| Undo / Redo | Records an attributable reversal and restores checked checkpoint data. It does not erase the original edit. |
| New edit after Undo | Creates an alternative path while preserving the abandoned redo path in History. |
| Compare | Compares two saved versions or snapshots, including across cases. It shows engineering and presentation field changes. |
| Export flowsheet image | Saves a PNG of the visible canvas. This is separate from a restorable snapshot. |

The command service owns history. It stores immutable canonical JSON checkpoints
and ordered, hash-verified JSON events in the local `history` directory. The event
sequence forms a rebuildable index; no SQLite database contains the sole copy.
Each event records a stable local actor ID, request ID, timestamp, parent, branch,
affected objects, classification and before/after identities. Local actor IDs do
not expose the operating-system username and do not claim authenticated identity.

Save does not alter the working checkpoint's original draft metadata. A
`SavedVersionReference` carries the separately published native revision number;
the header displays that number. Snapshot names are metadata, not scientific
approval labels. The snapshot contract reserves hash-addressed result references;
the current preview has no selected run artifact and therefore records no result
links. DW4/DW5 must connect those links to verified artifact selection.

Continuous recovery persists committed edits, not uncommitted keystrokes in a field.
Save, Snapshot, tab changes and window close finish modified input rows before
continuing. Queued input edits retain their originating case identity. Save remains
available while a field is being edited, including after a previously clean save.
A storage rejection leaves the previous committed document active and displays a
diagnostic. A checkpoint written before an interrupted journal commit remains an
unreferenced file, not the current state. A native Save completed before a failed
history acknowledgement may leave a saved revision; retrying Save reuses that
revision and records the acknowledgement without rerunning anything.

Every disk read still checks content hashes. Bounded caches retain decoded immutable
DTOs to avoid repeated parsing; they do not skip byte verification. Startup reads
checkpoints rather than replaying commands. Command text in the journal is audit
data and never executes. Corrupt/gapped history rejects opening rather than quietly
returning an older head. Prior native saved revisions remain separate and intact.
History detects accidental corruption, not malicious rewriting of an entire chain
or deletion of an unknown final suffix; there is no signing or external anchor.

Old native/browser drafts import as one explicitly labelled starting point, with no
invented earlier edits. Original files remain unchanged. Existing history remains
the workstation's working authority; changes made through another legacy client
require explicit import/reconciliation and are not a live synchronization path.
History retention is unlimited on disk unless a later explicit retention policy is
approved. The current UI loads a case's event index in memory; very long histories
need a separately measured paging improvement before large-history performance
claims.

## Command line

The Commands dock accepts a closed application grammar. It is neither a shell nor
a Python console. Quote names containing spaces. Up/Down recall the last 100 local
entries without executing them. Autocomplete uses object names, catalogue model
and parameter names, typed ports, canonical units and configured/submitted units.

```text
add source
add sink
connect Source-001 out-0 Sink-001 in-0
set Source-001 pressure 1.000 bar
select Source-001
rename Source-001 Feed
snapshot "Design review baseline"
save
undo
redo
help
```

GUI and command-line edits reach the same application policy. Connected deletion
and family/tag-swap renaming retain the same confirmations. A command never evaluates
an expression or bypasses unit validation. Result and Run commands remain unavailable
until their native integration gates pass.

## Evidence and remaining gates

The [change record](DW3_2_CHANGE_RECORD.md) reports exact checks and observed limits.
The [clickable prototype](prototypes/dw32-layout.html) captures the initial layout
proposal; native screenshots represent the implemented interface.

Live editing over LAN/VPN belongs to the [following collaboration milestone](DW3_3_COLLABORATION.md).
This workstation reserves attributable histories and checks against the current history head; it
does not start a network service. Review layouts do not implement HAZOP execution,
participant records, approvals, numerical dynamics or controls. Native assistive-
technology verification, cross-platform native execution and installer acceptance
remain distinct gates.
