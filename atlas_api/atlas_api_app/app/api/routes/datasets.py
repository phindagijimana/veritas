from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import DatasetVisibility, StorageProvider
from app.db.session import get_db
from app.integrations.pennsieve import PennsieveClient
from app.models.dataset import AtlasDataset
from app.security.deps import get_current_principal
from app.security.models import Principal
from app.services.dataset_access import principal_may_create_staging, principal_may_read_dataset
from app.services.staging_authorization import ensure_stage_allowed
from app.services.veritas_payloads import dataset_row_to_veritas_detail, dataset_row_to_veritas_summary

router = APIRouter(prefix="/datasets", tags=["datasets"])  # dataset access enforced via dataset_access


class StageRequest(BaseModel):
    compute_target: str
    requested_by: str | None = None


def _serialize_dataset(row: AtlasDataset) -> dict[str, Any]:
    visibility = row.visibility
    return {
        "dataset_id": row.dataset_id,
        "name": row.name,
        "visibility": visibility,
        "access_class": row.access_class,
        "storage_provider": row.storage_provider,
        "canonical_source": row.canonical_source,
        "downloadable": visibility == DatasetVisibility.PUBLIC.value,
        "staging_allowed": bool(row.staging_allowed),
        "allowed_compute_targets": list(row.allowed_compute_targets or []),
    }


def _get_dataset_row(db: Session, dataset_id: str) -> AtlasDataset:
    row = db.scalar(select(AtlasDataset).where(AtlasDataset.dataset_id == dataset_id))
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    return row


@router.get("")
async def list_datasets(
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> dict[str, Any]:
    rows = db.scalars(select(AtlasDataset).order_by(AtlasDataset.dataset_id)).all()
    visible = [r for r in rows if principal_may_read_dataset(principal, r, db)]
    return {
        "items": [_serialize_dataset(r) for r in visible],
        "data": [dataset_row_to_veritas_summary(r) for r in visible],
        "count": len(visible),
        "principal_id": principal.principal_id,
    }


@router.get("/{dataset_id}")
async def get_dataset(
    dataset_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> dict[str, Any]:
    row = _get_dataset_row(db, dataset_id)
    if not principal_may_read_dataset(principal, row, db):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    body = _serialize_dataset(row)
    body["principal_id"] = principal.principal_id
    body["data"] = dataset_row_to_veritas_detail(row)
    return body


@router.get("/{dataset_id}/download")
async def download_dataset(
    dataset_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> dict[str, Any]:
    row = _get_dataset_row(db, dataset_id)
    if not principal_may_read_dataset(principal, row, db):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    if row.visibility != DatasetVisibility.PUBLIC.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only datasets labeled as public or open-source may be downloaded.",
        )

    settings = get_settings()
    download_url = row.download_url
    pennsieve_resolved = False

    if settings.pennsieve_integration_enabled and row.pennsieve_package_id:
        client = PennsieveClient(settings)
        ps_url = await client.fetch_package_download_url(row.pennsieve_package_id)
        if ps_url:
            download_url = ps_url
            pennsieve_resolved = True

    return {
        "dataset_id": row.dataset_id,
        "downloadable": True,
        "download_url": download_url,
        "storage_provider": StorageProvider.PENNSIEVE.value,
        "requested_by": principal.principal_id,
        "pennsieve_resolved": pennsieve_resolved,
    }


@router.post("/{dataset_id}/stage")
async def stage_dataset(
    dataset_id: str,
    payload: StageRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> dict[str, Any]:
    row = _get_dataset_row(db, dataset_id)
    mode = ensure_stage_allowed(row, payload.compute_target)
    if not principal_may_create_staging(principal, row, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to request staging for this dataset.",
        )

    settings = get_settings()
    body: dict[str, Any] = {
        "dataset_id": row.dataset_id,
        "status": "authorized",
        "mode": mode,
        "canonical_source": row.canonical_source,
        "storage_provider": StorageProvider.PENNSIEVE.value,
        "compute_target": payload.compute_target,
        "requested_by": payload.requested_by or principal.principal_id,
    }
    if settings.pennsieve_integration_enabled:
        body["pennsieve_integration"] = True
        if row.pennsieve_package_id:
            body["pennsieve_package_id"] = row.pennsieve_package_id
            body["pennsieve_staging_note"] = (
                "Trigger export/staging via Pennsieve APIs or a worker using this package id; Atlas has authorized the target."
            )
    return body