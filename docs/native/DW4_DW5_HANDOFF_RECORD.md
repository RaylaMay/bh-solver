# DW4/DW5 handoff preparation — Appendix A record

Date: 2026-09-14. Project owner and document author: Rayla May.
Prepared with Codex. Status: **PROPOSED DEVELOPMENT PLAN; DOCUMENTATION DELIVERED**.

## Objective and instruction

Rayla May requested a senior-developer handoff for DW4/DW5, adding drag-and-drop PFD
elements and whole-process/individual-unit graphs in popup or side views. Rayla May
requested planning only in this work unit, with explicit documentation and further
handoff instructions.

References: ADR-001/004/005/009/010/011, DW4/DW5 in the native action plan,
PFD-001–005, CORE-001/008/009/010, UIX-ARCH-001/002, UIX-RUN-001/002,
UIX-HISTORY-001, UIX-PERF-001 and UIX-DOC-001.

## Scope, evidence and assumptions

The [handoff](DW4_DW5_DEVELOPER_HANDOFF.md) defines intake, editor follow-up, worker
contracts/supervision/recovery, native commands, workbooks, plot views and acceptance.
It preserves the kernel, Qt/raster canvas, history, browser compatibility and all
existing user-owned changes. HEAD at preparation was `a0d3281`; the working tree
contained substantial earlier implementation not represented by that commit alone.

Source inspection established that canvas movement and port gestures already exist,
palette placement by drag/drop does not, and native calculation ports remain
unavailable. The synchronous run path lacks the requested worker admission/lifecycle.
The current result projection lacks full stream/balance/series views. The last-valid
query permits extrapolated correlation results. Native subsystem identity requires
explicit binding to the older draft/run shape. The thermal-buffer prototype does
not provide a flowsheet trajectory. The handoff links the relevant source evidence.

## Selected design and tradeoffs

Extend existing gestures and history commands. Recommend a supervised worker with
reviewed typed IPC, durable admission and separate lifecycle records. Recommend one
graph model hosted in a dock or floating window. Keep authoritative data in immutable
artifacts and render bounded read views. Compare plot candidates only through licence,
boundary and measured workload review; Matplotlib QtAgg is the initial candidate,
not an adopted desktop dependency. Its documented Qt/PySide and static output
backends support evaluating it for this role. [Primary source](https://matplotlib.org/stable/users/explain/figure/backends.html)

Keep whole-process plots as explicitly selected traces, avoiding an undefined plant
temperature. Keep real time-history production behind a governed trajectory/model
contract and M7; a viewer can be tested with labelled fixtures first. Reusing the
scalar thermal-buffer prototype to fabricate a curve would cross that boundary.

Separate network collaboration, scientific dynamics and release work. Preserve
the existing behaviour for extrapolated results pending an explicit policy review.
Flag worker/UI lifetime as an architectural decision because process separation
alone does not establish survival after UI failure.

## Files and impact

- Added `DW4_DW5_DEVELOPER_HANDOFF.md` and this planning record.
- Added a discoverable link in `docs/README.md`.
- Changed no runtime source, contracts, dependency locks, tests, model equations,
  licence files, user cases, saved artifacts or existing evidence files.
- Froze no protocol and changed no requirement to VERIFIED. Later implementation
  must carry schema/migration, dependency, security/privacy and scientific reviews.

The README link intentionally makes its old DW3.2 manifest hash historical. Preserve
that manifest unchanged; do not regenerate it to claim the original check covered
this later documentation. Other DW3.2 manifest entries must still match.

## Verification

- `.venv/bin/python tools/check_project.py`: passed; 184 baseline Git objects,
  historical evidence bytes unchanged and 336 public file links resolved.
- `git diff --check`: passed.
- SHA-256 comparison against the preserved DW3.2 manifest: 42 entries matched;
  only `docs/README.md` differed, as expected from the new handoff link. Exact check:

```sh
.venv/bin/python - <<'PY'
import hashlib, json
from pathlib import Path
manifest = json.loads(Path('docs/native/evidence/dw3-2/manifest.json').read_text())
changed = [name for name, digest in manifest['files_sha256'].items()
           if hashlib.sha256(Path(name).read_bytes()).hexdigest() != digest]
assert changed == ['docs/README.md'], changed
print('PASS: 42 unchanged entries; expected README transition')
PY
```

Reviewed the handoff for source/gate distinctions, existing gesture reuse, physical
time versus iteration/runtime, separate result statuses, history preservation,
documentation obligations and next-developer acceptance. Python/web runtime tests,
native interaction and benchmarks were not rerun because this slice changes only
documentation; the plan labels prior DW3.2 results as inherited evidence.

## Risks, rollback and remaining work

The handoff cannot establish worker reliability, graph performance or scientific
validity. The receiving developer must inspect current source and rerun the relevant
baseline before implementation. Native VoiceOver, other-platform execution and
installer acceptance remain unverified gates inherited from DW3.2.

Rollback removes only the two new planning documents and their new README link;
it does not touch prior work or evidence. No commit, push, application/solver launch
or network editing occurs in this preparation. No decision is required to deliver this plan.
Section 9 of the handoff separates suggested defaults from later steward/owner
decisions, including time-domain scope, worker lifetime and extrapolated-result policy.
