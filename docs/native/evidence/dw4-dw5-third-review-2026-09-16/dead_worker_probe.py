"""Review probe: a receipt from a stopped worker must not authorize local execution."""
import json
import tempfile
from pathlib import Path
from bh_sim.adapters.worker_supervisor import WorkerSupervisor
from bh_sim.adapters.desktop_preview import create_supervised_gateway
from bh_sim.boundary import contracts as c
from test_dw4_command_integration import make_sample_draft
with tempfile.TemporaryDirectory() as data:
    supervisor=WorkerSupervisor()
    supervisor.start()
    try:
        gateway=create_supervised_gateway(Path(data),supervisor=supervisor)
        draft=make_sample_draft('DeadWorkerReview')
        receipt=gateway.dispatch(c.CommandRequest('draft.validate','v1','reviewer',c.DraftParameters(draft))).data
        assert isinstance(receipt,c.ValidationReceiptDto)
        old_session=receipt.worker_session_id
        supervisor.stop()
        calls=[]
        original=gateway.services.engineering.run
        def local_run(*args,**kwargs):
            calls.append('in-process engine called')
            return original(*args,**kwargs)
        gateway.services.engineering.run=local_run
        outcome=gateway.dispatch(c.CommandRequest('run.start','r1','reviewer',c.StartRunParameters(draft,receipt.receipt_id)))
        print(json.dumps({'receipt_had_worker_session':bool(old_session),'worker_alive':supervisor.is_alive(),'disposition':outcome.disposition,'diagnostics':[d.code for d in outcome.diagnostics],'local_engine_calls':calls,'attempts':[{'state':a.state,'persisted':a.persisted} for a in gateway.services.list_attempts()]},indent=2))
    finally:
        supervisor.stop()
