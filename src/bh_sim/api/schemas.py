"""Pydantic v1alpha schemas at the browser/API boundary."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


def _camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=_camel, populate_by_name=True, extra="forbid")


class QuantityDto(ApiModel):
    value: float
    unit: str


class ParameterValueDto(ApiModel):
    label: str
    quantity: QuantityDto
    description: str | None = None


EquipmentKind = Literal[
    "source",
    "sink",
    "heater",
    "mixer",
    "splitter",
    "heat-exchanger",
    "radiator",
]


class PointDto(ApiModel):
    x: float
    y: float


class MetricDto(ApiModel):
    label: str
    display_value: str


class NodeDataDto(ApiModel):
    label: str
    kind: EquipmentKind
    status: Literal["draft", "valid", "warning", "invalid", "running", "failed"]
    validity: Literal["VALID", "EXTRAPOLATED", "INVALID", "UNKNOWN"]
    parameters: dict[str, ParameterValueDto]
    metrics: list[MetricDto] | None = None


class PfdNodeDto(ApiModel):
    model_config = ConfigDict(alias_generator=_camel, populate_by_name=True, extra="allow")

    id: str = Field(min_length=1, max_length=120)
    type: str = "equipment"
    position: PointDto
    data: NodeDataDto


class PfdEdgeDto(ApiModel):
    model_config = ConfigDict(alias_generator=_camel, populate_by_name=True, extra="allow")

    id: str = Field(min_length=1, max_length=120)
    source: str
    target: str
    source_handle: str | None = None
    target_handle: str | None = None
    animated: bool | None = None


class PfdDraftDto(ApiModel):
    schema_version: Literal["v1alpha"]
    draft_id: str = Field(min_length=1, max_length=120)
    revision: int = Field(ge=1)
    base_case_id: str | None = None
    updated_at: datetime
    nodes: list[PfdNodeDto]
    edges: list[PfdEdgeDto]


class DiagnosticDto(ApiModel):
    severity: Literal["info", "warning", "error"]
    code: str
    message: str
    subject_id: str | None = None


class ValidationResultDto(ApiModel):
    valid: bool
    degrees_of_freedom: int
    diagnostics: list[DiagnosticDto]


class NodeResultDto(ApiModel):
    node_id: str
    status: Literal["draft", "valid", "warning", "invalid", "running", "failed"]
    validity: Literal["VALID", "EXTRAPOLATED", "INVALID", "UNKNOWN"]
    metrics: list[MetricDto]


class RunResultDto(ApiModel):
    run_id: str
    draft_id: str
    revision: int
    converged: bool
    conservation_closed: bool
    diagnostics: list[DiagnosticDto]
    node_results: list[NodeResultDto]
    completed_at: datetime


class ApiEnvelope(ApiModel):
    api_version: Literal["v1alpha"] = "v1alpha"
    data: Any
