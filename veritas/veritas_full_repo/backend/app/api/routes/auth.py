
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core import api_tokens as pat
from app.core.config import get_settings
from app.core.security import CurrentUser, get_current_user, require_jwt
from app.db.session import get_db
from app.models.api_token import ApiToken
from app.models.user import User
from app.schemas.auth import (
    ApiTokenCreateRequest,
    ApiTokenCreateResponse,
    ApiTokenItem,
    ApiTokenListResponse,
    LoginRequest,
    MeResponse,
    RegisterRequest,
    TokenResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    service = AuthService.build(db=db)
    user = service.authenticate_user(payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    token = service.create_access_token(subject=user.email, role=user.role, full_name=user.full_name)
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    service = AuthService.build(db=db)
    # Self-registration is always "researcher"; admins are promoted out-of-band
    # (DB seed in dev, or future admin endpoint). The payload role is ignored.
    user = service.register_user(payload.email, payload.password, payload.full_name, role="researcher")
    token = service.create_access_token(subject=user.email, role=user.role, full_name=user.full_name)
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.get("/me", response_model=MeResponse)
def me(user=Depends(get_current_user)):
    return {"data": user}


@router.get("/mode")
def auth_mode():
    settings = get_settings()
    return {"data": {"enabled": settings.auth_enabled, "mode": settings.auth_mode}}


@router.get("/bootstrap-status")
def bootstrap_status(db: Session = Depends(get_db)):
    """Used by LoginGate to decide whether to show the first-admin form.

    Reports `needs_bootstrap=true` only when auth is enabled AND no active
    admin user exists in the DB. Once any admin is in place this flips to
    false and stays false, so the bootstrap form can never be used to
    overwrite an existing admin.
    """
    settings = get_settings()
    if not settings.auth_enabled:
        return {"data": {"needs_bootstrap": False, "auth_enabled": False}}
    admin_count = db.query(User).filter(User.role == "admin", User.is_active.is_(True)).count()
    return {"data": {"needs_bootstrap": admin_count == 0, "auth_enabled": True}}


@router.post("/bootstrap-admin", response_model=TokenResponse)
def bootstrap_admin(payload: RegisterRequest, db: Session = Depends(get_db)):
    """One-shot creation of the first admin when the DB has none.

    Refuses if auth is disabled (use AUTH_ENABLED=true), or if any active
    admin already exists. Intended for use from the LoginGate's bootstrap
    form right after `alembic upgrade head` on a fresh production DB —
    saves an ops user from having to shell in and run
    `veritas-api users create-admin`.
    """
    settings = get_settings()
    if not settings.auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="AUTH_ENABLED is false; admins are not used in this deployment.",
        )
    admin_count = db.query(User).filter(User.role == "admin", User.is_active.is_(True)).count()
    if admin_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An admin already exists; use the regular login or admin endpoints.",
        )
    if not payload.password or len(payload.password) < 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 12 characters.",
        )
    service = AuthService.build(db=db)
    user = service.register_user(payload.email, payload.password, payload.full_name, role="admin")
    token = service.create_access_token(subject=user.email, role=user.role, full_name=user.full_name)
    return {"access_token": token, "token_type": "bearer", "user": user}


# ───────── personal access tokens ─────────

def _user_row(db: Session, current: CurrentUser) -> User:
    row = db.query(User).filter(User.email == current.email).one_or_none()
    if row is None:
        # Dev mode user (auth disabled) may not have a DB row. Bootstrap one so
        # PATs can still be created and traced to a user_id.
        row = User(
            email=current.email,
            password_hash="!",  # unusable; this account cannot log in via password
            full_name=current.full_name,
            role=current.role or "researcher",
            is_active=True,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _to_item(row: ApiToken) -> ApiTokenItem:
    return ApiTokenItem(
        id=row.id,
        label=row.label,
        prefix=row.prefix,
        created_at=row.created_at,
        last_used_at=row.last_used_at,
        expires_at=row.expires_at,
        revoked_at=row.revoked_at,
    )


@router.post("/tokens", response_model=ApiTokenCreateResponse, status_code=status.HTTP_201_CREATED)
def create_api_token(
    payload: ApiTokenCreateRequest,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_jwt),
):
    user = _user_row(db, current)
    plaintext = pat.generate_token()
    token_row = ApiToken(
        user_id=user.id,
        label=payload.label.strip(),
        token_hash=pat.hash_token(plaintext),
        prefix=pat.short_prefix(plaintext),
        expires_at=(datetime.utcnow() + timedelta(days=payload.expires_in_days)) if payload.expires_in_days else None,
    )
    db.add(token_row)
    db.commit()
    db.refresh(token_row)
    return {"data": _to_item(token_row), "token": plaintext}


@router.get("/tokens", response_model=ApiTokenListResponse)
def list_api_tokens(db: Session = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    user = _user_row(db, current)
    rows = (
        db.query(ApiToken)
        .filter(ApiToken.user_id == user.id)
        .order_by(ApiToken.created_at.desc())
        .all()
    )
    return {"data": [_to_item(r) for r in rows]}


@router.delete("/tokens/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_token(
    token_id: int,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    user = _user_row(db, current)
    row = (
        db.query(ApiToken)
        .filter(ApiToken.id == token_id, ApiToken.user_id == user.id)
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found.")
    if row.revoked_at is None:
        row.revoked_at = datetime.utcnow()
        db.add(row)
        db.commit()
    return None
