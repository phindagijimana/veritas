from __future__ import annotations

import json
import secrets
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import StorageProvider
from app.db.session import get_db
from app.models.dataset import AtlasDataset
from app.models.staging_session import StagingSession
from app.security.deps import get_current_principal
from app.security.models import Principal
from app.services.dataset_access import principal_may_create_staging
from app.services.staging_authorization import ensure_stage_allowed
from app.services.staging_transfer import hydrate_staging_after_request

router = APIRouter(prefix="/staging", tags=["staging"])


class VeritasStagingRequestBody(BaseModel):
    request_id: str
    atlas_dataset_id: str
    user_id: str | None = None
    purpose: str = "benchmark_validation"
    pipeline_id: str | None = None
    compute_target: str | None = None


def _get_dataset_row(db: Session, dataset_id: str) -> AtlasDataset:
    row = db.scalar(select(AtlasDataset).where(AtlasDataset.dataset_id == dataset_id))
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    return row


def _get_staging_row(db: Session, staging_id: str) -> StagingSession:
    row = db.scalar(select(StagingSession).where(StagingSession.staging_id == staging_id))
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staging session not found")
    return row


def _build_manifest_url(staging_id: str) -> str:
    settings = get_settings()
    base = settings.public_base_url.rstrip("/")
    prefix = settings.api_prefix.rstrip("/")
    return f"{base}{prefix}/staging/{staging_id}/manifest"


def _veritas_staging_response_payload(session: StagingSession) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "transfer_status": session.transfer_status,
    }
    if session.transfer_log:
        meta["transfer_log"] = session.transfer_log
    return {
        "atlas_staging_id": session.staging_id,
        "atlas_dataset_id": session.dataset_id,
        "status": session.status,
        "token": session.token,
        "manifest_url": session.manifest_url,
        "source": StorageProvider.PENNSIEVE.value,
        "metadata": meta,
    }


def _stub_manifest_files(dataset_id: str) -> list[dict[str, Any]]:
    return [
        {"path": f"{dataset_id}/sub-01/T1w.nii.gz", "size": 1024},
        {"path": f"{dataset_id}/sub-01/labels.json", "size": 128},
    ]


@router.post("/request")
async def veritas_request_staging(
    payload: VeritasStagingRequestBody,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> dict[str, Any]:
    settings = get_settings()
    row = _get_dataset_row(db, payload.atlas_dataset_id)
    compute_target = (payload.compute_target or settings.veritas_default_compute_target).strip()
    ensure_stage_allowed(row, compute_target)
    if not principal_may_create_staging(principal, row, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to request staging for this dataset.",
        )

    staging_id = f"STAGE-{secrets.token_hex(8).upper()}"
    token = secrets.token_urlsafe(32)
    manifest_url = _build_manifest_url(staging_id)

    session = StagingSession(
        staging_id=staging_id,
        dataset_id=row.dataset_id,
        request_id=payload.request_id,
        compute_target=compute_target,
        status="approved",
        token=token,
        manifest_url=manifest_url,
        principal_id=principal.principal_id,
        transfer_status="pending",
    )
    db.add(session)
    db.flush()
    await hydrate_staging_after_request(db, session, row, settings)
    db.commit()
    db.refresh(session)

    return {"data": _veritas_staging_response_payload(session)}


@router.get("/{staging_id}")
async def veritas_staging_status(
    staging_id: str,
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_principal),
) -> dict[str, Any]:
    session = _get_staging_row(db, staging_id)
    return {"data": _veritas_staging_response_payload(session)}


@router.get("/{staging_id}/manifest")
async def veritas_staging_manifest(
    staging_id: str,
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_principal),
) -> dict[str, Any]:
    session = _get_staging_row(db, staging_id)
    files: list[dict[str, Any]] = _stub_manifest_files(session.dataset_id)
    if session.manifest_files_json:
        try:
            parsed = json.loads(session.manifest_files_json)
            if isinstance(parsed, list):
                files = parsed
        except (json.JSONDecodeError, TypeError):
            pass
    body = {
        "atlas_staging_id": session.staging_id,
        "atlas_dataset_id": session.dataset_id,
        "files": files,
        "dataset_root": None,
        "source": StorageProvider.PENNSIEVE.value,
        "metadata": {
            "compute_target": session.compute_target,
            "request_id": session.request_id,
            "transfer_status": session.transfer_status,
        },
    }
    return {"data": body}
