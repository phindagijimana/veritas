"""Personal access tokens: create/list/revoke + PAT-based authentication."""
from __future__ import annotations

import pytest

from app.core.config import get_settings
from app.services.auth_service import AuthService


def _jwt(role: str = "admin", email: str | None = None) -> str:
    email = email or f"{role}@veritas.local"
    return AuthService.build().create_access_token(email, role=role, full_name=role.title())


@pytest.fixture
def auth_on(monkeypatch):
    secret = "pat-test-secret-key-32bytes-minim!"
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_SECRET_KEY", secret)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_create_returns_plaintext_token_once(auth_on, client):
    r = client.post(
        "/api/v1/auth/tokens",
        headers={"Authorization": f"Bearer {_jwt()}"},
        json={"label": "ci-laptop"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["token"].startswith("veritas_pat_")
    assert body["data"]["label"] == "ci-laptop"
    assert body["data"]["prefix"].startswith("veritas_pat_")
    assert "token" not in body["data"]  # plaintext is NOT in the persisted item


def test_list_omits_plaintext_token(auth_on, client):
    # seed one token
    client.post(
        "/api/v1/auth/tokens",
        headers={"Authorization": f"Bearer {_jwt(email='list-test@veritas.local')}"},
        json={"label": "list-test"},
    )
    r = client.get(
        "/api/v1/auth/tokens",
        headers={"Authorization": f"Bearer {_jwt(email='list-test@veritas.local')}"},
    )
    assert r.status_code == 200, r.text
    items = r.json()["data"]
    assert len(items) >= 1
    sample = items[0]
    assert "token" not in sample
    assert sample["prefix"].startswith("veritas_pat_")


def test_pat_authenticates_protected_endpoint(auth_on, client):
    create = client.post(
        "/api/v1/auth/tokens",
        headers={"Authorization": f"Bearer {_jwt(email='pat-auth@veritas.local')}"},
        json={"label": "pat-auth"},
    )
    plaintext = create.json()["token"]

    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {plaintext}"})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["email"] == "pat-auth@veritas.local"


def test_pat_cannot_mint_more_pats(auth_on, client):
    create = client.post(
        "/api/v1/auth/tokens",
        headers={"Authorization": f"Bearer {_jwt(email='pat-pivot@veritas.local')}"},
        json={"label": "first"},
    )
    plaintext = create.json()["token"]

    # Use the PAT to try to create another PAT — must be refused (403).
    r = client.post(
        "/api/v1/auth/tokens",
        headers={"Authorization": f"Bearer {plaintext}"},
        json={"label": "leaked-pivot"},
    )
    assert r.status_code == 403, r.text


def test_revoke_invalidates_token(auth_on, client):
    create = client.post(
        "/api/v1/auth/tokens",
        headers={"Authorization": f"Bearer {_jwt(email='revoke-test@veritas.local')}"},
        json={"label": "to-revoke"},
    )
    body = create.json()
    plaintext = body["token"]
    token_id = body["data"]["id"]

    # Works before revoke
    pre = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {plaintext}"})
    assert pre.status_code == 200, pre.text

    # Revoke via owner JWT
    rev = client.delete(
        f"/api/v1/auth/tokens/{token_id}",
        headers={"Authorization": f"Bearer {_jwt(email='revoke-test@veritas.local')}"},
    )
    assert rev.status_code == 204, rev.text

    # Now rejects with 401
    post = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {plaintext}"})
    assert post.status_code == 401, post.text


def test_revoke_404_when_token_belongs_to_other_user(auth_on, client):
    # User A creates a token
    create = client.post(
        "/api/v1/auth/tokens",
        headers={"Authorization": f"Bearer {_jwt(email='alice@veritas.local')}"},
        json={"label": "alice-only"},
    )
    token_id = create.json()["data"]["id"]

    # User B tries to revoke it — must see 404 (not 403 — we don't leak existence)
    r = client.delete(
        f"/api/v1/auth/tokens/{token_id}",
        headers={"Authorization": f"Bearer {_jwt(email='bob@veritas.local')}"},
    )
    assert r.status_code == 404, r.text
