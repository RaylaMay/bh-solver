# DW2 native macOS verification and launcher correction

Date: 2026-09-11. Author/witness: Rayla May. The record uses the computer-use tool and the local
development environment. Status: **NATIVE DRAFT WORKFLOW WITNESSED ON THIS HOST**.

The native BH solver window now launches and passes the bounded New/Save/Open,
unsaved Cancel, keyboard panel recovery, command palette and workspace-restart
walkthrough. This closes the earlier native-launch/walkthrough evidence gap for
this development checkout. It does not approve a standalone release, every
accessibility behavior, the renderer or scientific models.

## Objective, authority and scope

Rayla May requested: “Shall we verify this one?”, referring to the previously unwitnessed
macOS walkthrough and intentionally unavailable calculation controls, followed by
“continue with what you were doing before”. References: ADR-010; DW2;
UIX-DIST-001, UIX-CMD-001, UIX-A11Y-001 and UIX-DOC-001; CORE-008;
[original DW2 implementation record](DW2_CHANGE_RECORD.md).

Scope: diagnose native startup, correct the local developer entry point and
accessible status labels, conduct a native software walkthrough, add regression
checks, and update current documentation. No kernel, application policy, neutral
contract, storage schema, licence file, dependency lock or browser code changes.
No Qt/solver process coupling is introduced: the development host embeds Python,
which still wires only the existing mock-service desktop composition.

## Observed startup failure and selected correction

The original shell-script `.app` again returned `timeoutReached` from computer
use and left no BH process running. Launch Services startup-output capture exposed
Python failing before Qt initialization:

```text
Fatal Python error: init_import_site: Failed to import the site module
PermissionError: [Errno 1] Operation not permitted: '<project>/.venv/pyvenv.cfg'
```

The repository is inside Documents. Read-only System Settings inspection found
Documents access enabled for an existing Python entry but no BH solver entry.
That entry does not establish permission for this uv runtime or shell launcher.
No privacy toggle, Full Disk Access grant, TCC database or global protection was
changed by the agent.

