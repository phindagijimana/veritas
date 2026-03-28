from __future__ import annotations

from jose import jwt

from app.core.config import get_settings
from app.services.auth_service import AuthService


def test_access_token_encodes_as_signed_jwt(monkeypatch):
    secret = "unit-test-jwt-secret-key-32bytes!!"
    monkeypatch.setenv("AUTH_SECRET_KEY", secret)
    get_settings.cache_clear()
    token = AuthService.build().create_access_token("user@veritas.local", role="researcher", full_name="U")
    payload = jwt.decode(token, secret, algorithms=["HS256"])
    assert payload["sub"] == "user@veritas.local"
    assert payload["role"] == "researcher"
    assert payload["full_name"] == "U"
    assert "exp" in payload


def test_me_with_bearer_succeeds_when_auth_enabled(monkeypatch, client):
    secret = "integration-test-secret-key-32b!!!"
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_SECRET_KEY", secret)
    get_settings.cache_clear()
    token = AuthService.build().create_access_token("admin@veritas.local", role="admin")
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["email"] == "admin@veritas.local"
    assert data["role"] == "admin"
