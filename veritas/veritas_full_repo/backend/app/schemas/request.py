from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import DataResponse, ORMModel


class EvaluationRequestCreate(BaseModel):
    datasets: list[str] = Field(default_factory=list)
    pipeline: str
    description: str | None = None


class EvaluationRequestStatusUpdate(BaseModel):
    current_phase: str
    admin_note: str | None = None


class TimelineItem(BaseModel):
    code: str
    label: str
    active: bool
    complete: bool


class EvaluationRequestRead(BaseModel):
    id: str
    request_id: int
    datasets: list[str]
    submitted_at: datetime
    current_phase: str
    report_status: str
    admin_note: str | None = None
    timeline: list[TimelineItem] = Field(default_factory=list)
    pipeline: str | None = None
    pipeline_id: int | None = None
    dataset_ids: list[int] = Field(default_factory=list)
    description: str | None = None


EvaluationRequestListResponse = DataResponse[list[EvaluationRequestRead]]
EvaluationRequestItemResponse = DataResponse[EvaluationRequestRead]
