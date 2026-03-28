"""Production validation edge cases (ATLAS_REQUIRE_VERITAS_CLIENT_SECRET)."""

from __future__ import annotations

import pytest

from app.core.config import Settings, get_settings, validate_production_settings


def _clear() -> None:
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def reset_cache():
    yield
    _clear()


def test_production_fails_when_require_veritas_secret_but_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATLAS_ENV", "production")
    monkeypatch.setenv("ATLAS_DEBUG", "false")
    monkeypatch.setenv("ATLAS_DATABASE_URL", "postgresql+psycopg2://atlas:atlas@127.0.0.1:5432/atlas_dev")
    monkeypatch.setenv("ATLAS_DATABASE_AUTO_CREATE_SCHEMA", "false")
    monkeypatch.setenv("ATLAS_INTERNAL_API_KEY", "strong-internal-key-for-production-use-only")
    monkeypatch.setenv("ATLAS_DEV_BEARER_SECRET", "strong-dev-bearer-secret-for-production-use-only")
    monkeypatch.setenv("ATLAS_ALLOW_FORWARDED_PRINCIPAL", "false")
    monkeypatch.setenv("ATLAS_JWKS_URL", "https://login.example.com/.well-known/jwks.json")
    monkeypatch.setenv("ATLAS_JWT_AUDIENCE", "veritas-atlas")
    monkeypatch.setenv("ATLAS_JWT_ISSUER", "https://login.example.com/")
    monkeypatch.setenv("ATLAS_SECURITY_DEMO_ENABLED", "false")
    monkeypatch.setenv("ATLAS_SEED_DEMO_DATA_ON_STARTUP", "false")
    monkeypatch.setenv("ATLAS_CORS_ORIGINS", "https://app.example.org")
    monkeypatch.setenv("PENNSIEVE_INTEGRATION_ENABLED", "false")
    monkeypatch.setenv("ATLAS_REQUIRE_VERITAS_CLIENT_SECRET", "true")
    monkeypatch.setenv("ATLAS_VERITAS_CLIENT_SECRET", "")

    _clear()
    with pytest.raises(RuntimeError, match="ATLAS_VERITAS_CLIENT_SECRET"):
        validate_production_settings(Settings())


def test_production_passes_when_require_veritas_secret_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATLAS_ENV", "production")
    monkeypatch.setenv("ATLAS_DEBUG", "false")
    monkeypatch.setenv("ATLAS_DATABASE_URL", "postgresql+psycopg2://atlas:atlas@127.0.0.1:5432/atlas_dev")
    monkeypatch.setenv("ATLAS_DATABASE_AUTO_CREATE_SCHEMA", "false")
    monkeypatch.setenv("ATLAS_INTERNAL_API_KEY", "strong-internal-key-for-production-use-only")
    monkeypatch.setenv("ATLAS_DEV_BEARER_SECRET", "strong-dev-bearer-secret-for-production-use-only")
    monkeypatch.setenv("ATLAS_ALLOW_FORWARDED_PRINCIPAL", "false")
    monkeypatch.setenv("ATLAS_JWKS_URL", "https://login.example.com/.well-known/jwks.json")
    monkeypatch.setenv("ATLAS_JWT_AUDIENCE", "veritas-atlas")
    monkeypatch.setenv("ATLAS_JWT_ISSUER", "https://login.example.com/")
    monkeypatch.setenv("ATLAS_SECURITY_DEMO_ENABLED", "false")
    monkeypatch.setenv("ATLAS_SEED_DEMO_DATA_ON_STARTUP", "false")
    monkeypatch.setenv("ATLAS_CORS_ORIGINS", "https://app.example.org")
    monkeypatch.setenv("PENNSIEVE_INTEGRATION_ENABLED", "false")
    monkeypatch.setenv("ATLAS_REQUIRE_VERITAS_CLIENT_SECRET", "true")
    monkeypatch.setenv("ATLAS_VERITAS_CLIENT_SECRET", "matching-veritas-atlas-shared-secret")

    _clear()
    validate_production_settings(Settings())
