from __future__ import annotations

from pydantic import BaseModel
from typing import Optional

class ExecuteStageRequest(BaseModel):
    request_id: str
    atlas_dataset_id: str
    destination_root: Optional[str] = None

class StageValidationResponse(BaseModel):
    request_id: str
    status: str
    validation_status: str
    staged_dataset_path: Optional[str] = None
    transfer_log: Optional[str] = None
    message: Optional[str] = None
