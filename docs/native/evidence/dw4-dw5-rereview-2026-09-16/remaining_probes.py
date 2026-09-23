import json,tempfile,time
from pathlib import Path
from dataclasses import replace
from bh_sim.boundary import contracts as c
from bh_sim.boundary.json_codec import boundary_from_json
from bh_sim.persistence.store import PersistenceStore
from bh_sim.adapters.desktop_preview import create_supervised_gateway
from bh_sim.adapters.worker_supervisor import WorkerSupervisor
from test_dw4_command_integration import make_sample_draft

def call(g,cmd,params):return g.dispatch(c.CommandRequest(cmd,str(time.time_ns()),'review',params))
with tempfile.TemporaryDirectory() as data:
    root=Path(data);s=PersistenceStore(root)
    a=c.RunAttemptRecord(attempt_id='att:probe',run_id='run:probe',case_id='case:probe',engineering_hash='engineering',context_hash='context',state='COMPLETED',admitted_at='2026-09-16T00:00:00Z',terminal_at='2026-09-16T00:00:01Z',persisted=True)
    s.record_attempt(a);s.record_attempt(replace(a,state='FAILED',failure_reason='late event'))
    indexed=s.get_attempt(a.attempt_id).state
    manifest=boundary_from_json((s.attempts_dir/'att:probe.json').read_text()).state
    (root/'index.sqlite3').unlink()
    s2=PersistenceStore(root);s2.rebuild_index_from_artifacts()
    print('TERMINAL_REBUILD',json.dumps({'indexed_before_rebuild':indexed,'manifest':manifest,'indexed_after_rebuild':s2.get_attempt(a.attempt_id).state}))

class EmptyCompletion:
    def is_alive(self):return True
    def validate(self,draft,engineering_hash,context_hash):return c.WorkerValidateResponse('probe',True,0,engineering_hash,context_hash,())
    def execute_job(self,job):return c.WorkerCompletedEvent(run_id=job.run_id,worker_session_id='probe',sequence=1,timestamp='2026-09-16T00:00:00Z',artifact_hash='0'*64,staged_path='',convergence='converged',closure='passed',physical_validity='valid',correlation_validity='valid',execution_duration_ms=1.0)
with tempfile.TemporaryDirectory() as data:
    g=create_supervised_gateway(Path(data),supervisor=EmptyCompletion());draft=make_sample_draft('EmptyStage')
    val=call(g,'draft.validate',c.DraftParameters(draft));out=call(g,'run.start',c.StartRunParameters(draft,val.data.receipt_id));a=g.services.list_attempts()[0]
    inspect=call(g,'run.inspect',c.InspectRunParameters(a.run_id))
    print('EMPTY_STAGE',json.dumps({'disposition':out.disposition,'attempt_state':a.state,'persisted':a.persisted,'inspect':inspect.disposition}))

with tempfile.TemporaryDirectory() as data:
    sup=WorkerSupervisor()
    try:
        sup.start();g=create_supervised_gateway(Path(data),supervisor=sup);draft=make_sample_draft('RestartReceipt')
        val=call(g,'draft.validate',c.DraftParameters(draft));before=sup.session_id;sup.stop();sup.start();after=sup.session_id
        out=call(g,'run.start',c.StartRunParameters(draft,val.data.receipt_id))
        print('WORKER_RESTART_RECEIPT',json.dumps({'worker_session_changed':before!=after,'old_receipt_run_disposition':out.disposition,'diagnostics':[d.message for d in out.diagnostics]}))
    finally:sup.stop()
