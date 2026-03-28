from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_liveness() -> None:
    with TestClient(create_app()) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


def test_ready_readiness() -> None:
    with TestClient(create_app()) as client:
        r = client.get("/ready")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ready"
        assert body["database"] == "ok"


def test_request_id_propagates() -> None:
    with TestClient(create_app()) as client:
        r = client.get("/health", headers={"X-Request-ID": "custom-req-id"})
        assert r.headers.get("X-Request-ID") == "custom-req-id"


def test_request_id_generated() -> None:
    with TestClient(create_app()) as client:
        r = client.get("/health")
        assert r.headers.get("X-Request-ID")


def _admin_headers() -> dict[str, str]:
    return {"X-Internal-Api-Key": "test-internal-key"}


def test_admin_rate_limit_returns_429(monkeypatch) -> None:
    monkeypatch.setenv("ATLAS_ADMIN_RATE_LIMIT_PER_MINUTE", "2")
    from app.core import config as config_module
    from app.db import session as session_module

    config_module.get_settings.cache_clear()
    session_module.clear_engine_cache()
    with TestClient(create_app()) as client:
        assert client.get("/api/v1/admin/grants", headers=_admin_headers()).status_code == 200
        assert client.get("/api/v1/admin/grants", headers=_admin_headers()).status_code == 200
        r = client.get("/api/v1/admin/grants", headers=_admin_headers())
        assert r.status_code == 429
