from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user, require_admin
from app.schemas.hpc import (
    HPCConnectionConfig,
    HPCConnectionListResponse,
    HPCConnectionResponse,
    HPCSummaryResponse,
)
from app.services.hpc_service import HPCConnectionService

router = APIRouter(prefix="/hpc", tags=["hpc"])


@router.get("/summary", response_model=HPCSummaryResponse)
def hpc_summary(db: Session = Depends(get_db), _=Depends(require_admin)):
    return {"data": HPCConnectionService.summary(db)}


@router.get("/connections", response_model=HPCConnectionListResponse)
def list_hpc_connections(db: Session = Depends(get_db)):
    return {"data": HPCConnectionService.list_connections(db)}


@router.post("/connect", response_model=HPCConnectionResponse)
def connect_hpc(payload: HPCConnectionConfig, db: Session = Depends(get_db)):
    return {"data": HPCConnectionService.connect(db, payload)}


@router.post("/test-connection", response_model=HPCConnectionResponse)
def test_hpc_connection(payload: HPCConnectionConfig, db: Session = Depends(get_db)):
    return {"data": HPCConnectionService.test_connection(db, payload)}
