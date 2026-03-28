from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.integrations.pennsieve import PennsieveClient
from app.models.dataset import AtlasDataset
from app.models.staging_session import StagingSession

logger = logging.getLogger(__name__)


async def hydrate_staging_after_request(
    db: Session,
    session: StagingSession,
    dataset_row: AtlasDataset,
    settings: Settings,
) -> None:
    """Phase 4: optionally pull manifest file list from Pennsieve; otherwise mark ready."""
    session.transfer_status = "transferring"
    if settings.pennsieve_integration_enabled and dataset_row.pennsieve_package_id:
        client = PennsieveClient(settings)
        files = await client.fetch_package_files(dataset_row.pennsieve_package_id)
        if files:
            session.manifest_files_json = json.dumps(files)
            session.transfer_status = "ready"
            session.transfer_log = None
        else:
            session.transfer_status = "failed"
            session.transfer_log = "Pennsieve package listing returned no file entries"
            logger.info("No files parsed for package %s", dataset_row.pennsieve_package_id)
    else:
        session.transfer_status = "ready"
        session.transfer_log = None

    db.add(session)
    db.flush()
