"""Application startup: validate config, create schema, seed demo data."""

from __future__ import annotations

from app.core.config import get_settings, validate_production_settings
from app.db.base import Base
from app.db.session import get_engine
from app.models import AtlasDataset, DatasetPermissionGrant, StagingSession  # noqa: F401 — register metadata
from app.services.seed import seed_demo_datasets_if_empty, seed_demo_grants_if_empty


def run_startup() -> None:
    settings = get_settings()
    validate_production_settings(settings)

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
