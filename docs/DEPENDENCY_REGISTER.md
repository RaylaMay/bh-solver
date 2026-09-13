# Dependency and Licence Register

Exact versions are locked by the repository lock file and recorded in each run
manifest. A dependency update requires tests, licence review, and regenerated
software-bill-of-materials data. “Data licence” is assessed separately from code.

## Default product stack

| Component | Purpose and boundary | Code licence | Data/licence note |
|---|---|---|---|
| Python | Kernel runtime | PSF-2.0 | No scientific data |
| NumPy | Private numerical arrays | BSD-3-Clause | No scientific data |
| SciPy | Default solver adapter and numerical algorithms | BSD-3-Clause | No property data |
| Pint | Boundary unit validation/conversion | BSD-3-Clause | Unit definitions reviewed with upgrades |
| Pydantic | API/schema validation | MIT | No scientific data |
| NetworkX | Private graph compiler implementation | BSD-3-Clause | Objects never persisted |
| FastAPI | Local HTTP application adapter | MIT | No scientific data |
| Uvicorn | Local ASGI server | BSD-3-Clause | Development/local deployment |
| React | Browser UI | MIT | No engineering equations |
| TypeScript | Browser type checking/build | Apache-2.0 | Tooling only |
| `@xyflow/react` | PFD canvas | MIT | Presentation state only |
| SQLite | Local artifact index | Public Domain | JSON artifacts remain canonical |
| pytest / Hypothesis | Verification | MIT / MPL-2.0 | Development only; MPL package unmodified |
| Ruff / Pyright | Lint, format, type checks | MIT / MIT | Development only |

The repository's root licence file and package metadata specify the BH
Non-Commercial Source-Available License; Rayla May owns the BH material. Qt/PySide follows
the selected LGPLv3 route. Third-party dependencies and externally owned
material retain their own terms and are not relicensed by this repository.
Scientific papers, extracted tables, fitted coefficients, property
datasets, setting canon, and user-supplied source documents retain their own
licences and are not relicensed merely by being referenced from this repository.

## Optional research adapters

| Adapter | Intended use | Distribution policy |
|---|---|---|
| CoolProp | Open property backend and benchmark | Optional extra; record package and data provenance |
| Cantera | Reaction/equilibrium research | Optional extra; not a kernel requirement |
| ChEDL / `thermo` | Process correlations and cross-checks | Optional extra; verify dataset licences per source |
| Pyomo / HiGHS | Optimisation studies | Optional extra behind optimisation port |
| SALib | Sensitivity and uncertainty studies | Optional study dependency |
| CasADi | Future DAE/optimisation research | Optional; licence review at adoption |
| REFPROP | High-fidelity proprietary properties | User-installed adapter; never redistribute binaries/data |
| Commercial simulators | Independent comparison and import/export | External workflow; do not embed proprietary formats without permission |

No optional package becomes a transitive default dependency. Missing optional
adapters produce capability diagnostics, not fallback to unlabelled correlations.

## Property and evidence data register

Every dataset record contains its dataset owner or publisher, citation, retrieved date, version,
hash, permitted uses, redistribution status, modified/unmodified status, and models
that consume it. Public accessibility is not evidence of redistribution permission.
Generated coefficients retain links to the source dataset and fitting procedure.

## Deferred plugins and tools

- Consensus, SciSpace, Sider Scholar, PDF review, Jupyter, spreadsheets, and
  visualization support research; their outputs are not numerical authorities.
- Wolfram is deferred for independent symbolic/numerical checking.
- GitHub is deferred until a remote review workflow exists.
- Codex Security is deferred until API/UI and dependency surface warrant it.

## DW0 proposed desktop dependency review

No packages or lock files change in DW0. The following are candidates, not adopted
dependencies. The [decision brief](native/DECISION_POINTS.md) records primary
sources checked on 2026-09-10; the
[2026-09-11 disposition by Rayla May](native/DW0_OWNER_DISPOSITION.md) resolves the platform
direction and Qt LGPLv3 route. The following table retains DW0's candidate review;
DW2's bounded local adoption is recorded below. Distribution compliance remains open.

