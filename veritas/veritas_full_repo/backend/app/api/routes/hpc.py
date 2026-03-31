from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.hpc import (
    HPCConnectionConfig,
    HPCConnectionListResponse,
    HPCConnectionProbeRead,
    HPCConnectionProbeResponse,
    HPCConnectionResponse,
    HPCSummaryResponse,
)
from app.services.hpc_service import HPCConnectionService

router = APIRouter(prefix="/hpc", tags=["hpc"])


@router.get("/summary", response_model=HPCSummaryResponse)
def hpc_summary(db: Session = Depends(get_db)):
    """Queue counts and active SSH connection for the Veritas operator UI (no admin gate)."""
    return {"data": HPCConnectionService.summary(db)}


@router.get("/connections", response_model=HPCConnectionListResponse)
def list_hpc_connections(db: Session = Depends(get_db)):
    return {"data": HPCConnectionService.list_connections(db)}


@router.post("/connect", response_model=HPCConnectionResponse)
def connect_hpc(payload: HPCConnectionConfig, db: Session = Depends(get_db)):
    try:
        return {"data": HPCConnectionService.connect(db, payload)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/test-connection", response_model=HPCConnectionProbeResponse)
def test_hpc_connection(payload: HPCConnectionConfig, db: Session = Depends(get_db)):
    try:
        row = HPCConnectionService.test_connection(db, payload)
        probe = HPCConnectionProbeRead(
            id=row.id,
            hostname=row.hostname,
            username=row.username,
            port=row.port,
            ssh_key_reference=row.ssh_key_reference,
            notes=row.notes,
            status=row.status,
            is_active=row.is_active,
            created_at=row.created_at,
        )
        return {"data": probe}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
