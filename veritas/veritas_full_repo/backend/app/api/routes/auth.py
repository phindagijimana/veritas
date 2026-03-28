
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import get_settings
from app.core.security import get_current_user
from app.schemas.auth import LoginRequest, MeResponse, RegisterRequest, TokenResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    service = AuthService.build()
    user = service.authenticate_user(payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    token = service.create_access_token(subject=user.email, role=user.role, full_name=user.full_name)
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest):
    service = AuthService.build()
    user = service.register_user(payload.email, payload.password, payload.full_name, payload.role)
    token = service.create_access_token(subject=user.email, role=user.role, full_name=user.full_name)
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.get("/me", response_model=MeResponse)
def me(user=Depends(get_current_user)):
    return {"data": user}


@router.get("/mode")
def auth_mode():
    settings = get_settings()
    return {"data": {"enabled": settings.auth_enabled, "mode": settings.auth_mode}}
