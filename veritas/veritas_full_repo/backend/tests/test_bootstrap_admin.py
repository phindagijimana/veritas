"""GET /auth/bootstrap-status + POST /auth/bootstrap-admin.

These let the UI LoginGate detect a fresh production DB (zero admins) and
offer a one-shot admin-creation form instead of the login form.
"""
from __future__ import annotations

import pytest

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.user import User


@pytest.fixture
def auth_on(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_SECRET_KEY", "bootstrap-test-secret-32bytes-min!")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _drop_all_admins() -> None:
    """Remove every existing admin so bootstrap-status reports True.

    Sibling tests may have seeded admins (the dev seed in 0014_users always
    runs in CI mode); this isolates the bootstrap scenario.
    """
    db = SessionLocal()
    try:
        db.query(User).filter(User.role == "admin").delete()
        db.commit()
    finally:
        db.close()


def test_bootstrap_status_auth_off(monkeypatch, client):
    monkeypatch.delenv("AUTH_ENABLED", raising=False)
    get_settings.cache_clear()
    r = client.get("/api/v1/auth/bootstrap-status")
    assert r.status_code == 200
    body = r.json()["data"]
    assert body["auth_enabled"] is False
    assert body["needs_bootstrap"] is False


def test_bootstrap_status_no_admins_says_yes(auth_on, client):
    _drop_all_admins()
    r = client.get("/api/v1/auth/bootstrap-status")
    assert r.status_code == 200
    body = r.json()["data"]
    assert body["auth_enabled"] is True
    assert body["needs_bootstrap"] is True


def test_bootstrap_admin_creates_first_admin(auth_on, client):
    _drop_all_admins()
    r = client.post(
        "/api/v1/auth/bootstrap-admin",
        json={
            "email": "first-admin@veritas.local",
            "password": "very-strong-password-1!",
            "full_name": "First Admin",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user"]["role"] == "admin"
    assert body["access_token"]

    # status now flips to false; cannot run bootstrap-admin twice.
    r2 = client.get("/api/v1/auth/bootstrap-status")
    assert r2.json()["data"]["needs_bootstrap"] is False

    r3 = client.post(
        "/api/v1/auth/bootstrap-admin",
        json={"email": "intruder@veritas.local", "password": "also-strong-pw-1!"},
    )
    assert r3.status_code == 409
    assert "admin already exists" in r3.json()["detail"].lower()


def test_bootstrap_admin_rejects_weak_password(auth_on, client):
    _drop_all_admins()
    r = client.post(
        "/api/v1/auth/bootstrap-admin",
        json={"email": "weak@veritas.local", "password": "short"},
    )
    assert r.status_code == 400, r.text
    assert "12 characters" in r.json()["detail"]


def test_bootstrap_admin_refuses_when_auth_off(monkeypatch, client):
    monkeypatch.delenv("AUTH_ENABLED", raising=False)
    get_settings.cache_clear()
    r = client.post(
        "/api/v1/auth/bootstrap-admin",
        json={"email": "x@veritas.local", "password": "very-strong-pw-1!"},
    )
    assert r.status_code == 409, r.text
    assert "auth_enabled" in r.json()["detail"].lower() or "auth is false" in r.json()["detail"].lower()
