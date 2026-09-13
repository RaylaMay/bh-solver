# DW2 Qt development adoption record

Date/reviewer: 2026-09-11, Codex. Scope: local development and testing of the
authorized DW2 shell under ADR-010 and the owner's selected LGPLv3 route.
This is not clearance to redistribute an installer or the complete wheel payload.

## Selected dependency and observed artifacts

Pin `PySide6-Essentials==6.11.2` and `shiboken6==6.11.2` in the optional `desktop`
extra. Default kernel requirements are unchanged; BH-owned project material follows
the adopted root non-commercial license.
Both downloaded macOS wheels match their PyPI SHA-256 records. Their metadata
declares `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only`; the selected route is
LGPLv3. The complete file/module/platform-plugin inventory is retained in
[qt-wheel-inventory.json](evidence/dw2/qt-wheel-inventory.json).
[PySide release](https://pypi.org/project/PySide6-Essentials/6.11.2/),
[Shiboken release](https://pypi.org/project/shiboken6/6.11.2/).

The inspected wheels target macOS 13+ universal2 and CPython 3.10–3.14. Current
testing uses macOS/arm64 with CPython 3.13.12. The optional extra is gated below
Python 3.15; an unavailable desktop runtime must produce an explicit diagnostic.
These upstream bounds are not final BH minimums. Windows/x86_64 and Linux wheels
exist upstream, but no BH execution evidence is claimed on those platforms.

## Runtime scope and licence evidence

| Component used | Selected route / evidence |
|---|---|
| PySide bindings and Shiboken runtime | Wheel metadata above; unmodified dynamic libraries |
| QtCore | LGPL-3.0-only route; [module attributions](https://doc.qt.io/qt-6/qtcore-index.html#licenses-and-attributions) |
| QtGui and Cocoa platform plugin | LGPL-3.0-only for Qt; Cocoa third-party attribution BSD-3-Clause; [module attributions](https://doc.qt.io/qt-6/qtgui-index.html#licenses-and-attributions) |
| QtWidgets | LGPL-3.0-only route; [module licensing](https://doc.qt.io/qt-6/qtwidgets-index.html#licenses) |
| QtTest and offscreen plugin | Verification only; [QtTest attributions](https://doc.qt.io/qt-6/qttest-index.html#licenses-and-attributions) |

Core's upstream third-party list includes BSD, MIT, Apache-2.0, zlib, CC0,
Unicode and public-domain components, including PCRE2's package exception. GUI's
list additionally includes font, FreeType, PNG/JPEG and ICC terms. The permissible
FreeType licence alternative must be retained when distributing it. These module
lists describe possible compiled contents; they are not a binary-level SBOM.
Qt for Python has its own [third-party attribution list](https://doc.qt.io/qtforpython-6/licenses.html).

The Essentials wheel also installs QML/Quick, OpenGL, Designer, Lottie and other
modules/tools. Installing that development wheel does not select those modules
for BH runtime use or approve their redistribution. Production UI imports are
restricted to Core/Gui/Widgets; tests additionally use QtTest. There is no selected
OpenGL viewport, commercial licence purchase, proprietary library or renderer
benchmark claim.

## Gaps and distribution gate

Neither inspected wheel contains a separately named licence/notice bundle or
SBOM. Do not copy the whole environment into a release and call it LGPL compliant.
Before DW9 distribution, identify the actual loaded/bundled closure, recover its
build-specific notices and source, choose licence alternatives, prune unused
modules/tools, and test replacement/relinking with the chosen signing/installer
arrangement. Retain installation information where applicable and a named release
compliance review. Upstream [PySide source archives](https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.11.2-src/)
are available; matching Qt build/source and third-party inputs remain part of the
release evidence, not an assumed result of package installation.
[Qt obligations](https://www.qt.io/development/open-source-lgpl-obligations).

The DW2 macOS launcher is a local developer wrapper around this repository's
environment. It does not redistribute Qt or bundle a standalone runtime. This
bounded development adoption follows the existing owner decision; no additional
platform/licence-route approval is needed. The root BH license remains separate
from Qt's upstream LGPLv3 terms.

## Review rationale

Objective: supply the authorized mock-service shell with the selected toolkit.
Alternatives: the full PySide metapackage also brings Addons; a renderer/packager
change would exceed DW2. The smaller Essentials distribution still needs the
inventory and release restrictions above. Verification: archive SHA-256 comparison,
metadata/file inspection and primary module licence pages; actual import/runtime
tests and all work-unit impacts are recorded in the DW2 change record. This
record approves local development scope only and grants no new rights in upstream
code, engineering cases or results.