| Candidate | Boundary | Licence/data review required before adoption |
|---|---|---|
| PySide6, Shiboken6, Qt Core/Gui/Widgets and platform plugins | Desktop only | Selected LGPLv3 route; select exact versions/module/binary inventory and verify applicable LGPL and third-party redistribution obligations |
| Qt OpenGLWidgets / optional Qt Quick | Rendering spike only | Separate module/plugin inventory and renderer evidence; no default acceleration claim |
| `pyside6-deploy` / Nuitka toolchain | Build/distribution only | Review tool, bundled runtime/plugin licences and generated payload; do not infer signing, worker packaging or compliant library replacement from executable creation |
| Spellcheck adapter | Desktop text port | Select code separately from technical dictionaries, dictionaries' redistribution terms and user additions |
| Audio capture adapter | Desktop device port | Package/platform permissions and code licence; retention is a separate policy for Rayla May |
| AI and transcription adapters | Optional provider ports | SDK code licences, model weights/service terms, context policy and audio/transcript retention; no provider selected |

ADR-006 still excludes non-permissive dependencies from the default kernel.
Rayla May accepted ADR-010's scoped desktop-distribution exception on 2026-09-11
and selected the LGPLv3 Qt/PySide route. Exact payload/compliance review remains
required; placing Qt in an extra is not sufficient evidence. Dependencies requiring
a commercial licence purchase are excluded at this stage. Exact component
SPDX identifiers and hashes must be recorded for the chosen payload, separately
from code, model weights, scientific data and dictionaries. No legal-compliance or
release-platform approval is asserted by this register.

### DW2 local desktop adoption

The optional `desktop` extra now pins `PySide6-Essentials==6.11.2` and
`shiboken6==6.11.2`, with Python below 3.15 markers matching upstream bounds.
The [adoption record](native/DW2_QT_ADOPTION.md) identifies downloaded wheel hashes,
module/plugin inventory, selected LGPLv3 route, third-party licence evidence and
unresolved build-specific notices/source/SBOM work. Only these two package names
were added to the lock; existing versions and default kernel dependencies remain
unchanged. UI code imports Core/Gui/Widgets; tests additionally use QtTest.

Essentials includes more modules/tools than this shell uses. Its installation
does not adopt those modules or clear the complete wheel for redistribution.
The local macOS launcher references the existing environment and bundles no
runtime. Its [native startup correction](native/DW2_MACOS_VERIFICATION.md) uses
the already installed Apple developer tools to compile a small AppKit entry point
and apply an ad-hoc signature. It dynamically loads the selected environment's
CPython library; no Python/Qt binary is copied or modified. This local build
prerequisite does not select a final packager or approve a release platform.
DW9 must review the actual distributable closure, source/notices,
replacement/relinking, signing and platform requirements. No commercially
licensed library is selected. The root BH license remains separate from all
third-party dependency terms.

### DW3 renderer research and CI

The production editor continues to use Core/Gui/Widgets, with no lockfile change.
The local benchmark additionally imports QtOpenGLWidgets/QtOpenGL from the already
installed PySide6 Essentials 6.11.2 wheel. This is research-only use, not inclusion
in an approved distributable. The [Qt OpenGL licensing documentation](https://doc.qt.io/qt-6/qtopengl-index.html)
identifies its LGPLv3 option; actual release notices/source/replacement obligations
remain DW9. No commercially licensed library or new binary package was added.
OpenGL visual acceptance was not established; [raster is selected](native/DW3_BENCHMARK.md).

GitHub Actions use official checkout/setup-python/setup-node actions and the existing
locked Python and npm dependencies. They build and test; they do not publish,
deploy, acquire signing credentials or approve the application licence. Hosted
runner results remain unobserved until this local workflow is pushed and runs.
