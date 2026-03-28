
from __future__ import annotations

from fastapi import APIRouter

from app.schemas.atlas import AtlasExecutionBundle, AtlasSubmissionContext
from app.services.atlas_execution_service import AtlasExecutionService

router = APIRouter(prefix="/atlas-execution", tags=["atlas-execution"])


@router.post("/prepare", response_model=AtlasExecutionBundle)
def prepare_atlas_execution(context: AtlasSubmissionContext) -> AtlasExecutionBundle:
    service = AtlasExecutionService()
    return service.prepare_submission(context)
