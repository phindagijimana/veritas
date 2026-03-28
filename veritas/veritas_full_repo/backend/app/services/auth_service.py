from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from jose import jwt

from app.core.config import get_settings
from app.schemas.auth import AuthUser


@dataclass
class AuthService:
    users: dict[str, dict]

    @classmethod
    def build(cls) -> "AuthService":
        settings = get_settings()
        return cls(
            users={
                settings.auth_default_dev_email: {
                    "email": settings.auth_default_dev_email,
                    "password": "dev-password",
                    "role": settings.auth_default_dev_role,
                    "full_name": "Development User",
                    "is_active": True,
                },
                "admin@veritas.local": {
                    "email": "admin@veritas.local",
                    "password": "admin-password",
                    "role": "admin",
                    "full_name": "Veritas Admin",
                    "is_active": True,
                },
                "researcher@veritas.local": {
                    "email": "researcher@veritas.local",
                    "password": "researcher-password",
                    "role": "researcher",
                    "full_name": "Veritas Researcher",
                    "is_active": True,
                },
            }
        )

    def register_user(self, email: str, password: str, full_name: str | None = None, role: str = "researcher") -> AuthUser:
        if email in self.users:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists.")
        self.users[email] = {"email": email, "password": password, "role": role, "full_name": full_name, "is_active": True}
        return AuthUser(email=email, role=role, full_name=full_name, is_active=True)

    def authenticate_user(self, email: str, password: str) -> Optional[AuthUser]:
        record = self.users.get(email)
        if not record or record["password"] != password:
            return None
        return AuthUser(email=record["email"], role=record["role"], full_name=record.get("full_name"), is_active=record.get("is_active", True))

    def create_access_token(self, subject: str, role: str = "researcher", full_name: str | None = None) -> str:
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
