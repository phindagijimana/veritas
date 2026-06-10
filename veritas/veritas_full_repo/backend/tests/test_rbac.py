"""RBAC: admin-only writes reject non-admin tokens; register cannot escalate."""
from __future__ import annotations

from app.core.config import get_settings
from app.services.auth_service import AuthService


def _token(role: str, email: str | None = None) -> str:
    email = email or f"{role}@veritas.local"
    return AuthService.build().create_access_token(email, role=role, full_name=role.title())


def test_admin_endpoints_reject_researcher_token(monkeypatch, client):
    secret = "rbac-test-secret-key-32bytes-min!!"
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_SECRET_KEY", secret)
    get_settings.cache_clear()

    headers = {"Authorization": f"Bearer {_token('researcher')}"}

    # pipeline create
    r = client.post(
        "/api/v1/pipelines",
        headers=headers,
        json={"name": "x", "title": "x", "image": "img:0", "modality": "MRI"},
    )
    assert r.status_code == 403, r.text

    # dataset create
    r = client.post("/api/v1/datasets", headers=headers, json={"code": "X", "name": "x"})
    assert r.status_code == 403, r.text

    # hpc connect
    r = client.post(
        "/api/v1/hpc/connect",
        headers=headers,
        json={"hostname": "h", "username": "u", "port": 22},
    )
    assert r.status_code == 403, r.text

    # leaderboard push
    r = client.post("/api/v1/leaderboard/push/REQ-2002", headers=headers, json={"consented": True})
    assert r.status_code == 403, r.text


def test_admin_endpoints_accept_admin_token(monkeypatch, client):
    secret = "rbac-test-secret-key-32bytes-min!!"
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_SECRET_KEY", secret)
    get_settings.cache_clear()

    headers = {"Authorization": f"Bearer {_token('admin')}"}

    # admin token must not be blocked by RBAC (status may be 200/400/404 depending on body, but never 403)
    r = client.post(
        "/api/v1/pipelines",
        headers=headers,
        json={"name": "rbac-test", "title": "RBAC test", "image": "img:0", "modality": "MRI"},
    )
    assert r.status_code != 403, r.text


def test_register_cannot_escalate_to_admin(monkeypatch, client):
    secret = "rbac-test-secret-key-32bytes-min!!"
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_SECRET_KEY", secret)
    get_settings.cache_clear()

    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "evil@veritas.local",
            "password": "hunter2hunter2",
            "full_name": "Mallory",
            "role": "admin",
        },
    )
    # registration may succeed (200) or conflict if a previous test created it (409)
    assert r.status_code in (200, 409), r.text
    if r.status_code == 200:
        assert r.json()["user"]["role"] == "researcher"
