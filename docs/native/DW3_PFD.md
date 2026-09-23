# DW3 native PFD editor

Status: **IMPLEMENTED EDITOR VERTICAL SLICE; FULL WORKSTATION PARITY OPEN**.
Date: 2026-09-13. Authority: ADR-010; instruction from Rayla May to build the editor and
approved P-02 initial acceptance targets. This is a local concept-development
preview with reference test fixtures, not approved scientific models.

The native launcher now opens `PfdEditorWindow`, which extends the retained DW2
shell. React/FastAPI and the independently tested shell remain available. The
canvas imports only Qt, standard-library and neutral boundary types. Editing policy
and unit conversion are dispatched through the shared command gateway.

## Editing workflow

Create a draft, activate equipment in the palette, and position symbols on the
canvas. New required parameters remain unset. Select equipment in the canvas or
keyboard-accessible equipment table to edit its inputs. All seven current reference
models are represented: source, sink, heater, radiator, mixer, splitter and heat
exchanger. Model descriptions retain **TEST FIXTURE ONLY** authority.

Drag an output handle to an input handle, or use **Edit PFD → Connect typed ports**.
Port direction, declared kind and multiplicity are checked by application policy.
A crossing, alignment or visual snap never joins streams. Dragging from an existing
stream to an input inserts a visible splitter; its required split fraction remains
unset. No composition or flow is inferred from a stream tag.

Streams receive unique case-local tags, initially `S-001` onward. Permanent object
IDs remain unchanged on rename. F2 opens rename; a collision identifies the
conflicting stream and offers an explicit swap. Settings can instead choose the
next available number. Linked split branches default to `(a)` and `(b)`, with
independent numbering available. Parent rename previews linked branch changes;
manual branch renames detach that tag from the naming family. Any family collision
rejects the entire edit. Settings changes affect future numbering, not existing tags.

Routes are orthogonal doglegs. Return paths use explicit outside stubs. The initial
crossing convention gaps the vertical segment; bridge crossings are configurable.
Grid spacing, snap distance in viewport pixels, grid/alignment/port snapping and
handle sizes are preferences. Alt-drag a stream to adjust its middle vertical
route segment (or use Adjust route segment from the keyboard); **Reset automatic route** clears the manual points. Endpoint stubs
follow equipment movement. This is a trial routing policy: it does not guarantee
obstacle avoidance, optimal routing or elimination of every overlapping label.
Those limitations are visible layout issues, never automatic topology changes.

Middle-button drag pans and the wheel zooms. 100% zoom and Fit flowsheet are
shared commands; zero-delta wheel events do not alter zoom. Equipment selection supports multiple
objects. Cmd/Ctrl+C and Cmd/Ctrl+V copy equipment and submitted parameters without
connections. The context menu also offers internal connections or unset inputs.
Every pasted unit/stream receives a new permanent ID and available tag. Connected
equipment deletion requires confirmation; Cancel preserves the document. Undo and
Redo restore immutable snapshots through application policy and never replay Run.

## Units, preferences and templates

SI is the initial display preset. Case preferences and per-input display overrides
are available. Original numerical text and submitted unit are retained separately:
`1.000 bar` displays as `100000 Pa` with the default precision and returns to
`1.000`/`bar` for editing. **1 bar = 100,000 Pa**. Focus/blur without a change is a
no-op. Empty required inputs say **Input required** and are never replaced by zero.

The established finite double-precision quantity/Pint adapter handles compatible
units, including offset temperature units. No engineering equation or unit
conversion resides in Qt. Display precision changes formatting only. The optional
significant-figure count is an explicit preference, not an accuracy inferred from
input digits. Calculated-result formatting remains inactive while results are
unavailable; it must not be used to round stored inputs or artifacts.

PFD settings include a small detail-field set, colours, snapping, routing, numbering,
unit preferences and shortcut bindings. Expand/collapse and pin/unpin retain detail
visibility separately from engineering data. Details show submitted inputs and
unavailable status, never synthetic results. Local JSON template import fills an
editable preview; Apply is explicit. Export and Reset are available. Unknown schema
fields/types and executable content are rejected. Templates are bounded to 100 KB;
clipboard selections to 2 MB. No upload or remote service is involved.

## Persistence and boundaries

`bh-pfd-document-v1` is an additive neutral JSON envelope around the existing
`DraftDto`. It carries object presentation, original input notation, naming lineage,
case preferences and viewport. Scientific canonical schemas are unchanged.

New native snapshots live in `native-drafts/` below the configured local data root.
The directory is separate from legacy `drafts/`. Native open prefers its own
revisions and can import a legacy draft without modifying the legacy bytes.
Native-only metadata is not written back into a browser revision. Browser migration
or export with complete native presentation is not claimed.

Snapshots use SHA-256 draft-name filenames, strict tagged JSON, an explicit 20 MB
bound, fsynced temporary files and exclusive atomic publication. Identical saves
are idempotent. A concurrent publication collision fails explicitly; the caller
retains unsaved work. Previously saved revisions are never overwritten. Save/open
cannot validate a case, run the solver or advance the last-valid result.

Engineering edits change equipment/connection fields. Routes, viewport, preferences,
notation and position changes remain presentation metadata. Shared labels/positions
are synchronized while preserving legacy compatibility extensions. Existing
engineering-hash rules continue to exclude names/layout; canonical source-artifact
hashes still retain labels for auditability.

## Acceptance boundary

See [change record](DW3_CHANGE_RECORD.md), [measurements](DW3_BENCHMARK.md) and
[public baseline](PUBLIC_BASELINE_TRANSITION.md). Automated widget tests use the
Qt offscreen platform and do not establish native accessibility or physical input
latency. Native renderer measurements use the Cocoa platform on this Mac.

Validate, Run, worker recovery, calculated overlays, run comparison and last-valid
selection remain explicitly unavailable pending DW4/DW5. Therefore UIX-PFD-001 and
full PFD-002/004/005 native parity are not marked VERIFIED by this work. Production
packaging, printing/export acceptance, VoiceOver, Windows/Linux hardware and
minimum-OS testing remain separate gates. No browser implementation is removed.

## DW3.1 visible interaction additions

The common Select, Connect, Rename, Delete, Undo/Redo, Fit, zoom, Layers/Groups and
Settings actions now remain visible in a compact PFD toolbar. A persistent
**Layers & Groups** dock sits with Navigator and Equipment. It separates base
appearance, overlapping visual stream groups, engineering subsystems, unavailable
result layers and motion controls. A visual-group click highlights members without
changing selection; **Select members** performs the explicit editing selection.

Base stream colour, labels, line style/width and animation preferences persist with
the PFD. The existing local settings template continues to carry the synchronized
base stream colour. The canvas shows static direction arrows before results exist.
Only an attributable visualization frame enables markers and a source/scale legend.
Manual and operating-system reduced-motion preferences pause moving markers.

Flowsheet is enabled in the workspace switch. Dynamics and Controls remain disabled
and name their missing M7/M9 capabilities. Review the separate
[DW3.1 record](DW3_1_CHANGE_RECORD.md) for contracts, extension policy and benchmark
scope.
