import sys, tempfile, threading, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from bh_sim.adapters.worker_supervisor import WorkerSupervisor
from bh_sim.composition import create_services
from tests.test_dw4_command_integration import make_sample_draft
worker = Path('tests/fixtures/delayed_worker_entry.py').resolve()
for edge in ('before-registration', 'after-check-before-registration'):
 supervisor = WorkerSupervisor(worker_command=[sys.executable, str(worker), '3.0'], cancellation_grace_seconds=.15)
 supervisor.start()
 try:
  with tempfile.TemporaryDirectory() as td:
   services = create_services(Path(td), supervisor=supervisor)
   draft = make_sample_draft(edge)
   receipt = services.validate_draft(draft)
   entered, release = threading.Event(), threading.Event()
   original = supervisor.execute_job
   def delayed_admission(job, *, cancellation_requested=None):
    if edge == 'before-registration':
     entered.set()
     assert release.wait(5)
     return original(job, cancellation_requested=cancellation_requested)
    def callback():
     value = cancellation_requested()
     entered.set()
     assert release.wait(5)
     return value
    return original(job, cancellation_requested=callback)
   with patch.object(supervisor, 'execute_job', delayed_admission), ThreadPoolExecutor() as pool:
    future = pool.submit(services.start_run, draft, receipt.receipt_id)
    assert entered.wait(5)
    began = time.monotonic()
    cancel_future = pool.submit(services.cancel_run, '')
    assert services._active_cancel_event.wait(2)
    release.set()
    cancelled = cancel_future.result(timeout=2)
    assert cancelled.state == 'CANCELLED'
    try:
     future.result(timeout=2)
     raise AssertionError('unexpected publication')
    except Exception as error:
     assert getattr(error, 'code', '') == 'RUN_CANCELLED', repr(error)
    elapsed = time.monotonic() - began
    assert elapsed < 2.0
    assert services.last_valid_run(cancelled.case_id) is None
    assert supervisor._active_jobs == {} and supervisor._cancel_timers == {}
    print(edge, 'RUN_CANCELLED', 'elapsed', round(elapsed, 3), 'worker_alive', supervisor.is_alive())
 finally:
  supervisor.stop()
