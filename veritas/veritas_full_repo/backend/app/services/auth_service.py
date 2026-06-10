from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from jose import jwt
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.passwords import hash_password, verify_password
from app.models.user import User
from app.schemas.auth import AuthUser


def _to_auth_user(user: User) -> AuthUser:
    return AuthUser(
        email=user.email,
        role=user.role,
        full_name=user.full_name,
        is_active=user.is_active,
    )


@dataclass
class AuthService:
    db: Optional[Session] = None

    @classmethod
    def build(cls, db: Optional[Session] = None) -> "AuthService":
        return cls(db=db)

    def _require_db(self) -> Session:
        if self.db is None:
            raise RuntimeError("AuthService requires a database session for this operation.")
        return self.db

    def register_user(
        self,
        email: str,
        password: str,
        full_name: str | None = None,
        role: str = "researcher",
    ) -> AuthUser:
        db = self._require_db()
        email_norm = email.strip().lower()
        existing = db.query(User).filter(User.email == email_norm).one_or_none()
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists.")
        user = User(
            email=email_norm,
            password_hash=hash_password(password),
            full_name=full_name,
            role=role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return _to_auth_user(user)

    def authenticate_user(self, email: str, password: str) -> Optional[AuthUser]:
        db = self._require_db()
        email_norm = email.strip().lower()
        user = db.query(User).filter(User.email == email_norm).one_or_none()
        if user is None or not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return _to_auth_user(user)

    def create_access_token(
        self,
        subject: str,
        role: str = "researcher",
        full_name: str | None = None,
    ) -> str:
        settings = get_settings()
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.auth_access_token_expire_minutes)
        payload: dict = {
            "sub": subject,
            "role": role,
            "exp": int(expire.timestamp()),
        }
        if full_name is not None:
            payload["full_name"] = full_name
        return jwt.encode(payload, settings.auth_secret_key, algorithm=settings.auth_algorithm)
