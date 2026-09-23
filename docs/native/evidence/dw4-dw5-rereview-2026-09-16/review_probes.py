from __future__ import annotations
import json, tempfile, time
from pathlib import Path
from dataclasses import replace
from bh_sim.adapters.desktop_preview import create_supervised_gateway
from bh_sim.adapters.worker_supervisor import WorkerSupervisor
from bh_sim.boundary import contracts as c
from test_dw4_command_integration import make_sample_draft

def call(g, command, params):
    return g.dispatch(c.CommandRequest(command, 'probe:'+command+str(time.time_ns()), 'review', params))

def summary(outcome):
    return {'disposition':outcome.disposition,'diagnostics':[(x.code,x.message) for x in outcome.diagnostics]}

with tempfile.TemporaryDirectory() as data:
    sup=WorkerSupervisor()
    try:
        sup.start(timeout=10)
        g=create_supervised_gateway(Path(data),supervisor=sup)
        draft=make_sample_draft('RealWorkerProbe')
        val=call(g,'draft.validate',c.DraftParameters(draft))
        print('REAL_WORKER_VALIDATE',json.dumps(summary(val)))
        if isinstance(val.data,c.ValidationReceiptDto):
            print('REAL_WORKER_VALID',val.data.validation.valid)
            result=call(g,'run.start',c.StartRunParameters(draft,val.data.receipt_id))
            print('REAL_WORKER_RUN',json.dumps(summary(result)))
    finally:
        sup.stop()

with tempfile.TemporaryDirectory() as data:
    g=create_supervised_gateway(Path(data))
    draft=make_sample_draft('ArtifactProbe')
    val=call(g,'draft.validate',c.DraftParameters(draft))
    result=call(g,'run.start',c.StartRunParameters(draft,val.data.receipt_id))
    attempt=g.services.list_attempts()[0]
    workbook=g.services.inspect_workbook(draft.draft_id,result.data.run_id)
    plot=g.services.get_plot_data(draft.draft_id,result.data.run_id,'T_Q','u:heat')
    print('PLOT_TEMPERATURES',json.dumps({'artifact_streams_K':[x.temperature_k for x in workbook.streams], 'plot_samples_K':[p.y for s in plot.series for p in s.points]}))
    print('ATTEMPT_IDENTITY',json.dumps({'attempt_run_id':attempt.run_id,'artifact_run_id':result.data.run_id,'lookup_by_attempt':summary(call(g,'run.inspect',c.InspectRunParameters(attempt.run_id)))}))

class CompletionWithoutArtifact:
    def is_alive(self): return True
    def validate(self,draft,engineering_hash,context_hash):
        return c.WorkerValidateResponse('probe',True,0,engineering_hash,context_hash,())
    def execute_job(self,job):
        return c.WorkerCompletedEvent(run_id=job.run_id,worker_session_id='probe',sequence=1,timestamp='2026-09-15T00:00:00Z',artifact_hash='0'*64,staged_path='/private/tmp/nonexistent-bh-review-result.json',convergence='converged',closure='passed',physical_validity='valid',correlation_validity='valid',execution_duration_ms=1.0)

with tempfile.TemporaryDirectory() as data:
    g=create_supervised_gateway(Path(data),supervisor=CompletionWithoutArtifact())
    draft=make_sample_draft('MissingArtifactProbe')
    val=call(g,'draft.validate',c.DraftParameters(draft))
    result=call(g,'run.start',c.StartRunParameters(draft,val.data.receipt_id))
    attempt=g.services.list_attempts()[0]
    inspect=call(g,'run.inspect',c.InspectRunParameters(attempt.run_id))
    print('MISSING_ARTIFACT',json.dumps({'run':summary(result),'attempt_state':attempt.state,'persisted':attempt.persisted,'inspect':summary(inspect)}))
