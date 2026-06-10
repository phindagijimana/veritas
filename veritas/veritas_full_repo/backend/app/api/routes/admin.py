from __future__ import annotations

import secrets
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.passwords import hash_password
from app.core.security import get_current_user, require_admin
from app.db.session import get_db
from app.models.user import User
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


# ─────────────────── users ───────────────────

class _AdminUserItem(BaseModel):
    email: str
    role: str
    is_active: bool
    full_name: Optional[str] = None


class AdminUserListResponse(BaseModel):
    data: List[_AdminUserItem]


class _AdminPasswordResetResponse(BaseModel):
    email: str
    password: str


class AdminPasswordResetResponse(BaseModel):
    """Returned ONCE on admin-mediated password reset. The plaintext password
    is not persisted; deliver it to the user out-of-band (eg. encrypted email)
    and have them log in to set their own."""

    data: _AdminPasswordResetResponse


class AdminSetRoleRequest(BaseModel):
    role: str


@router.get("/users", response_model=AdminUserListResponse)
def admin_list_users(db: Session = Depends(get_db), _=Depends(require_admin)):
    rows = db.query(User).order_by(User.role.asc(), User.email.asc()).all()
    return {
        "data": [
            _AdminUserItem(email=u.email, role=u.role, is_active=u.is_active, full_name=u.full_name)
            for u in rows
        ]
    }


@router.post(
    "/users/{email}/reset-password",
    response_model=AdminPasswordResetResponse,
    status_code=status.HTTP_200_OK,
)
def admin_reset_password(
    email: str,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    user = db.query(User).filter(User.email == email.strip().lower()).one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    new_password = secrets.token_urlsafe(24)  # ~32 chars, URL-safe
    user.password_hash = hash_password(new_password)
    db.add(user)
    db.commit()
    return {"data": {"email": user.email, "password": new_password}}


@router.patch("/users/{email}/role", response_model=AdminUserListResponse)
def admin_set_role(
    email: str,
    payload: AdminSetRoleRequest,
    db: Session = Depends(get_db),
    current=Depends(require_admin),
):
    role = payload.role.strip().lower()
    if role not in ("admin", "researcher"):
        raise HTTPException(status_code=400, detail="Role must be one of: admin, researcher.")
    user = db.query(User).filter(User.email == email.strip().lower()).one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    # Don't allow demoting the last admin (lockout protection).
    if user.role == "admin" and role != "admin":
        admin_count = db.query(User).filter(User.role == "admin", User.is_active.is_(True)).count()
        if admin_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot demote the last active admin; promote another user first.",
            )
    user.role = role
    db.add(user)
    db.commit()
    rows = db.query(User).order_by(User.role.asc(), User.email.asc()).all()
    return {
        "data": [
            _AdminUserItem(email=u.email, role=u.role, is_active=u.is_active, full_name=u.full_name)
            for u in rows
        ]
    }
