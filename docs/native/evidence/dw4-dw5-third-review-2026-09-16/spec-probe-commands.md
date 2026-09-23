# Independent Spec review probes

Run from candidate root using its configured `.venv`:

```sh
PYTHONPATH=src:tests QT_QPA_PLATFORM=offscreen PYTHONDONTWRITEBYTECODE=1 .venv/bin/python ../evidence/bh_review_spec_cancel.py > ../evidence/spec-cancel.log 2>&1
PYTHONPATH=src QT_QPA_PLATFORM=offscreen PYTHONDONTWRITEBYTECODE=1 .venv/bin/python ../evidence/bh_review_spec_stale.py > ../evidence/spec-stale.log 2>&1
PYTHONPATH=src QT_QPA_PLATFORM=offscreen PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_dw5_acceptance.py
```

Both probe commands exited 0. Acceptance test command: 4 passed in 1.59s.

The cancellation probe queries `last_valid_run('case:cancel-test')`, using the canonical case prefix. Each scenario starts with an empty temporary repository and executes one cancelled run. Therefore `last_valid: true` establishes promotion of this cancelled run, not retention of an earlier result. In-process: COMPLETED response, CANCELLED persisted attempt, last-valid exists. Supervised: RUN_CANCELLED rejection after the delayed solve completes, CANCELLED unpersisted attempt, no last-valid result. The 300 ms observation is diagnostic, not an asserted specification deadline; the handoff instead requires a documented safe boundary and bounded escalation for noncooperative backends. The ordinary cancellation path has no escalation timer.

The stale-display probe retains the same selected run after changing heater duty from 75,000 W to 125,000 W and saving. Save clears the stale text although no new run occurred. The workbook dock is not raised, hence `visible: false` in both records; this does not affect the observed stale-label text removal.

The slow worker uses the real worker loop and engineering adapter with an injected two-second execution delay. Its generated runtime artifact is ignored candidate runtime data. Probe source and output are review evidence; tracked candidate source was not edited.
