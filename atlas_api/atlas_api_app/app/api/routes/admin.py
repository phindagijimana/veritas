from __future__ import annotations

import json
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import AccessLevel
from app.db.session import get_db
from app.models.audit_event import AuditEvent
from app.models.dataset import AtlasDataset
from app.models.dataset_grant import DatasetPermissionGrant
from app.security.deps import require_admin
from app.security.models import Principal
from app.services.audit import record_audit

router = APIRouter(prefix="/admin", tags=["admin"])


class GrantCreate(BaseModel):
    dataset_id: str
    principal_type: str = "user"
    principal_id: str
    access_level: str = Field(default=AccessLevel.READ.value, description="read | write | admin")


class GrantUpdate(BaseModel):
    access_level: Optional[str] = None


def _get_grant_or_404(db: Session, grant_id: int) -> DatasetPermissionGrant:
    row = db.get(DatasetPermissionGrant, grant_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grant not found")
    return row


@router.get("/grants")
def list_grants(
    dataset_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin),
) -> dict[str, Any]:
    q = select(DatasetPermissionGrant).order_by(DatasetPermissionGrant.id)
    if dataset_id:
        q = q.where(DatasetPermissionGrant.dataset_id == dataset_id)
    rows = db.scalars(q).all()
    return {
        "data": [
            {
                "id": r.id,
                "dataset_id": r.dataset_id,
                "principal_type": r.principal_type,
                "principal_id": r.principal_id,
                "access_level": r.access_level,
            }
            for r in rows
        ],
        "count": len(rows),
        "principal_id": principal.principal_id,
    }


@router.post("/grants", status_code=status.HTTP_201_CREATED)
def create_grant(
    body: GrantCreate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin),
) -> dict[str, Any]:
    if body.access_level not in {AccessLevel.READ.value, AccessLevel.WRITE.value, AccessLevel.ADMIN.value}:
        raise HTTPException(status_code=400, detail="Invalid access_level")
    ds = db.scalar(select(AtlasDataset).where(AtlasDataset.dataset_id == body.dataset_id))
    if ds is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    row = DatasetPermissionGrant(
        dataset_id=body.dataset_id,
        principal_type=body.principal_type,
        principal_id=body.principal_id,
        access_level=body.access_level,
    )
    db.add(row)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Grant already exists or constraint violation") from None
    record_audit(
        db,
        actor=principal,
        action="grant.create",
        resource_type="dataset_grant",
        resource_id=str(row.id),
        detail={"dataset_id": row.dataset_id, "principal_id": row.principal_id, "access_level": row.access_level},
    )
    db.commit()
    db.refresh(row)
    return {"data": {"id": row.id, "dataset_id": row.dataset_id, "principal_id": row.principal_id, "access_level": row.access_level}}


@router.patch("/grants/{grant_id}")
def update_grant(
    grant_id: int,
    body: GrantUpdate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin),
) -> dict[str, Any]:
    row = _get_grant_or_404(db, grant_id)
    if body.access_level is not None:
        if body.access_level not in {AccessLevel.READ.value, AccessLevel.WRITE.value, AccessLevel.ADMIN.value}:
            raise HTTPException(status_code=400, detail="Invalid access_level")
        row.access_level = body.access_level
    db.add(row)
    record_audit(
        db,
        actor=principal,
        action="grant.update",
        resource_type="dataset_grant",
        resource_id=str(row.id),
        detail={"access_level": row.access_level},
    )
    db.commit()
    db.refresh(row)
    return {"data": {"id": row.id, "access_level": row.access_level}}


@router.delete("/grants/{grant_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_grant(
    grant_id: int,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin),
) -> Response:
    row = _get_grant_or_404(db, grant_id)
    rid = row.id
    dataset_id = row.dataset_id
    principal_id = row.principal_id
    record_audit(
        db,
        actor=principal,
        action="grant.revoke",
        resource_type="dataset_grant",
        resource_id=str(rid),
        detail={"dataset_id": dataset_id, "principal_id": principal_id},
    )
    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/audit-events")
def list_audit_events(
    limit: int = Query(50, ge=1, le=500),
    action: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin),
) -> dict[str, Any]:
    stmt = select(AuditEvent)
    if action:
        stmt = stmt.where(AuditEvent.action == action)
    stmt = stmt.order_by(AuditEvent.id.desc()).limit(limit)
    rows = db.scalars(stmt).all()
    out = []
    for r in rows:
        detail = None
        if r.detail_json:
            try:
                detail = json.loads(r.detail_json)
            except (json.JSONDecodeError, TypeError):
                detail = {"raw": r.detail_json}
        out.append(
            {
                "id": r.id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "actor_principal_id": r.actor_principal_id,
                "action": r.action,
                "resource_type": r.resource_type,
                "resource_id": r.resource_id,
                "staging_id": r.staging_id,
                "detail": detail,
            }
        )
    return {"data": out, "count": len(out), "principal_id": principal.principal_id}
