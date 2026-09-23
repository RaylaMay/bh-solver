"""Real worker with an artificial blocking delay for cancellation fault injection."""

import sys
import time

from bh_sim.boundary.contracts import CalculatedRunDto, PreparedRevisionDto
from bh_sim.worker.entry import create_default_adapter, run_worker_loop


def delayed_adapter() -> object:
    adapter = create_default_adapter()
    calculate = adapter.run

    def run(
        prepared: PreparedRevisionDto,
        *,
        run_id: str | None = None,
        expected_context_hash: str | None = None,
    ) -> CalculatedRunDto:
        time.sleep(float(sys.argv[1]))
        return calculate(prepared, run_id=run_id, expected_context_hash=expected_context_hash)

    adapter.run = run
    return adapter


if __name__ == "__main__":
    run_worker_loop(sys.stdin.buffer, sys.stdout.buffer, delayed_adapter)
