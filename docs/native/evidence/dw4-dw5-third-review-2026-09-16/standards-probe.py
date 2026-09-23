from pathlib import Path
from tempfile import TemporaryDirectory
from dataclasses import replace
from unittest.mock import patch
from bh_sim.persistence import PersistenceStore
from bh_sim.boundary import contracts as c
from bh_sim.boundary.json_codec import boundary_from_json
from bh_sim.composition import create_services
from bh_sim.application.services import CommandRejected
from test_dw4_command_integration import make_sample_draft

with TemporaryDirectory() as td:
    p=Path(td); s=PersistenceStore(p)
    a=c.RunAttemptRecord(attempt_id='att:probe', run_id='run:probe', case_id='case:probe', engineering_hash='e', context_hash='c', state='RUNNING', admitted_at='2026-09-16T00:00:00Z')
    s.record_attempt(a)
    completed=replace(a,state='COMPLETED',persisted=True,artifact_hash='a'*64,terminal_at='2026-09-16T00:00:01Z')
    with patch.object(s,'_write_attempt_manifest',side_effect=OSError('disk full')):
        try: s.record_attempt(completed)
        except OSError: pass
    s.record_attempt(completed)
    print('MANIFEST_WRITE_RETRY', 'index='+s.get_attempt(a.attempt_id).state, 'manifest='+boundary_from_json((s.attempts_dir/'att:probe.json').read_text()).state)
    (p/'index.sqlite3').unlink()
    s=PersistenceStore(p);s.rebuild_index_from_artifacts()
    print('MANIFEST_REBUILD',s.get_attempt(a.attempt_id).state)

with TemporaryDirectory() as td:
    s=create_services(td);d=make_sample_draft('RejectedAttempt');r=s.validate_draft(d)
    with patch.object(s.engineering,'run',side_effect=CommandRejected('CONTEXT_CHANGED','context changed')):
        try: s.start_run(d,r.receipt_id)
        except CommandRejected: pass
    print('REJECTED_EXECUTION',s.list_attempts()[0].state,s.list_attempts()[0].terminal_at)

class DeadSupervisor:
    def is_alive(self): return False
with TemporaryDirectory() as td:
    s=create_services(td,supervisor=DeadSupervisor());d=make_sample_draft('DeadWorker');r=s.validate_draft(d)
    result=s.start_run(d,r.receipt_id)
    print('DEAD_WORKER',result.convergence, s.list_attempts()[0].state)

with TemporaryDirectory() as td:
    s=create_services(td);d=make_sample_draft('FailedRunSave');r=s.validate_draft(d)
    with patch.object(s.artifacts,'save_run',side_effect=OSError('disk full')):
        try:s.start_run(d,r.receipt_id)
        except OSError:pass
    a=s.list_attempts()[0]
    print('RUN_SAVE_FAILURE', a.state, a.terminal_at, a.failure_reason, a.persisted)
