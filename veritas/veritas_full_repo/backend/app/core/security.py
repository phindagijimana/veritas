from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt

from app.core.config import get_settings


@dataclass
class CurrentUser:
    email: str
    role: str = "researcher"
    full_name: str | None = None
    is_active: bool = True


def _decode_bearer_token(token: str) -> CurrentUser:
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
        )
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token.") from exc


def get_current_user_optional(authorization: Optional[str] = Header(default=None)) -> CurrentUser:
    settings = get_settings()
    if not settings.auth_enabled:
        return CurrentUser(email=settings.auth_default_dev_email, role=settings.auth_default_dev_role, full_name="Development User")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    token = authorization.split(" ", 1)[1]
    return _decode_bearer_token(token)


def get_current_user(user: CurrentUser = Depends(get_current_user_optional)) -> CurrentUser:
    return user


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    settings = get_settings()
    if not settings.auth_enabled:
        return user
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return user
