from __future__ import annotations

from fastapi import APIRouter

from app.schemas.atlas_phase_c import PrepareStagingRequest
from app.services.atlas_phase_c_service import AtlasPhaseCService

router = APIRouter(prefix="/atlas/phase-c", tags=["atlas-phase-c"])
service = AtlasPhaseCService()


@router.post("/prepare")
def prepare_staging(payload: PrepareStagingRequest):
    bundle = service.prepare_and_stage(
        request_id=payload.request_id,
        atlas_dataset_id=payload.atlas_dataset_id or "atlas-dataset-unknown",
    )
    return {"data": service.to_response(bundle).model_dump()}


@router.get("/requests/{request_id}/staging-status")
def get_staging_status(request_id: str):
    bundle = service.prepare_and_stage(
        request_id=request_id,
        atlas_dataset_id="atlas-dataset-demo",
    )
    return {"data": service.to_response(bundle).model_dump()}
