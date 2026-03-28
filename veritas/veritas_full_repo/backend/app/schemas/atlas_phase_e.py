from __future__ import annotations

from pydantic import BaseModel
from typing import Dict, Any

class HiddenTestExecutionRequest(BaseModel):
    request_id: str
    atlas_dataset_id: str
    staged_dataset_path: str
    pipeline_ref: str

class HiddenTestExecutionResponse(BaseModel):
    request_id: str
    atlas_dataset_id: str
    hidden_test_status: str
    evaluation_bundle_id: str
    metrics: Dict[str, Any]
    dataset_hash: str
    pipeline_hash: str
    container_hash: str
    message: str
