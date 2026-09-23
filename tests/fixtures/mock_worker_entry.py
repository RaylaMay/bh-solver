"""Test mock worker entry point for subprocess tests."""

import sys

from bh_sim.boundary import contracts as c
from bh_sim.worker.entry import run_worker_loop


class DummyMockAdapter:
    """Mock calculation adapter for fast deterministic tests without external libraries."""

    def __init__(self) -> None:
        from bh_sim.adapters.engineering import InProcessEngineeringAdapter
        from bh_sim.adapters.reference import reference_property_package
        from bh_sim.engine import AcyclicRunEngine, PropertyRegistry, reference_model_catalog

        self.engine = AcyclicRunEngine(
            reference_model_catalog(), PropertyRegistry((reference_property_package(),))
        )
        self.adapter = InProcessEngineeringAdapter(self.engine, lambda e: "mock")
        self._ctx = self.adapter.context_hash()

    def context_hash(self) -> str:
        return self._ctx

    def prepare(self, draft: c.DraftDto) -> c.PreparedRevisionDto:
        if not draft.equipment:
            return c.PreparedRevisionDto(
                case_id=draft.draft_id,
                revision_id="1",
                case_json='{"case_id": "' + draft.draft_id + '"}',
                revision_json='{"revision_id": 1}',
                source_artifact_hash="mock_source_hash",
                engineering_hash="mock_engineering_hash",
                node_ids=(),
                edge_ids=(),
            )
        return self.adapter.prepare(draft)

    def validate(self, prepared: c.PreparedRevisionDto) -> c.ValidationDto:
        if prepared.engineering_hash == "mock_engineering_hash":
            return c.ValidationDto(valid=True, degrees_of_freedom=0, diagnostics=())
        return self.adapter.validate(prepared)

    def run(
        self,
        prepared: c.PreparedRevisionDto,
        *,
        run_id: str | None = None,
        expected_context_hash: str | None = None,
        **kwargs: object,
    ) -> object:
        if prepared.engineering_hash == "mock_engineering_hash":
            from collections import namedtuple

            RunResultMock = namedtuple(
                "RunResultMock",
                ["convergence", "closure", "physical_validity", "correlation_validity"],
            )
            StatusMock = namedtuple("StatusMock", ["value"])
            CalculatedMock = namedtuple("CalculatedMock", ["run_id", "result"])

            return CalculatedMock(
                run_id=run_id or "run-100",
                result=RunResultMock(
                    convergence=StatusMock("converged"),
                    closure=StatusMock("passed"),
                    physical_validity=StatusMock("valid"),
                    correlation_validity=StatusMock("valid"),
                ),
            )
        return self.adapter.run(
            prepared,
            run_id=run_id,
            expected_context_hash=expected_context_hash,
        )


if __name__ == "__main__":
    run_worker_loop(sys.stdin.buffer, sys.stdout.buffer, adapter_factory=DummyMockAdapter)
