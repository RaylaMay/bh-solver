import sys,time
from bh_sim.worker.entry import create_default_adapter,run_worker_loop

def factory():
    adapter=create_default_adapter()
    original=adapter.run
    def slow(*a,**kw):
        time.sleep(2)
        return original(*a,**kw)
    adapter.run=slow
    return adapter
run_worker_loop(sys.stdin.buffer,sys.stdout.buffer,factory)