Apple describes how loss of responsible-app attribution can suppress both the
permission prompt and the Files & Folders entry, and identifies a shell-script
`CFBundleExecutable` followed by `exec` as a possible cause. This is consistent
with the observed failure; internal TCC attribution was not independently traced.
[Apple developer guidance](https://developer.apple.com/forums/thread/125438).
Apple also documents the optional Documents usage-description key and normal
user-consent behavior. [Documents usage description](https://developer.apple.com/documentation/bundleresources/information-property-list/nsdocumentsfolderusagedescription).

`tools/macos_developer_main.m` supplies a small native Mach-O entry point. It reads
explicit Python/library/data-root paths from its generated Info.plist, dynamically
loads the selected environment's existing CPython library, and calls `Py_BytesMain`
in the same process. It contains no engineering calculation, UI command policy or
solver import. Python still selects this checkout's virtual environment. Qt and
Python are unmodified dynamic dependencies, not copied into the application.

`tools/make_macos_launcher.py` now builds that entry point with the installed
Apple clang/AppKit toolchain and applies a local ad-hoc signature. It supplies the
BH bundle identity and a Documents usage explanation. The helper retains its
refusal to replace an unmarked application. The generated ownership marker moves
into `Contents/Resources`, because its former loose Contents location caused the
first signing check to fail. Rebuilding with the corrected resource placement
passed strict signature verification and native launch.

This is a development-launcher correction, not selection of the final packager,
Developer ID certificate, notarization, OS minimum or distribution architecture.
It is built for the current host architecture and must be rebuilt after changing
the checkout/environment. Ad-hoc signing is not a release identity guarantee.
A future host may still require normal user-approved folder access; this result
does not promise that every machine will grant access automatically.

Material alternatives: retaining the shell wrapper preserves the reproduced
failure; launching through a terminal would not witness the requested app path;
broad permission grants would exceed the access needed for this diagnosis; a full
standalone runtime bundle would prematurely enter DW9. The native development
entry point supplies an identifiable app without changing the scientific stack.

## Native observations

The following outcomes were observed through the actual macOS application using
computer-use keyboard, accessibility-tree and screenshot APIs. Native screenshots
were inspected in the task; they are distinct from the historical offscreen PNGs.
The [witness ledger](evidence/dw2-macos/witness.json) records the bounded steps and
persisted draft identity for reconstruction.

| Check | Native observed result |
|---|---|
| Launch `.app` by path, then by bundle ID | Window titled BH solver; toolbar, docks and welcome view rendered; no terminal window or server needed |
| Command+N, enter a distinct name, Return | `DW2 native walkthrough 2026-09-11` displayed as Unsaved, with zero equipment/connections |
| Command+W while unsaved | Save / Cancel / Don't Save prompt appeared |
| Escape from that prompt | Same unsaved draft remained selected |
| Command+S | Saved locally, revision 1; Save became disabled; immutable JSON file appeared |
| Command+W, Command+O, Return on selected saved item | Named draft reopened at revision 1; Open activity message appeared |
| Close Inspector, Command+2 | Inspector returned and accessibility focus moved to its input table |
| Command+Shift+P, search `run.start`, Return | Palette showed Run — unavailable; Return left it open and did not execute |
| Toolbar calculation controls | Validate and Run exposed disabled state with an unavailable-service explanation |
| Light theme via palette; hide Inspector; Command+Q; reopen app | Light theme and hidden Inspector survived; welcome view had no selected draft or automatic Run |
| Restore default layout via palette | Navigator, Inspector and Activity visible again |
| Restore Dark theme; quit/reopen | Original theme and visible panels restored; saved draft remained listed |
| Compare saved draft before/after presentation and restart checks | Exact SHA-256 unchanged; runtime contained only workspace INI and draft JSON, with no run artifacts |

The tool occasionally required a fresh observation after reporting external UI
changes; actions resumed only after re-reading the current state. An initial
`Untitled draft` was saved and preserved before the separately named walkthrough
continued. Neither saved draft was deleted or used as scientific evidence.

One real accessibility defect was corrected: setting a generic accessible name
on dynamic status and selection labels caused macOS to expose the generic name
instead of their values. These labels now use accessible descriptions. The
restarted app's accessibility tree exposed the actual selected draft and the
independent state text:

```text
Not validated | Convergence: not run | Closure: not checked |
Physical: unknown | Correlation: unknown
```

Remaining accessibility limit: computer-use trees did not consistently enumerate
the saved-draft picker's rows or palette item text. Their visible selections and
keyboard behavior were witnessed with native screenshots and actions. This does
not establish how VoiceOver announces those lists. Full screen-reader, focus,
scaling and all-platform accessibility acceptance remains outstanding; no full
UIX requirement is promoted to VERIFIED from this walkthrough.

## Verification, files and impacts

Exact software checks and build commands are in
[verification.txt](evidence/dw2-macos/verification.txt). The
[dated file inventory](evidence/dw2-macos/file-inventory.json) and
[review patch](evidence/dw2-macos/changes.patch) distinguish this follow-up from the
original DW2 package. The previous DW0/DW1/DW2 evidence and the original DW2 change
record remain historical and unchanged.

The final Python suite passed **100 tests**, with the same upstream Starlette
deprecation warning recorded in DW2. Ruff lint and format checks passed; Pyright
with the explicit project interpreter reported zero errors or warnings. An initial
Pyright invocation selected the wrong interpreter and reported missing imports;
the corrected command is retained in the log alongside that failure. An initial
line-length issue in the new review helper was corrected before its final check.
The local app passed strict signature verification and was identified as Mach-O
arm64. These software results complement the native observations above.

Changed implementation: [launcher helper](../../tools/make_macos_launcher.py) and
[native entry point](../../tools/macos_developer_main.m);
[two accessible-label assignments](../../src/bh_sim/uix/window.py);
[desktop assertions](../../tests/test_desktop.py) and
[native-launcher tests](../../tests/test_macos_launcher.py). The
launcher tests build a separate temporary app, verify its Mach-O identity and
signature, invoke its embedded Python `--help` path without a GUI, and verify that
an unowned application is preserved. UI regression tests retain mock calculation
ports. Python lint/type/contract/boundary tests are rerun after the correction.
Browser source/fixtures and scientific files are checked against the dated baseline;
unchanged browser build/test checks from DW2 are not repeatedly re-run.

Schema/migration: none. Dependency/licence: no package or lock changes; the existing
Apple developer toolchain is required to rebuild this local macOS launcher.
AppKit is an operating-system framework; CPython remains dynamically loaded from
the existing environment. Qt remains under the selected LGPLv3 route and BH-owned
material under the adopted root license. Privacy/security:
no provider, upload, permission reset or expanded-access setting; the usage string
supports normal OS consent. Scientific impact: none; no calculation was performed.

Checks not run: VoiceOver, complete native accessibility matrix, Windows/Linux,
clean-machine installation, final runtime packaging, Developer ID/notarization,
release SBOM/library-replacement validation, performance benchmarks, worker tests
or independent scientific V&V. The latter stages remain governed by their own gates.

## Risks, rollback and next work

The launcher remains tied to this development environment and current architecture.
A missing/moved Python library or changed signing/access policy can still require a
rebuild or normal OS consent. Build/sign failures must be resolved before treating
a newly generated `.app` as runnable. This is not a transferable release artifact.

Rollback only this follow-up's recorded files after checking for newer edits by Rayla May.
The saved before-state and reversible text patch support source rollback; regenerate
the development launcher afterward. Reverting to the earlier shell wrapper also
restores its known startup limitation. Preserve all draft JSON and unrelated Rayla May
notes; do not perform a broad Git reset/clean in this untracked workspace.

No new decision by Rayla May is needed to use the corrected local preview. The existing
the adopted BH project license, final platform minimums, release signing/packaging,
renderer targets and later scientific/provider gates remain separate decisions.
The next desktop implementation stage remains DW3's renderer research and PFD
slice, with calculation controls staying unavailable until the worker integration.
