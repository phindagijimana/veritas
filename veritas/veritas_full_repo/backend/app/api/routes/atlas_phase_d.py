from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.atlas_phase_d import ExecuteStageRequest
from app.services.atlas_phase_d_service import AtlasPhaseDService

router = APIRouter(prefix="/atlas/phase-d", tags=["atlas-phase-d"])
service = AtlasPhaseDService()

STAGE_CACHE: dict[str, dict] = {}


@router.post("/execute-stage")
def execute_stage(payload: ExecuteStageRequest):
    state = service.execute_stage(
        request_id=payload.request_id,
        atlas_dataset_id=payload.atlas_dataset_id,
        destination_root=payload.destination_root,
    )
    STAGE_CACHE[payload.request_id] = {
        "status": state.status,
        "atlas_staging_id": f"AST-{payload.request_id}",
        "staged_dataset_path": state.staged_dataset_path,
        "manifest_url": state.manifest_url,
        "message": state.message,
        "transfer_log": state.transfer_log,
        "validation_status": "",
    }
    return {"data": STAGE_CACHE[payload.request_id]}


@router.post("/requests/{request_id}/staging-validate")
def validate_staging(request_id: str):
    cached = STAGE_CACHE.get(request_id)
    if not cached or not cached.get("staged_dataset_path"):
        raise HTTPException(status_code=404, detail="No staged dataset found for request.")
    result = service.validate_stage(request_id=request_id, staged_dataset_path=cached["staged_dataset_path"])
    cached["validation_status"] = result.validation_status
    cached["message"] = result.message
    cached["transfer_log"] = result.transfer_log
    return {"data": result.model_dump()}


@router.get("/requests/{request_id}/staging-status")
def get_staging_status(request_id: str):
    cached = STAGE_CACHE.get(
        request_id,
        {
            "status": "not_started",
            "atlas_staging_id": "",
            "staged_dataset_path": "",
            "manifest_url": "",
            "message": "Staging has not started.",
            "transfer_log": "",
            "validation_status": "",
        },
    )
    return {"data": cached}
