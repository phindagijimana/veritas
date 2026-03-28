"""Application startup: validate config, create schema, seed demo data."""

from __future__ import annotations

import logging

from app.core.config import get_settings, validate_production_settings

logger = logging.getLogger(__name__)
from app.db.base import Base
from app.db.session import get_engine
from app.models import AtlasDataset, AuditEvent, DatasetPermissionGrant, StagingSession  # noqa: F401 — register metadata
from app.services.seed import seed_demo_datasets_if_empty, seed_demo_grants_if_empty


def run_startup() -> None:
    settings = get_settings()
    validate_production_settings(settings)
    if settings.is_production and not (settings.veritas_client_secret or "").strip():
        logger.warning(
            "ATLAS_VERITAS_CLIENT_SECRET is empty; Veritas cannot authenticate with X-Atlas-Client-* headers."
        )

    engine = get_engine()
    if settings.database_auto_create_schema:
        Base.metadata.create_all(bind=engine)

    if settings.seed_demo_data_on_startup:
        from app.db.session import open_session

        db = open_session()
        try:
            seed_demo_datasets_if_empty(db)
            seed_demo_grants_if_empty(db)
        finally:
            db.close()
