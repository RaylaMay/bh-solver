"""Thin retained FastAPI v1alpha adapter over neutral application services.

The legacy Run path intentionally preserves its prior-validation-free HTTP
semantics. New command admission uses draft.validate/run.start separately.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import uvicorn
from fastapi import FastAPI, HTTPException

from bh_sim.adapters.browser_format import from_browser, to_browser
from bh_sim.application.services import ApplicationServices
from bh_sim.boundary.contracts import RunExecutionDto, ValidationDto
from bh_sim.composition import create_services

from .schemas import (
    ApiEnvelope,
    DiagnosticDto,
    MetricDto,
    NodeResultDto,
    PfdDraftDto,
    RunResultDto,
    ValidationResultDto,
)


def _format_quantity(value: float, unit: str) -> str:
    return f"{value:.6g} {unit}" if unit != "1" else f"{value:.6g}"


def _validation_response(validation: ValidationDto) -> ApiEnvelope:
    result = ValidationResultDto(
        valid=validation.valid,
        degrees_of_freedom=validation.degrees_of_freedom,
        diagnostics=[
            DiagnosticDto(
                code=item.code,
                severity=item.severity,
                message=item.message,
                subject_id=item.subject_id,
            )
            for item in validation.diagnostics
        ],
    )
    return ApiEnvelope(data=result.model_dump(mode="json", by_alias=True))


def _run_response(execution: RunExecutionDto) -> ApiEnvelope:
    result = execution.result
    evaluations = {item.unit_id: item for item in result.unit_results}
    node_ids = dict(execution.prepared.node_ids)
    edge_ids = dict(execution.prepared.edge_ids)
    equipment = {node.object_id: node for node in execution.draft.equipment}
    node_results = []
    for unit_id, node_id in execution.prepared.node_ids:
        evaluation = evaluations.get(unit_id)
        if evaluation is None:
            node_results.append(
                NodeResultDto(node_id=node_id, status="failed", validity="INVALID", metrics=[])
            )
            continue
        status: Literal["valid", "warning", "invalid"] = "valid"
        if evaluation.validity == "EXTRAPOLATED":
            status = "warning"
        elif evaluation.validity == "INVALID":
            status = "invalid"
        elif equipment[node_id].model_id in {"source", "radiator"}:
            status = "warning"
        node_results.append(
            NodeResultDto(
                node_id=node_id,
                status=status,
                validity=evaluation.validity,
                metrics=[
                    MetricDto(
                        label=metric.name.replace("_", " ").title(),
                        display_value=_format_quantity(metric.quantity.value, metric.quantity.unit),
                    )
                    for metric in evaluation.metrics
                ],
            )
        )
    diagnostics = [
        DiagnosticDto(
            severity=item.severity,
            code=item.code,
            message=item.message,
            subject_id=(node_ids.get(item.subject_id) or edge_ids.get(item.subject_id))
            if item.subject_id is not None
            else None,
        )
        for item in result.diagnostics
    ]
    response = RunResultDto(
        run_id=result.run_id,
        draft_id=execution.draft.draft_id,
        revision=execution.draft.revision,
        converged=result.convergence == "CONVERGED",
        conservation_closed=result.closure == "PASSED",
        diagnostics=diagnostics,
        node_results=node_results,
        completed_at=datetime.fromisoformat(result.completed_at),
    )
    return ApiEnvelope(data=response.model_dump(mode="json", by_alias=True))


def create_app(
    data_root: str | Path | None = None,
    *,
    services: ApplicationServices | None = None,
) -> FastAPI:
    """Construct HTTP routing; injectable services support kernel-free adapter tests."""
    application = services if services is not None else create_services(data_root)
    app = FastAPI(title="BH Process Studio API", version="v1alpha")

    @app.get("/api/v1alpha/health")
    def health() -> ApiEnvelope:
        return ApiEnvelope(data={"status": "ok"})

    @app.put("/api/v1alpha/drafts/{draft_id}")
    def save_draft(draft_id: str, draft: PfdDraftDto) -> ApiEnvelope:
        if draft_id != draft.draft_id:
            raise HTTPException(400, "path and body draft IDs differ")
        saved = to_browser(application.save_draft(from_browser(draft)))
        return ApiEnvelope(data=saved.model_dump(mode="json", by_alias=True))

    @app.get("/api/v1alpha/drafts/{draft_id}")
    def load_draft(draft_id: str) -> ApiEnvelope:
        try:
            draft = to_browser(application.open_draft(draft_id))
        except KeyError as error:
            raise HTTPException(404, "draft not found") from error
        return ApiEnvelope(data=draft.model_dump(mode="json", by_alias=True))

    @app.post("/api/v1alpha/drafts/{draft_id}/validate")
    def validate_draft(draft_id: str, draft: PfdDraftDto) -> ApiEnvelope:
        if draft_id != draft.draft_id:
            raise HTTPException(400, "path and body draft IDs differ")
        try:
            neutral = from_browser(draft)
        except (KeyError, TypeError, ValueError) as error:
            # Conversion now precedes the service call; retain the legacy
            # validation endpoint's diagnostic response for invalid quantities.
            result = ValidationResultDto(
                valid=False,
                degrees_of_freedom=0,
                diagnostics=[
                    DiagnosticDto(severity="error", code="INVALID_DRAFT", message=str(error))
                ],
            )
            return ApiEnvelope(data=result.model_dump(mode="json", by_alias=True))
        return _validation_response(application._legacy_validate(neutral))

    @app.post("/api/v1alpha/drafts/{draft_id}/runs")
    def run_draft(draft_id: str, draft: PfdDraftDto) -> ApiEnvelope:
        if draft_id != draft.draft_id:
            raise HTTPException(400, "path and body draft IDs differ")
        try:
            execution = application._legacy_run(from_browser(draft))
        except (KeyError, TypeError, ValueError) as error:
            raise HTTPException(422, str(error)) from error
        return _run_response(execution)

    return app


def main() -> None:
    """Retain the local API entry point and loopback-only listen address."""
    uvicorn.run("bh_sim.api.app:create_app", factory=True, host="127.0.0.1", port=8000)


def __getattr__(name: str) -> Any:
    """Retain the historical repository Python import without endpoint ownership."""
    if name != "DraftRepository":
        raise AttributeError(name)
    from bh_sim.adapters.storage import DraftRepository

    return DraftRepository
