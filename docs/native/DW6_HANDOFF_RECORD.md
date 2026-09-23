# DW6 test-first handoff preparation record

Date: 2026-09-16. Owner: Rayla May. Preparation and self-checks: Codex.
Status: **HANDOFF PACKAGE COMPLETE; DW6 IMPLEMENTATION NOT ACCEPTED**.

## Outcome and authority

Prepared the user-selected test-first developer handoff, executable acceptance
suite and reviewer-controlled portable package. ADR-012 records the narrow
approved exploration extension. The [handoff](DW6_DEVELOPER_HANDOFF.md) and
[acceptance specification](DW6_ACCEPTANCE_SPEC.md) define the receiving work.
This does not accept DW4/DW5, deliver the DW6 product or approve a scientific model.
The user authorized preparation; no independent human review is claimed.

## Source and preservation

The [intake inventory](evidence/dw6-handoff/intake.json) captures 307 public files,
including relevant uncommitted and untracked work, on main at
`a0d3281aee909914cdf82a6f35ef4550f0b29604`. Runtime data and private environment
files are excluded. HEAD alone does not reproduce this checkout.

The [source comparison](evidence/dw6-handoff/source-delta.json) finds exactly 11
existing files changed, all documentation: architecture, contracts, decisions,
dependencies, failure recovery, milestones, native action plan, PFD specification,
document index, requirements matrix and vocabulary. No intake files were removed.
Production source, ordinary tests, tools, browser code, existing evidence and local
CI configuration retain their intake bytes. Earlier user work remains uncommitted.

New files are the three DW6 native documents, `handoffs/dw6/`, the portable archive
and checksum, and this work's evidence directory. The baseline executable inventory
includes untracked files and existing build metadata; its SHA-256 is
`0cffe3ff6ed2821c6e30374c0c4813a0b1a37d68d349e20c5505c4c44f6ecff4`.
This inventory identifies bytes; it is not a complete source checkout archive.

## Frozen delivery

Use the [portable archive](../../handoffs/dw6-acceptance-v1.zip),
[checksum receipt](../../handoffs/dw6-acceptance-v1.sha256) and
[package instructions](../../handoffs/dw6/README.md).
Revision 1 contains 97 mandatory test identities and a manifest of every package
file, including fixtures and frozen specification copies. Repository-relative
links in the copies are rendered as source references; their original hashes and
transformation are recorded in `spec/provenance.json`.

**Reviewer trust anchor — manifest SHA-256:**

```text
c9eb72f084c00f4b820d7294b68f80ebdc0721f402ea9cfb5c65483f7ccca91a
```

Copy this digest from the reviewer-controlled record. Do not obtain it from a
modified candidate. Extract the archive outside the candidate checkout, then run:

```sh
/path/to/review-python /path/to/extracted/dw6/run.py \
  --candidate /path/to/candidate \
  --output /path/to/new-evidence-directory \
  --manifest-sha256 c9eb72f084c00f4b820d7294b68f80ebdc0721f402ea9cfb5c65483f7ccca91a
```

Tests/fixtures may be amended only with Rayla May or the designated reviewer's
agreement, an attributable reason and a new revision/digest. Preparation snapshots
were not released or approved as the receiving contract; they remain retained
alongside their original logs. Do not regenerate a manifest to bless failed code.

## Verification performed here

See [command and method record](evidence/dw6-handoff/verification.json),
[environment versions](evidence/dw6-handoff/versions.json),
[release gate](evidence/dw6-handoff/release-r1/gate.json), and
[complete release output](evidence/dw6-handoff/release-r1/pytest.log).
The final package was executed from a separate temporary reviewer copy against
this checkout; candidate source and package hashes remained unchanged.

| Check | Observed result |
|---|---|
| Frozen acceptance collection | 97 tests; zero collection errors |
| Pre-DW6 acceptance run | 3 legacy checks passed; 94 expected missing-capability failures; zero skips/xfails; exit 1 |
| Verifier challenges | 9 passed: authority, isolation, budget, artifact/chain, nonfinite values, missing/skip/xfail outcomes, manifest tampering and pytest-config isolation |
| Existing Python suite | 173 passed; one upstream Starlette deprecation warning |
| Existing browser suite | 5 passed |
| Ruff lint and formatting | Passed for source, tests, tools and package |
| Pyright | Project and portable package both passed |
| Project integrity/links and diff whitespace | Passed; final counts in linked logs |
| Browser lint/build | Passed |
| Python distribution build | Source distribution and wheel from that distribution built offline with setuptools 84.0.0 in a temporary source copy |
| Synthetic PDFs | Strict local parse: one text page with expected text; one image-only page with no extracted text |

The 94 initial failures comprise 88 missing `DraftDto.profile/execution_scope`,
three missing production-factory paths (including both crash points), and three
missing AI contracts. Exact identities and observations are in
[initial outcomes](evidence/dw6-handoff/expected-initial-outcomes.json).
These are failures for product acceptance, not expected-failure markers in pytest.
A future implementation must pass every test, including the positive native and
real-worker workflows.

Initial style/type and harness-path errors were corrected without changing
production code. Two build entrypoints failed for local tooling reasons; the
installed setuptools backend then built both distributions offline. Full details,
including the earlier red runs and diagnostic correction, remain in
[authoring QA](evidence/dw6-handoff/initial-qa.md). Logs with machine paths were
sanitized by replacing path prefixes, documented in the evidence directory.

## Engineering impacts and limits

No production dependency, scientific equation, artifact schema implementation or
runtime policy changed. The specification defines additive versioned AI contracts,
profile/scope persistence, local extraction and credential ports; the developer
must implement and review compatibility. Existing scientific artifact fixtures
remain byte-for-byte compatible. Synthetic data and a synthetic API key are used;
no live provider call or user case transmission occurred.

The tests exercise public commands and the ordinary production composition;
provider HTTP, time and credential boundaries are controlled. Scientific results
must come from the real supervised worker. The suite rejects skipped/missing tests
and candidate pytest configuration; it is not an OS sandbox for malicious Python.
Verifier mutation checks damage observations; they are not an independent mutation
review of a working DW6 implementation. Deeper assertions cannot execute past the
current missing capabilities. Record this limit when interpreting the red baseline.

DW4/DW5 have not been accepted in this checkout. Their accepted worker/artifact
boundary is required before a DW6 green integration claim. macOS native/assistive
technology witness, explicitly initiated synthetic live-provider check, independent
implementation review and remote branch-protection verification were not performed.
The locally prepared CI file is not proof of an enforced remote gate.

## Recovery and receiving work

The first bounded task is to reconcile the exact candidate source and accepted
DW4/DW5 contracts, then implement the frozen neutral contracts and production
factory. Report conflicts to the reviewer; preserve the suite and earlier evidence.
Proceed through the handoff increments and require the unmodified suite, existing
checks, real-worker/native integration, witness and review before main acceptance.
Update the existing requirements and continuity records with actual outcomes.

To withdraw this preparation, remove only the new DW6 artifacts and its appended
documentation sections; preserve the pre-existing dirty tree and historical evidence.
For a later product rollback, disable AI capabilities while retaining audit and
exploration artifacts. Recovery must not replay provider requests or solver runs.
No commit, push, merge or message to another person was performed.
