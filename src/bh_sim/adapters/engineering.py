"""In-process DW1 engineering port; the supervised worker replaces it at DW4.

Only this adapter reconstructs domain objects and calls the existing engine. The
hash projection omits case title and unit display names, preserving all remaining
canonical fields, array order and literal quantity value/unit representations.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Literal, cast

from bh_sim.boundary.contracts import (
    ENGINEERING_HASH_SCHEME,
    ArtifactReferenceDto,
    CalculatedRunDto,
    DiagnosticDto,
    DraftDto,
    MetricDto,
    PreparedRevisionDto,
    QuantityDto,
    RunViewDto,
    UnitResultDto,
    ValidationDto,
)
from bh_sim.core import DraftRevision, RunResult
from bh_sim.core.json_codec import canonical_json, contract_digest, contract_from_json
from bh_sim.engine import AcyclicRunEngine

from .reference import diagnostic_to_dto, draft_to_contract

_Validity = Literal["VALID", "EXTRAPOLATED", "INVALID", "UNKNOWN"]


def read_prepared_revision(prepared: PreparedRevisionDto) -> DraftRevision:
    """Validate canonical input identities before an adapter persists or evaluates."""

    revision = contract_from_json(prepared.revision_json)
    if not isinstance(revision, DraftRevision):
        raise TypeError("prepared input is not a DraftRevision")
    if (
        str(revision.revision_id) != prepared.revision_id
        or str(revision.case.case_id) != prepared.case_id
        or canonical_json(revision.case) != prepared.case_json
        or contract_digest(revision.case) != prepared.source_artifact_hash
    ):
        raise ValueError("prepared revision identity mismatch")
    return revision


def run_to_view(result: RunResult) -> RunViewDto:
    """Expose returned quantities and four statuses without changing artifact bytes."""

    diagnostics = tuple(
        DiagnosticDto(
            item.code.upper().replace("-", "_"),
            item.message,
            cast(Literal["info", "warning", "error"], item.severity),
            str(item.subject_id) if item.subject_id is not None else None,
        )
        for item in result.diagnostics
    )
    diagnostics += (
        DiagnosticDto(
            "REFERENCE_FIXTURE_ONLY",
            "The reference liquid and radiator are BLOCKED_EVIDENCE test fixtures; "
            "VALID means inside the fixture domain, not scientifically approved.",
            "warning",
        ),
    )
    return RunViewDto(
        str(result.run_id),
        str(result.case_id),
        str(result.revision_id) if result.revision_id else None,
        result.created_at,
        cast(Literal["NOT_RUN", "CONVERGED", "FAILED"], result.convergence.name),
        cast(Literal["NOT_CHECKED", "PASSED", "FAILED"], result.closure.name),
        cast(_Validity, result.physical_validity.name),
        cast(_Validity, result.correlation_validity.name),
        tuple(
            UnitResultDto(
                str(unit.unit_id),
                cast(_Validity, unit.validity.name),
                tuple(
                    MetricDto(name, QuantityDto(value.value, value.unit))
                    for name, value in unit.metrics
                ),
            )
            for unit in result.unit_evaluations
        ),
        diagnostics,
        ArtifactReferenceDto("RunResult", str(result.run_id), contract_digest(result)),
    )


class InProcessEngineeringAdapter:
    """Existing acyclic fixture engine behind a synchronous, versioned-value port.

    context_metadata must describe the actual selected catalogue, property data and
    configuration. Source files are required in DW1; missing or changed loaded source
    fails explicitly. Packaged source manifests are a DW9 contract task.
    """

    def __init__(
        self,
        engine: AcyclicRunEngine,
        context_metadata: Callable[[AcyclicRunEngine], str],
    ) -> None:
        self.engine = engine
        self._context_metadata = context_metadata
        self._source_digest = self._read_source_digest()

    @staticmethod
    def _read_source_digest() -> str:
        package = Path(__file__).parents[1]
        required = (
            "core/contracts.py",
            "core/json_codec.py",
            "core/quantity.py",
            "engine/compiler.py",
            "engine/runner.py",
            "engine/models.py",
            "engine/properties.py",
            "solvers/scipy_solver.py",
        )
        if not all((package / name).is_file() for name in required):
            raise RuntimeError("engineering source manifest is unavailable")
        paths = [
            path
            for folder in ("core", "engine", "solvers")
            for path in (package / folder).rglob("*.py")
        ]
        paths += [Path(__file__), Path(__file__).with_name("reference.py")]
        if not paths:
            raise RuntimeError("engineering source manifest is unavailable")
        records = [
            (path.relative_to(package).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest())
            for path in sorted(paths)
        ]
        return hashlib.sha256(json.dumps(records, separators=(",", ":")).encode()).hexdigest()

    def context_hash(self) -> str:
        """Fingerprint loaded code and current concrete execution configuration."""

        if self._read_source_digest() != self._source_digest:
            raise RuntimeError("engineering source changed; restart before validating")
        return self._hash_engine(self.engine)

    def _hash_engine(self, engine: AcyclicRunEngine) -> str:
        return hashlib.sha256(
            (self._source_digest + "\n" + self._context_metadata(engine)).encode()
        ).hexdigest()

    def prepare(self, draft: DraftDto) -> PreparedRevisionDto:
        """Construct unchanged domain artifacts plus a separately named input hash."""

        adapted = draft_to_contract(draft)
        case_json = canonical_json(adapted.revision.case)
        projection = json.loads(case_json)
        del projection["title"]
        for unit in projection["units"]:
            del unit["name"]
        encoded = json.dumps(
            {"scheme": ENGINEERING_HASH_SCHEME, "case": projection},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        return PreparedRevisionDto(
            str(adapted.revision.case.case_id),
            str(adapted.revision.revision_id),
            case_json,
            canonical_json(adapted.revision),
            contract_digest(adapted.revision.case),
            hashlib.sha256(encoded.encode()).hexdigest(),
            tuple((str(key), value) for key, value in adapted.node_ids.items()),
            tuple((str(key), value) for key, value in adapted.edge_ids.items()),
        )

    def validate(self, prepared: PreparedRevisionDto) -> ValidationDto:
        """Compile exactly the supplied immutable revision without saving or Run."""

        revision = read_prepared_revision(prepared)
        report = self.engine.validate(revision.case, revision_id=revision.revision_id)
        # Legacy diagnostics name UI subjects; the mappings are opaque IDs, not UI objects.
        from bh_sim.core import StableId

        return ValidationDto(
            report.valid,
            report.degrees_of_freedom,
            tuple(
                diagnostic_to_dto(
                    item,
                    {StableId(key): value for key, value in prepared.node_ids},
                    {StableId(key): value for key, value in prepared.edge_ids},
                )
                for item in report.diagnostics
            ),
        )

    def run(
        self,
        prepared: PreparedRevisionDto,
        *,
        expected_context_hash: str | None = None,
    ) -> CalculatedRunDto:
        """Execute existing equations; repository acknowledgment is a separate step."""

        revision = read_prepared_revision(prepared)
        engine = self.engine
        if expected_context_hash is not None:
            self.context_hash()  # Also enforce the loaded-source manifest.
            engine = deepcopy(self.engine)
            if self._hash_engine(engine) != expected_context_hash:
                raise ValueError("execution context changed before snapshot")
        result = engine.run(revision.case, revision_id=revision.revision_id)
        return CalculatedRunDto(canonical_json(result), run_to_view(result))
