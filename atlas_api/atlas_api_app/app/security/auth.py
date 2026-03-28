from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import jwt
from fastapi import Header, HTTPException, status
from jwt import PyJWKClient

from app.core.config import get_settings
from app.core.enums import PrincipalType
from app.security.models import Principal


class AuthError(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_401_UNAUTHORIZED) -> None:
        super().__init__(status_code=status_code, detail=detail)


@dataclass
class BearerTokenPayload:
    sub: str
    roles: set[str]
    claims: dict[str, Any]


@lru_cache(maxsize=1)
def get_jwks_client() -> PyJWKClient:
    settings = get_settings()
    return PyJWKClient(settings.jwks_url)


def _decode_dev_bearer(token: str) -> BearerTokenPayload:
    settings = get_settings()
    claims = jwt.decode(
        token,
        settings.dev_bearer_secret,
        algorithms=["HS256"],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
    )
    roles = set(claims.get("roles", []))
    return BearerTokenPayload(sub=str(claims["sub"]), roles=roles, claims=claims)


def _decode_oidc_bearer(token: str) -> BearerTokenPayload:
    settings = get_settings()
    jwks_client = get_jwks_client()
    signing_key = jwks_client.get_signing_key_from_jwt(token)
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256", "ES256"],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
        options={"require": ["sub", "iss", "aud"]},
    )
    roles = set(claims.get("roles", claims.get("groups", [])))
    return BearerTokenPayload(sub=str(claims["sub"]), roles=roles, claims=claims)


def build_internal_principal() -> Principal:
    return Principal(
        principal_id="atlas-internal",
        principal_type=PrincipalType.INTERNAL,
        roles={"admin", "service"},
        claims={"internal": True},
        auth_source="internal_api_key",
    )


def verify_internal_api_key(x_internal_api_key: str | None) -> Principal | None:
    if not x_internal_api_key:
        return None
    settings = get_settings()
    if x_internal_api_key != settings.internal_api_key:
        raise AuthError("Invalid internal API key")
    return build_internal_principal()


def verify_veritas_service_headers(
    x_atlas_client_id: str | None,
    x_atlas_client_secret: str | None,
) -> Principal | None:
    """Optional service auth for Veritas AtlasClient (X-Atlas-Client-* headers)."""
    settings = get_settings()
    secret = (settings.veritas_client_secret or "").strip()
    if not secret:
        return None
    if not x_atlas_client_id and not x_atlas_client_secret:
        return None
    if not x_atlas_client_id or not x_atlas_client_secret:
        raise AuthError("Both X-Atlas-Client-Id and X-Atlas-Client-Secret are required for Veritas service auth")

    if x_atlas_client_id != settings.veritas_client_id:
        raise AuthError("Invalid Veritas Atlas client id")
    if x_atlas_client_secret != secret:
        raise AuthError("Invalid Veritas Atlas client secret")

    return Principal(
        principal_id="veritas-service",
        principal_type=PrincipalType.INTERNAL,
        roles={"service"},
        claims={"veritas_client": True},
        auth_source="veritas_headers",
    )


def verify_bearer_token(authorization: str | None) -> Principal | None:
    if not authorization:
        return None
    if not authorization.lower().startswith("bearer "):
        raise AuthError("Authorization header must use Bearer scheme")

    token = authorization.split(" ", 1)[1].strip()
    settings = get_settings()

    try:
        if settings.use_dev_jwt:
            payload = _decode_dev_bearer(token)
        else:
            payload = _decode_oidc_bearer(token)
    except Exception as exc:  # pragma: no cover - exact jwt failures depend on backend
        raise AuthError(f"Bearer token validation failed: {exc}") from exc

    return Principal(
        principal_id=payload.sub,
        principal_type=PrincipalType.USER,
        roles=payload.roles,
        claims=payload.claims,
        auth_source="bearer",
    )


async def resolve_principal(
    authorization: str | None = Header(default=None),
    x_internal_api_key: str | None = Header(default=None),
    x_atlas_client_id: str | None = Header(default=None),
    x_atlas_client_secret: str | None = Header(default=None),
    x_principal_id: str | None = Header(default=None),
    x_principal_type: str | None = Header(default=None),
    x_principal_roles: str | None = Header(default=None),
) -> Principal:
    internal = verify_internal_api_key(x_internal_api_key)
    if internal is not None:
        return internal

    veritas = verify_veritas_service_headers(x_atlas_client_id, x_atlas_client_secret)
    if veritas is not None:
        return veritas

    bearer = verify_bearer_token(authorization)
    if bearer is not None:
        return bearer

    if x_principal_id and x_principal_type:
        if not get_settings().allow_forwarded_principal:
            raise AuthError("Forwarded principal headers are disabled; use Bearer or internal API key")
        roles = {r.strip() for r in (x_principal_roles or "").split(",") if r.strip()}
        try:
            principal_type = PrincipalType(x_principal_type)
        except ValueError as exc:
            raise AuthError("Invalid X-Principal-Type header") from exc
        return Principal(
            principal_id=x_principal_id,
            principal_type=principal_type,
            roles=roles,
            claims={},
            auth_source="header-forwarded",
        )

    raise AuthError("Authentication required")
