from __future__ import annotations


from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.common import DataResponse, ORMModel


class ReportCreate(BaseModel):
    request_id: int
    pdf_path: str | None = None
    json_path: str | None = None
    csv_path: str | None = None
    status: str = "pending"


class ArtifactRead(BaseModel):
    id: str
    name: str
    type: str
    status: str
    url: str | None = None
    size: str | None = None
    metadata: dict[str, Any] | None = None


class MetricSummary(BaseModel):
    dice: float | None = None
    sensitivity: float | None = None
    specificity: float | None = None
    precision: float | None = None
    recall: float | None = None
    auc: float | None = None


class ReportRead(ORMModel):
    id: int
    request_id: int
    status: str
    pdf_path: str | None = None
    json_path: str | None = None
    csv_path: str | None = None
    metrics_summary_json: str | None = None
    published_at: datetime | None = None
    created_at: datetime


class ReportDetail(BaseModel):
    request_id: str
    status: str
    generated_at: datetime | None = None
    published_at: datetime | None = None
    metrics_summary: MetricSummary | None = None
    artifacts: list[ArtifactRead]


class DownloadLink(BaseModel):
    url: str
    artifact_type: str
    status: str = "ready"


ReportListResponse = DataResponse[list[ReportRead]]
ReportItemResponse = DataResponse[ReportRead]
ReportDetailResponse = DataResponse[ReportDetail]
DownloadLinkResponse = DataResponse[DownloadLink]
