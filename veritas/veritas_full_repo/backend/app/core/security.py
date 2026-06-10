from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.api_tokens import hash_token, looks_like_pat
from app.core.config import get_settings
from app.db.session import get_db


@dataclass
class CurrentUser:
    email: str
    role: str = "researcher"
    full_name: str | None = None
    is_active: bool = True
    # "jwt" or "pat" — useful so downstream code can refuse PATs for sensitive ops.
    auth_method: str = "jwt"


def _decode_bearer_jwt(token: str) -> CurrentUser:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.auth_secret_key,
            algorithms=[settings.auth_algorithm],
            options={"require": ["exp", "sub"]},
        )
        return CurrentUser(
            email=str(payload["sub"]),
            role=str(payload.get("role", "researcher")),
            full_name=payload.get("full_name"),
            is_active=True,
            auth_method="jwt",
        )
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token.") from exc


def _resolve_pat(token: str, db: Session) -> CurrentUser:
    # Local import to avoid circular import at module load time.
    from app.models.api_token import ApiToken
    from app.models.user import User

    row = db.query(ApiToken).filter(ApiToken.token_hash == hash_token(token)).one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token.")
    if row.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API token has been revoked.")
    if row.expires_at is not None and row.expires_at <= datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API token has expired.")
    user = db.query(User).filter(User.id == row.user_id).one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API token user is inactive.")

    row.last_used_at = datetime.utcnow()
    db.add(row)
    db.commit()

    return CurrentUser(
        email=user.email,
        role=user.role,
        full_name=user.full_name,
        is_active=user.is_active,
        auth_method="pat",
    )


def get_current_user_optional(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> CurrentUser:
    settings = get_settings()
    if not settings.auth_enabled:
        return CurrentUser(
            email=settings.auth_default_dev_email,
            role=settings.auth_default_dev_role,
            full_name="Development User",
            auth_method="jwt",
        )
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    token = authorization.split(" ", 1)[1].strip()
    if looks_like_pat(token):
        return _resolve_pat(token, db)
    return _decode_bearer_jwt(token)


def get_current_user(user: CurrentUser = Depends(get_current_user_optional)) -> CurrentUser:
    return user


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    settings = get_settings()
    if not settings.auth_enabled:
        return user
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return user


def require_jwt(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """For operations that should not be reachable via a PAT (e.g. PAT creation
    itself, so a leaked PAT cannot mint more PATs)."""
    settings = get_settings()
    if not settings.auth_enabled:
        return user
    if user.auth_method != "jwt":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This operation requires a session login (not an API token).",
        )
    return user
