"""Tests default to PostgreSQL (see README). Set ATLAS_USE_SQLITE_TESTS=1 for SQLite without Docker."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import text

_ROOT = Path(__file__).resolve().parents[1]

_USE_SQLITE = os.environ.get("ATLAS_USE_SQLITE_TESTS", "").lower() in ("1", "true", "yes")

if _USE_SQLITE:
    _fd, _SQLITE_PATH = tempfile.mkstemp(suffix="atlas_test.db")
    os.close(_fd)
    os.environ["ATLAS_DATABASE_URL"] = f"sqlite:///{_SQLITE_PATH}"
    os.environ.setdefault("ATLAS_DATABASE_AUTO_CREATE_SCHEMA", "false")
else:
    os.environ.setdefault(
        "ATLAS_DATABASE_URL",
        "postgresql+psycopg2://atlas:atlas@127.0.0.1:5432/atlas_test",
    )
    os.environ.setdefault("ATLAS_DATABASE_AUTO_CREATE_SCHEMA", "false")


@pytest.fixture(scope="session", autouse=True)
def _atlas_apply_migrations(request: pytest.FixtureRequest) -> None:
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=_ROOT,
        check=True,
        env=os.environ.copy(),
    )

    if _USE_SQLITE:

        def _unlink() -> None:
            try:
                os.unlink(_SQLITE_PATH)
            except OSError:
                pass

        request.addfinalizer(_unlink)


@pytest.fixture(autouse=True)
def _atlas_test_isolation() -> Iterator[None]:
    """Clear app tables before each test."""
    from app.core import config as config_module
    from app.db import session as session_module
    from app.db.session import get_engine

    config_module.get_settings.cache_clear()
    session_module.clear_engine_cache()

    engine = get_engine()
    url = os.environ.get("ATLAS_DATABASE_URL", "")
    with engine.begin() as conn:
        if url.startswith("sqlite"):
            for table in (
                "atlas_audit_events",
                "dataset_permission_grants",
                "atlas_staging_sessions",
                "atlas_datasets",
            ):
                conn.execute(text(f"DELETE FROM {table}"))
        else:
            conn.execute(
                text(
                    """
                    TRUNCATE TABLE atlas_audit_events, dataset_permission_grants,
                    atlas_staging_sessions, atlas_datasets
                    RESTART IDENTITY CASCADE
                    """
                )
            )

    yield

    config_module.get_settings.cache_clear()
    session_module.clear_engine_cache()
