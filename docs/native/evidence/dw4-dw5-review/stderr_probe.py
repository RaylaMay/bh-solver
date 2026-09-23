import sys,time
from pathlib import Path
from bh_sim.adapters.worker_supervisor import WorkerSupervisor
worker=Path(__file__).with_name('stderr_worker.py')
s=WorkerSupervisor(worker_command=[sys.executable,str(worker)])
start=time.monotonic()
try:
    s.start(timeout=1.0)
    print('STDERR_FLOOD handshake completed')
except Exception as error:
    print('STDERR_FLOOD',type(error).__name__,str(error),'elapsed_s',round(time.monotonic()-start,2))
finally:
    s.stop()
