# DW2 native shell

Date: 2026-09-11. Status: **IMPLEMENTED; NATIVE macOS DRAFT WORKFLOW WITNESSED**.
This local development preview provides New/Open/Save and workspace controls
through the neutral application boundary. The full flowsheet editor, calculation
worker, workbooks and packaged release retain their later gates.
[Original implementation record](DW2_CHANGE_RECORD.md) and
[native verification follow-up](DW2_MACOS_VERIFICATION.md).

## Launch and local data

One-time developer setup from the repository root:

```sh
uv sync --extra api --extra desktop --group dev --inexact
.venv/bin/python tools/make_macos_launcher.py
```

On macOS, the helper uses the installed Apple developer tools (`xcrun clang` and
`codesign`) to create `.bh/BH solver.app`. Its native entry
point dynamically hosts this checkout's existing Python, preserving the app's
process identity. Open that application for a window without a terminal or server.
Native launch and the draft walkthrough passed on the development macOS/arm64 host;
the follow-up record documents the former shell launcher's startup failure.

This developer application bundles no runtime, requires this checkout and
environment, and must be regenerated after moving them. It has a local ad-hoc
signature, not a Developer ID/notarized DW9 installer. Normal OS folder consent
may be required on another host. Build/sign failure requires correction before
the generated application can be treated as runnable.

The optional GUI entry point is `bh-workstation`. Developer invocation:

```sh
.venv/bin/bh-workstation --data-root .bh/native-preview
```

The wrapper uses that same repository-local data root. Without `--data-root`, the
entry point uses Qt's application-local data directory for BH solver.
`drafts/` holds existing-format immutable PFD revisions; `workspace.ini` holds
presentation preferences. Opening saved work lists drafts in the selected root;
DW2 does not introduce arbitrary-file import/export or relocate browser artifacts.
A developer can explicitly choose `.bh/runtime` to use the retained
browser draft directory. Avoid concurrent writers: the legacy draft store is
process-local and has no cross-process locking guarantee.

The optional desktop extra pins Essentials/Shiboken 6.11.2; no paid library is
introduced. [Exact toolkit review](DW2_QT_ADOPTION.md). The launcher rejects an
absent desktop runtime with `DESKTOP_RUNTIME_UNAVAILABLE`; it does not silently
start the browser or change a backend.

## Available interaction

The window has a saved-draft navigator, a read-only equipment/input inspector,
an activity panel, menus, toolbar, command palette, customizable shortcuts and
movable/resizable docks. Dark, Light and High contrast themes share versioned
design tokens; compact density is optional. No animation is enabled.

| Action | Default shortcut on macOS / Windows and Linux | Behavior |
|---|---|---|
| New draft | Command+N / Ctrl+N | Enter a name; creates an unsaved empty draft |
| Open draft | Command+O / Ctrl+O | Choose the latest saved revision in this data root |
| Save draft | Command+S / Ctrl+S | Explicitly persist; acknowledge only after success |
| Close draft | Platform standard Close, normally Command+W / Ctrl+W | Save/Discard/Cancel protects unsaved work |
| Quit | Platform standard Quit, with Command+Q / Ctrl+Q fallback | Protect unsaved work and save layout |
| Command palette | Command+Shift+P / Ctrl+Shift+P | Search and invoke the same menu/toolbar actions |
| Focus Navigator / Inspector / Activity | Command+1 / 2 / 3; Ctrl+1 / 2 / 3 | Reveal a hidden panel and move keyboard focus |
| Shortcuts, themes, density, restore layout | Workspace menu or command palette | Presentation-only changes |

Qt's platform bindings determine displayed modifier names. The defaults above
have offscreen test evidence and a bounded native macOS keyboard walkthrough for
New/Open/Save, unsaved Cancel, palette, panel focus and layout recovery.
Windows/Linux and full native assistive-technology behavior remain unwitnessed.
Shortcut edits reject ambiguous or multi-stroke bindings. A valid saved swap is
restored atomically; an invalid map retains the existing/default map and reports
why. Native dock toggles and focus controls are also discoverable in the palette.

