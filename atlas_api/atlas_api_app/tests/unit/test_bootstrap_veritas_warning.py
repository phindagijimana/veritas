"""Startup warning when Veritas client secret is unset in production."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def test_run_startup_warns_when_veritas_secret_empty_in_production(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("WARNING")
    settings = MagicMock()
    settings.is_production = True
    settings.veritas_client_secret = ""
    settings.database_auto_create_schema = False
    settings.seed_demo_data_on_startup = False

    with patch("app.bootstrap.get_settings", return_value=settings), patch(
        "app.bootstrap.validate_production_settings"
    ), patch("app.bootstrap.get_engine") as ge:
        ge.return_value = MagicMock()
        from app.bootstrap import run_startup

        run_startup()

    assert any(
        "ATLAS_VERITAS_CLIENT_SECRET" in r.message and "Veritas" in r.message for r in caplog.records
    )
