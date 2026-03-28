"""Override session DB setup for pure unit tests (no Postgres / alembic)."""

from __future__ import annotations

import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    yield
