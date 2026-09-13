# DW3 native macOS verification

Date: 2026-09-13. Author: Rayla May. Status: **SCOPED NATIVE WALKTHROUGH OBSERVED**.
Rayla May's record reports native UI observations, not an independent
engineer witness, scientific validation or complete accessibility acceptance.

An isolated local developer app was built using the existing launcher helper at
`.bh/BH DW3 Verification.app`. Its generated bundle name/identifier and data root
were set to a dedicated verification identity and `.bh/dw3-verification`. It uses
the checkout's existing environment; no runtime or library was copied. The existing
user app and its draft directory were not replaced or closed. The wrapper remains
a local ad-hoc developer build, not a signed/notarized distribution.

## Observed workflow

Native accessibility state and screenshots in this task showed:

1. Launch into the native BH welcome screen without a browser or manual server.
2. New draft creation and a visible unsaved state. The test draft retained the
   default name `Untitled draft`; a requested automated name replacement did not
   take effect, so this record does not claim that replacement worked.
3. Add Source from the palette; add Sink using the shared Cmd+Shift+A command.
   The palette was selected visibly, and equipment counts changed to two.
4. Drag Source to a new canvas position. The layout edit produced an unsaved state.
5. Drag the Source output to the Sink input. The canvas showed one orthogonal
   stream labeled `S-001`, with both endpoint handles attached.
6. Enter `1.000` for Source pressure, then set its submitted unit to `bar`. The
   native inspector showed `100000` under `Pressure [Pa]`, with `bar` as the
   submitted unit. Other required inputs remained visibly missing.
7. Request connected deletion. The native confirmation explicitly named the
   connected stream count. A subsequent automation sequence resulted in deletion;
   because the cancellation click was ambiguous, native **cancellation is not
   certified by this sequence**. Automated widget tests independently exercise No.
8. Cmd+Z restored both equipment items and their stream. Cmd+S acknowledged a new
   immutable revision, disabled Save, and showed `Saved locally · Revision 2`.
9. Cmd+O and Return reopened that saved revision. Native screenshot/state showed
   two equipment items, the `S-001` orthogonal route and retained layout. Validate
   and Run remained disabled with independent unavailable scientific states.

The generated [witness document](evidence/dw3/native-witness-document.json) is the
saved test fixture captured after this workflow. It contains only the explicitly
created test objects, submitted pressure notation and presentation; it is not an
engineer's case or a calculated artifact. The screenshots are visible in
this task's native-tool transcript; this record does not claim an exported raw
screenshot file for that walkthrough. Renderer PNGs are separately generated Qt
captures and must not be described as native automation screenshots.

## Defects found and corrected

Zero-vertical-delta wheel events were incorrectly treated as zoom-out, reducing the
view to its 0.1 minimum during native interaction. The canvas now ignores those
phase/horizontal events. A regression test sends a zero-delta Qt wheel event and
asserts unchanged scale. Explicit 100% zoom and Fit flowsheet commands provide
keyboard recovery. The follow-up native workflow above displayed full-size symbols
and saved/reopened scale 1.0.

Native-only shortcut preferences were restored before their extended actions existed,
producing misleading startup diagnostics. Restoration is now deferred until the
native action registry is complete. Automated restoration tests cover the shared
registry; this small follow-up was not part of the already-running native process.

## Limits and failed attempts

Locating a standalone Python/OpenGL probe through native automation timed out.
The isolated `.app` wrapper resolved that app-discovery problem for the editor
walkthrough. OpenGL visual acceptance remains unresolved; see the
[renderer record](DW3_BENCHMARK.md). Some accessibility-index actions selected
rather than activated Qt list items; pointer coordinates from current screenshots
and the shared keyboard action completed the workflow. No OS privacy/security
permission was changed to force automation.

This is not a complete VoiceOver or keyboard-only witness. Native template import,
all routing/crossing cases, multi-monitor behavior, printing/export, installation,
Windows/Linux UI and physical input-to-photon latency remain unverified. The
[automated suite](../../tests/test_pfd_editor.py) supplies separate widget evidence.
Worker/result/failed-run/last-valid behavior remains DW4/DW5 scope.

The isolated verification app was closed after saving; the subsequent native app
inventory no longer listed it as running. The separate pre-existing user app was
not targeted by that close action.
