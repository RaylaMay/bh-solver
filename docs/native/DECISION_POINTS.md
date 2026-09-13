# DW0 platform, licence and later decisions by Rayla May

Prepared: 2026-09-10. Updated: 2026-09-13.
Status: **P-01, QT LGPLv3 ROUTE, AND BH NON-COMMERCIAL LICENCE ADOPTED**.

Rayla May approved DW0 with the [recorded annotations](DW0_OWNER_DISPOSITION.md).
Research below supports the selected route; it does not certify the compliance of
an unbuilt payload. Later decisions retain their separate gates.

## P-01 — Development and first-release platforms

Rayla May decided on 2026-09-11 to develop and release first on **macOS/arm64**, while
designing for eventual **Windows/x86_64** as well. **BH solver Linux** is planned.
Minimum OS/runtime/hardware versions will
be selected as the build becomes deployable. Only macOS test hardware is currently
available. Observed test host at DW0: macOS 26.4.1, arm64, Python 3.13.12.

| Earlier alternative considered | Disposition after Rayla May's decision |
|---|---|
| macOS/arm64 first release | Selected; design must anticipate Windows/x86_64 and eventual BH Linux |
| macOS/arm64 and Windows/x86_64 first release | Not selected; Windows release awaits suitable test evidence/hardware |
| A different explicit platform set | Linux distribution/architecture and all minimums remain later release decisions |

Qt's current supported-platform page lists desktop configurations for macOS,
Windows and Linux; support is tied to a Qt release and build environment. The page
served during review identifies Qt 6.11. This is upstream information, not evidence
that BH or a particular PySide wheel supports those targets. Pin and
verify the chosen release/toolchain against the matrix Rayla May approves before adoption.
[Qt supported platforms](https://doc.qt.io/qt-6/supported-platforms.html).

**Disposition: approved by Rayla May**, with minimums deferred by explicit instruction.
Cross-platform architecture is required now; release support requires actual
platform evidence later.

## L-01 — Qt licence route and distribution scope

Rayla May decided on 2026-09-11: **Qt/PySide under LGPLv3**, no commercial Qt licence
route at this stage. On 2026-09-13, BH-owned project material adopted the
[BH Non-Commercial Source-Available License](../../LICENSE), copyright © 2026
Rayla May. Third-party dependencies and externally owned material retain their
own licenses.

Qt offers commercial and open-source licensing; module licences differ and some
modules are GPL-only for open-source users. Its third-party components and SBOM
also need review. A generic “Qt is LGPL” entry does not identify the obligations
of an actual installer. [Qt licensing](https://doc.qt.io/qt-6/licensing.html).

Qt for Python separately documents third-party components in addition to its
LGPL/commercial licensing, so PySide/Shiboken and bundled Qt/plugin contents must
all appear in the selected payload inventory.
[Qt for Python licences](https://doc.qt.io/qtforpython-6/licenses.html).

| Route considered | Disposition / remaining review |
|---|---|
| LGPLv3 compliance route | Selected for Qt/PySide; identify exact modules/plugins and implement/test applicable distribution obligations |
| Commercial Qt route | Rayla May excluded it at this stage |
| Alternate native toolkit | Contingency if the selected route cannot meet compliance or measured requirements |

For an LGPL route, Qt's published guidance identifies library source availability,
licence notices, user ability to replace/relink the library and run the result,
and compatible distribution terms. Dynamic linking alone is not a completed
compliance assessment. Review the final packaging/signing arrangement and any
distribution-store restrictions against the applicable licence text.
[Qt LGPL obligations](https://www.qt.io/development/open-source-lgpl-obligations).

The proposed initial module scope is Core/Gui/Widgets plus necessary platform
plugins; accelerator/Quick, audio and other modules require their own inventory
when added. This is a proposed scope, not a verified package manifest. Do not
automatically bundle every installed PySide add-on.

**Project policy impact:** Rayla May accepted ADR-010's scoped desktop-distribution
exception to ADR-006. It is confined to the reviewed desktop payload and does not
add Qt to default kernel dependencies. Scientific data retains its own rights.
Existing grants and third-party terms must be preserved alongside the adopted
BH-owned-code license selected by Rayla May.

Adoption evidence still required: exact version and artifact hashes, module/plugin
and third-party SPDX inventory, licence texts/notices, source/terms records as
applicable, distribution-channel assessment, compliance responsibility and
reviewer/date. A chosen open-source route does not certify a future installer;
final payload compliance must be rechecked at DW9. **Route and BH license adopted;
exact payload compliance remains pending.**

## Packaging research input

`pyside6-deploy` is documented as a Nuitka-based tool; its options include
standalone and one-file output and controls for Qt modules/plugins. This makes it
a candidate for a bounded packaging spike, not proof of correct worker startup,
signed distribution, rollback or LGPL library replacement.
[Qt deployment tool](https://doc.qt.io/qtforpython-6/deployment/deployment-pyside6-deploy.html).

No packager, signing identity, distribution store, update service or dependency
version has been selected or installed by DW0.

## Later decisions — keep separate from DW0 implementation authority

| ID | Decision and information to provide | Required by |
|---|---|---|
| P-02 | Initial 50-equipment reference and p95 33 ms paint / 50 ms synthetic event-to-paint targets accepted 2026-09-13; see disposition below. Future OS/GPU/display expansion remains open. | [DW3 measured evidence](DW3_BENCHMARK.md); no 4K/144-Hz or 10,000-item promise |
| D-01 | Whether FastAPI remains an optional installed capability and its approved use case | Final packaging design/DW9; retain existing source through migration |
| AI-01 | Local/remote AI and transcription providers; permitted attached context and capability limits | DW6/DW7 before provider implementation/use |
| S-01 | Separate audio/transcript retention, deletion/export and explicit-send policy for each voice mode | DW7; typed text remains capable |
| AI-02 | Participant count, elapsed time, tokens, tool calls, solver runs and retries | DW8; no inferred numeric defaults |
| D-02 | Packager, signing/distribution, update cadence and compatible rollback policy | Packaging spike and DW9 release |
| AI-03 | Any use of outputs for a corpus/training/fine-tuning and associated independent review | Separate proposal before any collection or training |

The entries in this later-decisions table remain pending. Choosing a native toolkit does not choose a provider,
authorize context upload, establish a retention duration or approve training.
DW0 approval and P-01/L-01's route are recorded in Rayla May's disposition.
Later policy choices remain deferred to their named gates.

## P-02 initial disposition by Rayla May — 2026-09-13

Rayla May accepted in this task: reference scene of 50 equipment, p95 paint
≤33 ms and p95 synthetic event-to-paint ≤50 ms on the available Mac, with p99
and correctness reported. Small 10 and exploratory 100 scenes provide context;
100 is not a promised acceptance level. [DW3 evidence](DW3_BENCHMARK.md) records
measured limits and selects raster for the initial editor. Future platform/display
matrices and larger realistic workloads remain separate decisions, not implied
approval of 4K/144-Hz or 10,000-item performance.
