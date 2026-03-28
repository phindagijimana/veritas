from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user, require_admin
from app.schemas.admin import AdminInboxResponse
from app.schemas.hpc import HPCSummaryResponse
from app.services.admin_service import AdminService
from app.services.hpc_service import HPCConnectionService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/inbox", response_model=AdminInboxResponse)
def admin_inbox(db: Session = Depends(get_db), _=Depends(require_admin)):
    return {"data": AdminService.inbox(db)}


@router.get("/hpc-summary", response_model=HPCSummaryResponse)
def admin_hpc_summary(db: Session = Depends(get_db), _=Depends(require_admin)):
    return {"data": HPCConnectionService.summary(db)}
