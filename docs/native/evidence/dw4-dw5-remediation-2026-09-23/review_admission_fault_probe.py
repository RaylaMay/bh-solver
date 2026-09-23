"""Independent Standards probe: no product store or implementation modifications."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from bh_sim.composition import create_services
from tests.test_dw4_command_integration import make_sample_draft

with TemporaryDirectory() as temporary:
    services = create_services(Path(temporary))
    draft = make_sample_draft('admission-fault')
    receipt = services.validate_draft(draft)
    with patch.object(services.artifacts, 'record_attempt', side_effect=OSError('disk full')):
        try:
            services.start_run(draft, receipt.receipt_id)
        except Exception as error:
            print('Raised:', type(error).__name__, str(error))
    (attempt,) = services.list_attempts()
    print('Retained state:', attempt.state)
    print('Terminal timestamp:', attempt.terminal_at)
    print('Failure reason:', attempt.failure_reason)
    print('Active run:', services._active_run_id)
    assert attempt.state == 'ADMITTED' and attempt.terminal_at is None
    assert attempt.failure_reason is None and services._active_run_id is None
