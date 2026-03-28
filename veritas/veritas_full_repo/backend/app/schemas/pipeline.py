from __future__ import annotations

from pydantic import BaseModel

from app.schemas.common import DataResponse, ORMModel


class PipelineCreate(BaseModel):
    name: str
    title: str
    image: str
    modality: str = "MRI"
    description: str | None = None
    yaml_definition: str


class PipelineRead(ORMModel):
    id: int
    name: str
    title: str
    image: str
    modality: str
    description: str | None = None
    yaml_definition: str
    is_active: bool


PipelineListResponse = DataResponse[list[PipelineRead]]
PipelineItemResponse = DataResponse[PipelineRead]


class PipelineValidationRequest(BaseModel):
    yaml_definition: str


class PipelineValidationCheck(BaseModel):
    name: str
    ok: bool
    detail: str


class PipelineValidationResult(BaseModel):
    valid: bool
    summary: str
    checks: list[PipelineValidationCheck]
    normalized: dict | None = None


PipelineValidationResponse = DataResponse[PipelineValidationResult]
