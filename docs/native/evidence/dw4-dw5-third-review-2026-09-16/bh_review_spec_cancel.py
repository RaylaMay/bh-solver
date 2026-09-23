import sys,tempfile,time,threading,json
from pathlib import Path
from bh_sim.adapters.desktop_preview import create_supervised_gateway
from bh_sim.adapters.worker_supervisor import WorkerSupervisor
from bh_sim.boundary import contracts as c
from test_dw4_command_integration import make_sample_draft

def call(g,n,p):return g.dispatch(c.CommandRequest(n,str(time.time_ns()),'review',p))
for supervised in (False,True):
    with tempfile.TemporaryDirectory() as temp:
        sup=WorkerSupervisor([sys.executable,str(Path(__file__).with_name('bh_review_spec_slow_worker.py'))]) if supervised else None
        try:
            if sup:sup.start()
            g=create_supervised_gateway(Path(temp),supervisor=sup)
            if not sup:
                original=g.services.engineering.run
                def slow(*a,**kw):time.sleep(2);return original(*a,**kw)
                g.services.engineering.run=slow
            d=make_sample_draft('cancel-test')
            v=call(g,'draft.validate',c.DraftParameters(d));out=[]
            t=threading.Thread(target=lambda:out.append(call(g,'run.start',c.StartRunParameters(d,v.data.receipt_id))))
            t.start()
            deadline=time.monotonic()+5
            while not g.services._active_run_id and time.monotonic()<deadline:time.sleep(.01)
            time.sleep(.15)
            before=time.monotonic();cancel=call(g,'run.cancel',c.CancelRunParameters('run:in-flight','probe'))
            cancel_latency=time.monotonic()-before
            t.join(.3);still_running=t.is_alive();t.join(5)
            print(json.dumps({'supervised':supervised,'cancel_latency':cancel_latency,'still_running_after_300ms':still_running,'run_return_after_cancel_seconds':time.monotonic()-before,'run_outcome':out[0].disposition,'diagnostics':[x.code for x in out[0].diagnostics],'attempts':[(x.state,x.persisted) for x in g.services.list_attempts()],'last_valid':g.services.last_valid_run('case:cancel-test') is not None}),flush=True)
        finally:
            if sup:sup.stop()
