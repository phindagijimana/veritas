"""Admin Pennsieve health-check endpoint: mock mode, missing-token, live OK, live 401."""
from __future__ import annotations

from unittest.mock import patch

import pytest
import requests

from app.core.config import get_settings
from app.services.auth_service import AuthService


def _admin_jwt() -> str:
    return AuthService.build().create_access_token("pennhealth-admin@veritas.local", role="admin")


@pytest.fixture
def auth_on(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_SECRET_KEY", "penn-health-secret-key-32-bytes!!!")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_requires_admin(auth_on, client):
    r = client.get("/api/v1/admin/integrations/pennsieve/health")
    assert r.status_code in (401, 403), r.text


def test_mock_mode_is_ok_without_outbound_call(auth_on, client, monkeypatch):
    monkeypatch.setenv("ATLAS_INTEGRATION_MODE", "mock")
    get_settings.cache_clear()
    with patch("app.api.routes.admin.requests.get") as g:
        r = client.get(
            "/api/v1/admin/integrations/pennsieve/health",
            headers={"Authorization": f"Bearer {_admin_jwt()}"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["integration"] == "pennsieve"
        assert body["mode"] == "mock"
        assert body["ok"] is True
        g.assert_not_called()


def test_live_without_token_fails_cleanly(auth_on, client, monkeypatch):
    monkeypatch.setenv("ATLAS_INTEGRATION_MODE", "live")
    monkeypatch.setenv("PENNSIEVE_API_TOKEN", "")
    get_settings.cache_clear()
    r = client.get(
        "/api/v1/admin/integrations/pennsieve/health",
        headers={"Authorization": f"Bearer {_admin_jwt()}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is False
    assert "PENNSIEVE_API_TOKEN" in body["detail"]


def test_live_with_token_calls_pennsieve_user(auth_on, client, monkeypatch):
    monkeypatch.setenv("ATLAS_INTEGRATION_MODE", "live")
    monkeypatch.setenv("PENNSIEVE_API_TOKEN", "test-token-not-real")
    monkeypatch.setenv("PENNSIEVE_BASE_URL", "https://api.pennsieve.example")
    get_settings.cache_clear()

    class _FakeResp:
        status_code = 200

    with patch("app.api.routes.admin.requests.get", return_value=_FakeResp()) as g:
        r = client.get(
            "/api/v1/admin/integrations/pennsieve/health",
            headers={"Authorization": f"Bearer {_admin_jwt()}"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True
        assert "200" in body["detail"]
        url, _ = g.call_args[0], g.call_args[1]
        assert url[0].startswith("https://api.pennsieve.example/")
        assert url[0].endswith("/user")


def test_live_with_bad_token_reports_401_clearly(auth_on, client, monkeypatch):
    monkeypatch.setenv("ATLAS_INTEGRATION_MODE", "live")
    monkeypatch.setenv("PENNSIEVE_API_TOKEN", "rotated-out-token")
    get_settings.cache_clear()

    class _FakeResp:
        status_code = 401

    with patch("app.api.routes.admin.requests.get", return_value=_FakeResp()):
        r = client.get(
            "/api/v1/admin/integrations/pennsieve/health",
            headers={"Authorization": f"Bearer {_admin_jwt()}"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is False
        assert "401" in body["detail"]
        assert "PENNSIEVE_API_TOKEN" in body["detail"]


def test_live_network_error_does_not_500(auth_on, client, monkeypatch):
    monkeypatch.setenv("ATLAS_INTEGRATION_MODE", "live")
    monkeypatch.setenv("PENNSIEVE_API_TOKEN", "tok")
    get_settings.cache_clear()
    with patch(
        "app.api.routes.admin.requests.get",
        side_effect=requests.ConnectionError("name resolution failed"),
    ):
        r = client.get(
            "/api/v1/admin/integrations/pennsieve/health",
            headers={"Authorization": f"Bearer {_admin_jwt()}"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is False
        assert "name resolution failed" in body["detail"]
