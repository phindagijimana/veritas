import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.auth_rate_limit import clear_auth_rate_limit_caches
from app.core.config import get_settings
from app.main import app


@pytest.fixture(autouse=True)
def _reset_auth_rate_limits():
    clear_auth_rate_limit_caches()
    yield
    clear_auth_rate_limit_caches()


def test_login_extra_rate_limit_returns_429(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUTH_LOGIN_RATE_LIMIT", "2/minute")
    monkeypatch.setenv("AUTH_REGISTER_RATE_LIMIT", "")
    get_settings.cache_clear()
    clear_auth_rate_limit_caches()

    client = TestClient(app)
    prefix = get_settings().api_v1_prefix.rstrip("/")
    url = f"{prefix}/auth/login"
    body = {"email": "admin@veritas.local", "password": "admin-password"}

    assert client.post(url, json=body).status_code in (200, 401)
    assert client.post(url, json=body).status_code in (200, 401)
    assert client.post(url, json=body).status_code == 429


def test_register_bucket_independent_of_login(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUTH_LOGIN_RATE_LIMIT", "1/minute")
    monkeypatch.setenv("AUTH_REGISTER_RATE_LIMIT", "5/minute")
    get_settings.cache_clear()
    clear_auth_rate_limit_caches()

    client = TestClient(app)
    prefix = get_settings().api_v1_prefix.rstrip("/")

    assert client.post(f"{prefix}/auth/login", json={"email": "a@b.c", "password": "x"}).status_code in (200, 401)
    assert client.post(f"{prefix}/auth/login", json={"email": "a@b.c", "password": "x"}).status_code == 429

    email = f"t{uuid.uuid4().hex[:12]}@veritas.local"
    r = client.post(
        f"{prefix}/auth/register",
        json={"email": email, "password": "longpassword1", "full_name": "N"},
    )
    assert r.status_code != 429
