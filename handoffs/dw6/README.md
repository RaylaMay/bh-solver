# DW6 reviewer-controlled acceptance package

This package is the executable contract for the receiving developer. It is
intentionally separate from the ordinary repository test directory: the pre-DW6
application must fail its missing-capability tests. The frozen specification and
handoff are in `spec/`; their repository originals remain the editable authority.
This snapshot is identified by an external manifest digest, not by a candidate's
claim that its tests passed.

## Run against a candidate

Use Python 3.13 with the repository's locked development, desktop and API extras.
Pytest, HTTPX and PySide6 are required; missing native support is a failure, not a
skip. Run from an external reviewer copy when evaluating incoming implementation.

```sh
/path/to/review-python run.py --candidate /path/to/candidate \
  --output /path/to/new-evidence-directory \
  --manifest-sha256 REVIEWER_SUPPLIED_DIGEST
```

The digest comes from the separately delivered preparation record. Do not obtain
the trust anchor from a modified candidate. The runner refuses an altered manifest,
changed or additional package files, missing tests, skips, xfails, incomplete
outcomes and changed candidate source. It ignores candidate pytest configuration,
conftest files, `PYTEST_ADDOPTS` and autoloaded plugins. Exit 0 means the mandatory
software suite passed; exit 1 means failed acceptance; exit 2 is an integrity error.
It writes `gate.json`, complete `pytest.json`, `pytest.log` and `candidate.json`.
The existing source manifest covers executable inputs including untracked files.

The factory and command contract is in `spec/DW6_ACCEPTANCE_SPEC.md`. No application,
solver, result repository or scenario-report mock can satisfy this package. Test
replacements are only provider HTTP, time and the OS credential store; fault
injection targets OS persistence and real worker processes. Synthetic text and
provider responses are test inputs. Every run value must come from the worker.

## Reference fixture and oracle provenance

`fixtures/source.json` is source→heater→sink with 1 kg/s at 300 K and a 500 kW
heater. The existing reference property adapter explicitly uses constant
1000 J/(kg K) heat capacity. For the proposed 600 kW trial the independent hand
expectation is 900 K: 300 + 600000/(1×1000). This is software verification with
`BLOCKED_EVIDENCE / TEST FIXTURE ONLY` data, not scientific validation or a new model.
`legacy-*.json` are exact copies of the existing DW1 canonical fixtures.

The two tiny PDFs are purpose-built syntax fixtures: one has selectable text and
one has an image-only page. They contain no third-party paper or user content.

## Test groups

- `test_authority_context.py`: proposal approval/edit/rejection, stale targets,
  profile labels, context identity/disclosure, injection and documents.
- `test_provider.py`: actual adapter request serialization, zero retries,
  provider errors, unknown usage, model identity and credentials.
- `test_exploration.py`: fixed bounds, all ceilings, real worker artifacts,
  source/result isolation, cancellation, stale source and adoption.
- `test_audit_native.py`: durable audit, failed writes/corruption, legacy bytes,
  immutable contracts, ordinary launcher and native keyboard/event-loop paths.

Every collected test is mandatory. The manifest contains exact node IDs including
parameterized cases. Full repository checks and the native/live-provider witness
remain additional requirements; this package is not the complete release gate.

## Verify the verifier

```sh
/path/to/review-python selftest.py --candidate /path/to/candidate
```

These tests challenge authority/isolation/budget/artifact assertions with deliberately
damaged observations and exercise real pytest skip/xfail/configuration attacks.
They verify the harness, not a DW6 implementation. The pre-DW6 run cannot demonstrate
the downstream integration assertions until the required product capabilities exist.
The runner is not a security sandbox for deliberately malicious Python code.

## Controlled amendments

`freeze.py` is a reviewer authoring utility, not a developer acceptance step.
An amendment requires the owner/reviewer's reason and disposition, changed tests
and specification, a new revision, exact collection and sensitivity checks, and
a new externally distributed digest. Old package/evidence bytes remain immutable.
Never regenerate the manifest merely to make an incoming candidate acceptable.

Run the existing project checks separately: full pytest, Ruff check/format --check,
Pyright, project-link/baseline checker, diff check, package build, and web
test/lint/build. Record versions and actual results. Do not silently install or
contact a live provider from this runner. The manual provider check is explicitly
initiated by the reviewer with synthetic data and their own configured credentials.
