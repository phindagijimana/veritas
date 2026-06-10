
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

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


# ───── personal access tokens ─────

class ApiTokenCreateRequest(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    expires_in_days: Optional[int] = Field(default=None, ge=1, le=3650)


class ApiTokenItem(BaseModel):
    id: int
    label: str
    prefix: str
    created_at: datetime
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None


class ApiTokenCreateResponse(BaseModel):
    """Returned ONCE at creation. The plaintext token is never persisted; it
    cannot be retrieved again, so clients must store it immediately."""
    data: ApiTokenItem
    token: str


class ApiTokenListResponse(BaseModel):
    data: List[ApiTokenItem]
