import sys, tempfile, threading, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from bh_sim.adapters.worker_supervisor import WorkerSupervisor
from bh_sim.composition import create_services
from tests.test_dw4_command_integration import make_sample_draft
worker = Path('tests/fixtures/delayed_worker_entry.py').resolve()
supervisor = WorkerSupervisor(worker_command=[sys.executable, str(worker), '2.0'], cancellation_grace_seconds=.15)
supervisor.start()
try:
  with tempfile.TemporaryDirectory() as td:
    services = create_services(Path(td), supervisor=supervisor)
    draft = make_sample_draft('admission-cancel')
    receipt = services.validate_draft(draft)
    enter, release = threading.Event(), threading.Event()
    original = supervisor.execute_job
    def delayed_admission(job):
      enter.set()
      assert release.wait(5)
      return original(job)
    with patch.object(supervisor, 'execute_job', delayed_admission), ThreadPoolExecutor() as pool:
      future = pool.submit(services.start_run, draft, receipt.receipt_id)
      assert enter.wait(5)
      print('before cancel:', services.list_attempts()[0].state, 'active jobs:', supervisor._active_jobs)
      cancelled = services.cancel_run('')
      print('cancel result:', cancelled.state, 'timers:', supervisor._cancel_timers)
      began = time.monotonic()
      release.set()
      time.sleep(.6)
      print('after .6s:', 'worker alive:', supervisor.is_alive(), 'future done:', future.done(), 'timers:', supervisor._cancel_timers)
      try: future.result(timeout=5)
      except Exception as error: print('final:', type(error).__name__, getattr(error, 'code', ''), 'elapsed:', round(time.monotonic()-began, 3))
finally:
  supervisor.stop()
