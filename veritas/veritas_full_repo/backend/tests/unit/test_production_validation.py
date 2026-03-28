"""Tests for validate_production_settings (go-live guardrails)."""

from __future__ import annotations

import pytest

from app.core.config import Settings, get_settings, validate_production_settings


def _clear_settings_cache() -> None:
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def reset_settings_cache():
    yield
    _clear_settings_cache()


def test_production_live_atlas_url_rejects_example_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://veritas:veritas@127.0.0.1:5433/veritas")
    monkeypatch.setenv("DATABASE_AUTO_CREATE_SCHEMA", "false")
    monkeypatch.setenv("SEED_DEMO_DATA_ON_STARTUP", "false")
    monkeypatch.setenv("HPC_MODE", "mock")
    monkeypatch.setenv("ATLAS_INTEGRATION_MODE", "live")
    monkeypatch.setenv("ATLAS_API_BASE_URL", "https://atlas.example.org/api/v1")
    monkeypatch.setenv("ATLAS_API_CLIENT_SECRET", "real-production-secret-not-placeholder")

    _clear_settings_cache()
    settings = Settings()
    with pytest.raises(RuntimeError, match="ATLAS_API_BASE_URL"):
        validate_production_settings(settings)


def test_production_live_atlas_url_accepts_real_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://veritas:veritas@127.0.0.1:5433/veritas")
    monkeypatch.setenv("DATABASE_AUTO_CREATE_SCHEMA", "false")
    monkeypatch.setenv("SEED_DEMO_DATA_ON_STARTUP", "false")
    monkeypatch.setenv("HPC_MODE", "mock")
    monkeypatch.setenv("ATLAS_INTEGRATION_MODE", "live")
    monkeypatch.setenv("ATLAS_API_BASE_URL", "https://atlas.prod.hospital.org/api/v1")
    monkeypatch.setenv("ATLAS_API_CLIENT_SECRET", "real-production-secret-not-placeholder")

    _clear_settings_cache()
    settings = Settings()
    validate_production_settings(settings)
