from __future__ import annotations

from pydantic import BaseModel

from app.schemas.common import DataResponse, ORMModel


class DatasetCreate(BaseModel):
    code: str
    name: str
    disease_group: str
    collection_name: str = "Default Collection"
    version: str = "v1"
    modality: str = "MRI"
    source: str | None = None
    subject_count: int = 0
    hpc_root_path: str | None = None
    manifest_path: str | None = None
    label_schema: str | None = None
    qc_status: str = "Curated"
    benchmark_enabled: bool = True
    description: str | None = None
    is_active: bool = True


class DatasetRead(ORMModel):
    id: int
    code: str
    name: str
    disease_group: str
    collection_name: str
    version: str
    modality: str
    source: str | None = None
    subject_count: int
    hpc_root_path: str | None = None
    manifest_path: str | None = None
    label_schema: str | None = None
    qc_status: str
    benchmark_enabled: bool
    description: str | None = None
    is_active: bool


class DatasetDiseaseSummary(BaseModel):
    disease_group: str
    dataset_count: int
    active_dataset_count: int


DatasetListResponse = DataResponse[list[DatasetRead]]
DatasetItemResponse = DataResponse[DatasetRead]
DatasetDiseaseListResponse = DataResponse[list[DatasetDiseaseSummary]]


class DatasetValidationCheck(BaseModel):
    name: str
    ok: bool
    detail: str


class DatasetValidationResult(BaseModel):
    dataset_id: int
    dataset_name: str
    dataset_code: str
    valid: bool
    summary: str
    checks: list[DatasetValidationCheck]


DatasetValidationResponse = DataResponse[DatasetValidationResult]
