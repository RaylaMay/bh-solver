# BH solver

An auditable, local-first thermofluid simulator for BH technical
development. The current `v1alpha` is a modular monolith: immutable scientific
contracts and a Python kernel sit behind neutral application services and a
versioned FastAPI adapter. The retained React PFD and a DW2 native draft-workspace
preview are peer presentation clients.

BH solver is the working name for this non-commercial project, owned by Rayla May.
The owner-approved
native-workstation direction targets development and first release on macOS/arm64,
with the architecture designed for eventual Windows/x86_64 and Linux support.
See the [owner disposition](docs/native/DW0_OWNER_DISPOSITION.md).

BH-owned project material is licensed under the [BH Non-Commercial
Source-Available License](LICENSE), copyright © 2026 Rayla May. It may be used,
modified, and shared only for non-commercial purposes. Third-party dependencies,
datasets, and other externally owned material retain their own licenses; Qt/PySide
is tracked separately under the selected LGPLv3 route.

This repository does not establish setting canon and is not qualified for
industrial or safety-critical use. The reference coolant is deliberately
illustrative; every promoted scientific model must pass the evidence and
verification lifecycle in [docs/MODEL_LIFECYCLE.md](docs/MODEL_LIFECYCLE.md).

## What is implemented

- Architecture preparation package and accepted `v1alpha` decisions.
- Explicit quantities with Pint-backed conversion and separate convergence,
  closure, physical-validity, and correlation-validity statuses.
- Immutable `CaseDefinition`, `DraftRevision`, `CompiledFlowsheet`, and
  `RunResult` contracts with canonical JSON and content hashes.
- Pure, single-phase polynomial-liquid properties behind replaceable flash
  contracts, including visible extrapolation.
- Port validation, degrees-of-freedom reporting, cycle detection, and
  deterministic acyclic execution.
- Sources, sinks, duty heater/cooler, mixers, splitters, effectiveness heat
  exchangers, and a first-pass solid-radiator model.
- Replaceable SciPy bounded-least-squares adapter.
- Immutable JSON run artifacts, SQLite index, and last-valid pointer.
- Neutral immutable commands/results and application services with validation
  receipts, result inspection and comparison; see the
  [DW1 boundary](docs/native/DW1_BOUNDARY.md) and
  [verification record](docs/native/DW1_CHANGE_RECORD.md).
- Local React PFD with explicit Save, Load, Validate, and Run actions, engineering
  overlays and prior-run comparison. The persistence layer protects last-valid
  results; browser overlay/status and stale-validation gaps remain recorded in
  the [parity inventory](docs/native/BROWSER_PARITY.md).
- Guarded review, exploration, and narrative AI change-set profiles.
- Native Qt Widgets shell with keyboard-accessible draft creation/open/save,
  shared actions and command palette, docking, themes and workspace preferences.
  Calculation services are explicitly unavailable in this mock-service preview;
  see the [DW2 shell guide](docs/native/DW2_SHELL.md) and
  [native macOS verification](docs/native/DW2_MACOS_VERIFICATION.md).

The older modules `thermo.py`, `stream.py`, `unit_ops.py`, `radiators.py`,
`transients.py`, and `audit.py` remain prototype reference calculations. They are
not the stable flowsheet API.

## Architecture package

Start with [docs/README.md](docs/README.md). It links the vocabulary, diagrams,
ADRs, contracts, model lifecycle, PFD specification, licence register, failure
policy, requirements matrix, and milestone backlog.

## Set up and verify

```bash
uv sync --extra api --extra desktop --group dev --inexact
.venv/bin/python -m pytest -q
.venv/bin/ruff check src tests tools
.venv/bin/pyright --pythonpath .venv/bin/python

cd web
npm install
npm run test
npm run lint
npm run build
```

## Open the native development preview

After the setup above, on macOS:

```bash
.venv/bin/python tools/make_macos_launcher.py
```

Open `.bh/BH solver.app`. Building this local native
launcher requires Apple's installed developer tools. It references the checkout
and its environment; standalone distribution is a later gate.
The GUI entry point is `bh-workstation`. The [shell guide](docs/native/DW2_SHELL.md)
records data locations, shortcuts and the witnessed macOS draft workflow.
Qt remains optional: omit `--extra desktop` for kernel/browser work.

## Run the retained local PFD

Start the API from the repository root:

```bash
uv run bh-api
```

In a second terminal:

```bash
cd web
npm run dev
```

Open `http://127.0.0.1:4173`. Vite proxies `/api/v1alpha` to the local API at
`127.0.0.1:8000`. Runtime artifacts live under `.bh/runtime/` and are
excluded from version control.

Prototype CLI examples remain available:

```bash
uv run bh-sim solid-radiator
uv run bh-sim droplet-radiator
uv run bh-sim surge-buffer
```

## Current boundary

This slice supports acyclic, pure, single-phase steady flowsheets. Recycles,
mixtures, phase equilibrium, pressure-changing equipment, pinch/exergy studies,
dynamics, combat surges, HAZOP-style envelopes, and P&ID semantics remain governed
future milestones. See [docs/MILESTONES.md](docs/MILESTONES.md).
