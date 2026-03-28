from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.integrations.pennsieve import PennsieveClient
from app.models.dataset import AtlasDataset
from app.models.staging_session import StagingSession
from app.security.models import Principal
from app.services.audit import record_audit

logger = logging.getLogger(__name__)


async def _resolve_manifest_files(
    client: PennsieveClient,
    package_id: str,
    settings: Settings,
) -> tuple[Optional[list[dict[str, Any]]], str]:
    """Try download-manifest API first, then package GET heuristic."""
    manifest = await client.fetch_download_manifest(package_id)
    if manifest:
        return manifest, "download_manifest"
    fallback = await client.fetch_package_files(package_id)
    if fallback:
        return fallback, "package_get_heuristic"
    return None, "none"


async def hydrate_staging_after_request(
    db: Session,
    session: StagingSession,
    dataset_row: AtlasDataset,
    settings: Settings,
    principal: Principal,
) -> None:
    """
    Pull manifest via Pennsieve (with retries), optional export job id, audit trail.
    """
    session.transfer_status = "transferring"
    db.add(session)
    db.flush()

    if not settings.pennsieve_integration_enabled or not dataset_row.pennsieve_package_id:
        session.transfer_status = "ready"
        session.transfer_log = None
        record_audit(
            db,
            actor=principal,
            action="staging.manifest",
            resource_type="staging_session",
            resource_id=session.staging_id,
            detail={"result": "ready", "reason": "no_pennsieve_package"},
            staging_id=session.staging_id,
        )
        db.commit()
        return

    client = PennsieveClient(settings)
    export_ref = await client.export_package_job(dataset_row.pennsieve_package_id)
    if export_ref:
        session.pennsieve_export_job_id = export_ref

    max_retries = max(1, settings.staging_max_retries)
    backoff = max(0.1, settings.staging_retry_backoff_seconds)
    files: list[dict[str, Any]] | None = None
    source = "none"
    last_err = ""

    for attempt in range(max_retries):
        session.retry_count = attempt
        session.last_attempt_at = datetime.now(timezone.utc)
        db.add(session)
        db.flush()

        try:
            files, source = await _resolve_manifest_files(client, dataset_row.pennsieve_package_id, settings)
        except Exception as exc:  # pragma: no cover - defensive
            last_err = str(exc)
            logger.warning("staging manifest attempt %s failed: %s", attempt, exc)

        if files:
            break
        if attempt < max_retries - 1:
            await asyncio.sleep(backoff * (attempt + 1))

    if files:
        session.manifest_files_json = json.dumps(files)
        session.transfer_status = "ready"
        session.transfer_log = json.dumps({"source": source, "attempts": session.retry_count + 1})
        record_audit(
            db,
            actor=principal,
            action="staging.manifest.ready",
            resource_type="staging_session",
            resource_id=session.staging_id,
            detail={"source": source, "file_count": len(files), "export_job": session.pennsieve_export_job_id},
            staging_id=session.staging_id,
        )
    else:
        session.transfer_status = "failed"
        session.transfer_log = json.dumps(
            {"error": "no_manifest_files", "last": last_err, "attempts": max_retries, "source": source}
        )
        record_audit(
            db,
            actor=principal,
            action="staging.manifest.failed",
            resource_type="staging_session",
            resource_id=session.staging_id,
            detail={"package_id": dataset_row.pennsieve_package_id},
            staging_id=session.staging_id,
        )

    db.add(session)
    db.commit()