Buttons, menus, palette, context menu and hotkeys reuse individual `QAction`
objects. These map engineering operations to one injected neutral
`CommandGateway`; presentation actions stay in UIX. No Qt object crosses that
port. `local-user` is a local session attribution label, not authenticated identity
or a qualified-engineer approval. Session activity is visible feedback, not a
durable engineering audit ledger.

Validate and Run are disabled with explanations. Attempted unsupported command
dispatch returns `CAPABILITY_UNAVAILABLE`. The mock engineering/result ports
raise the same absence diagnostic and supply no calculated values. Validation,
convergence, closure, physical validity and correlation validity remain separate
textual states; disabled controls explain solver availability. The inspector shows submitted input values and units,
without conversion or interpretation as results.

## Contracts, compatibility and recovery

The `bh-command-v1alpha` family gains `CreateDraftParameters`,
`ListDraftsParameters`, `DraftSummaryDto` and `DraftListDto`; existing envelope
fields, tags and meanings are unchanged. `CommandGateway` declares command-name
discovery and synchronous dispatch. Implementations advertise only supported
commands. An older strict codec rejects the new parameter tags; these additions
do not promise that an old receiver understands a new command. The future worker
must negotiate its own protocol/capabilities at DW4. Fixed DW2 fixtures accompany
these additions; all DW1 fixtures remain unchanged.

`draft.create` checks the name and existing normalized file identity, then returns
an unsaved empty `DraftDto` with revision 1, a UTC creation timestamp and empty
presentation. It creates no canonical case, validation receipt or run. Invalid,
blank, padded or over-120-character names fail. Existing names and filename
normalization collisions return `DRAFT_EXISTS`; Save retains the original
idempotent, immutable revision policy. A concurrent process can still race this
check, an inherited repository limit requiring later storage work.

`draft.list` reads and validates saved legacy revisions and returns the newest
revision per draft ID in name order. An unreadable/corrupt revision fails visibly;
it is not silently skipped. No scientific operation occurs during discovery.
Draft storage is mechanically separated from scientific artifact storage, while
old Python imports are retained as re-exports. Existing `PfdDraftDto` JSON,
canonical artifacts, HTTP endpoints, CLI outputs and presentation extensions
retain their formats; no engineering migration is performed.

Layout format version 1 contains Qt geometry/dock bytes (bounded to 64 KiB each),
theme, density and shortcut overrides. Unknown or malformed layout state falls
back to default presentation; a partial restore rolls back. Restore default layout
and keyboard panel-focus actions recover hidden docks. Layout restore does not
open a draft, save engineering data, restore a receipt or replay Run. Save failure
keeps the current draft dirty; Cancel leaves it selected. A rejected command's
payload is never treated as an acknowledged Save.

## Visual evidence and remaining gates

The [native follow-up](DW2_MACOS_VERIFICATION.md) records actual macOS screenshots
and accessibility-tree observations inspected in the task, including theme/layout
persistence across app restarts. Full VoiceOver/list announcement checks remain.

The following are actual Qt widget captures from temporary fixture storage using
Qt's offscreen plugin. They are not macOS screen captures or performance evidence.

- [Welcome](evidence/dw2/shell-welcome.png)
- [Draft inputs, Dark](evidence/dw2/shell-draft-dark.png)
- [Draft inputs, Light](evidence/dw2/shell-draft-light.png)
- [Draft inputs, High contrast](evidence/dw2/shell-draft-contrast.png)

DW3 owns renderer measurements, the editable PFD, undo/redo and presentation
round-trip. DW4 owns worker negotiation and run control; DW5 owns results and
workbooks. DW9 owns complete runtime packaging, licence closure, signing,
clean-machine/platform acceptance and browser retirement. No installer,
performance target, OS minimum, scientific model or industrial approval follows
from this shell implementation.
