"""Fresh SQLite per test and reload cached settings/engine."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _atlas_test_database(tmp_path, monkeypatch):
    db_path = tmp_path / "atlas_test.db"
    monkeypatch.setenv("ATLAS_DATABASE_URL", f"sqlite:///{db_path}")

    from app.core import config as config_module
    from app.db import session as session_module

    config_module.get_settings.cache_clear()
    session_module.clear_engine_cache()

    yield

    config_module.get_settings.cache_clear()
    session_module.clear_engine_cache()
