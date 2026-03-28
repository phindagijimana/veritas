from __future__ import annotations

from fastapi import APIRouter

from app.schemas.atlas import AtlasStagingRequest
from app.services.atlas_client import build_atlas_client
from app.services.dataset_staging_service import DatasetStagingService

router = APIRouter(prefix="/atlas", tags=["atlas"])


@router.get("/datasets")
def list_atlas_datasets():
    client = build_atlas_client()
    return {"data": [item.model_dump() for item in client.list_datasets()]}


@router.get("/datasets/{atlas_dataset_id}")
def get_atlas_dataset(atlas_dataset_id: str):
    client = build_atlas_client()
    return {"data": client.get_dataset(atlas_dataset_id).model_dump()}


@router.post("/staging/request")
def request_dataset_staging(payload: AtlasStagingRequest):
    client = build_atlas_client()
    staging = client.request_staging(payload)
    manifest = client.get_staging_manifest(staging.atlas_staging_id)
    plan = DatasetStagingService().build_staging_plan(
        request_id=payload.request_id,
        atlas_dataset_id=payload.atlas_dataset_id,
        staging=staging,
        manifest=manifest,
    )
    return {"data": {"staging": staging.dict(), "manifest": manifest.dict(), "plan": plan.dict()}}


@router.get("/staging/{atlas_staging_id}")
def get_staging_status(atlas_staging_id: str):
    client = build_atlas_client()
    return {"data": client.get_staging_status(atlas_staging_id).dict()}
