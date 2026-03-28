from __future__ import annotations

from pydantic import BaseModel
from typing import Optional

class StagingStatusResponse(BaseModel):
    request_id: str
    atlas_dataset_id: Optional[str] = None
    atlas_staging_id: Optional[str] = None
    status: str
    approval_status: Optional[str] = None
    staged_dataset_path: Optional[str] = None
    manifest_url: Optional[str] = None
    message: Optional[str] = None

class PrepareStagingRequest(BaseModel):
    request_id: str
    atlas_dataset_id: Optional[str] = None
