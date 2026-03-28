import jwt
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


def make_token(sub: str, roles: list[str]) -> str:
    settings = get_settings()
    return jwt.encode(
        {
            "sub": sub,
            "roles": roles,
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
        },
        settings.dev_bearer_secret,
        algorithm="HS256",
    )


def test_bearer_token_allows_me_endpoint() -> None:
    token = make_token("user-123", ["researcher"])
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/security-demo/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["principal_id"] == "user-123"


def test_internal_api_key_allows_admin_endpoint() -> None:
    settings = get_settings()
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/security-demo/admin", headers={"X-Internal-Api-Key": settings.internal_api_key})
    assert response.status_code == 200
