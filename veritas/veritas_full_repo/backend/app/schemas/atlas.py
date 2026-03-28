from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class AtlasDatasetSummary(BaseModel):
    atlas_dataset_id: str
    name: str
    disease_group: str
    biomarker_group: str
    version: str
    source: str = "pennsieve"
    benchmark_enabled: bool = True


class AtlasDatasetDetail(AtlasDatasetSummary):
    description: Optional[str] = None
    subject_count: Optional[int] = None
    manifest_ref: Optional[str] = None
    labels_available: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AtlasStagingRequest(BaseModel):
    request_id: str
    atlas_dataset_id: str
    user_id: Optional[str] = None
    purpose: str = "benchmark_validation"
    pipeline_id: Optional[str] = None


class AtlasStagingResponse(BaseModel):
    atlas_staging_id: str
    atlas_dataset_id: str
    status: str
    token: Optional[str] = None
    manifest_url: Optional[str] = None
    expires_at: Optional[str] = None
    source: str = "pennsieve"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AtlasStagingManifest(BaseModel):
    atlas_staging_id: str
    atlas_dataset_id: str
    files: List[Dict[str, Any]] = Field(default_factory=list)
    dataset_root: Optional[str] = None
    source: str = "pennsieve"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DatasetStagingPlan(BaseModel):
    atlas_dataset_id: str
    atlas_staging_id: str
    request_id: str
    destination_root: str
    manifest_url: Optional[str] = None
    access_token_env_var: str = "ATLAS_STAGING_TOKEN"
    env: Dict[str, str] = Field(default_factory=dict)
    stage_script: str
    staged_dataset_path: str


class AtlasExecutionBundle(BaseModel):
    atlas_dataset_id: str
    atlas_staging_id: str
    atlas_approval_status: str
    staging_status: str
    source: str = "pennsieve"
    staged_dataset_path: Optional[str] = None
    stage_script_path: Optional[str] = None
    stage_env_path: Optional[str] = None
    manifest_url: Optional[str] = None
    message: Optional[str] = None
    env: Dict[str, str] = Field(default_factory=dict)


class AtlasSubmissionContext(BaseModel):
    request_id: str
    atlas_dataset_id: str
    user_id: Optional[str] = None
    pipeline_id: Optional[str] = None
    consented_for_benchmark: bool = False
