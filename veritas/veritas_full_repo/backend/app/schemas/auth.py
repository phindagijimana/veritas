
from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    # Plain str: dev accounts use @veritas.local, which strict EmailStr rejects.
    email: str = Field(min_length=3)
    password: str


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str
    full_name: str | None = None
    role: str = "researcher"


class AuthUser(BaseModel):
    email: str
    full_name: str | None = None
    role: str = "researcher"
    is_active: bool = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUser


class MeResponse(BaseModel):
    data: AuthUser
