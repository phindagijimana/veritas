from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import DataResponse, ORMModel


class JobRead(ORMModel):
    id: str
    job_id: int
    request_id: str
    scheduler_job_id: str | None = None
    status: str
    job_type: str = "Evaluation"
    partition: str
    resources: str
    updated_at: datetime
    pipeline_ref: str | None = None
    dataset_name: str | None = None
    runtime_engine: str | None = None
    remote_workdir: str | None = None
    stdout_path: str | None = None
    stderr_path: str | None = None
    runtime_manifest_path: str | None = None
    metrics_path: str | None = None
    results_csv_path: str | None = None
    report_path: str | None = None


class JobAdvanceResult(BaseModel):
    job: JobRead
    request_status: str
    report_status: str


JobListResponse = DataResponse[list[JobRead]]
JobItemResponse = DataResponse[JobRead]
JobAdvanceResponse = DataResponse[JobAdvanceResult]
