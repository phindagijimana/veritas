from __future__ import annotations

import logging
from dataclasses import dataclass
from urllib.parse import quote

import requests

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class PennsieveStageResult:
    manifest_url: str
    staged_dataset_path: str
    status: str = "staged"
    message: str = "Pennsieve dataset staged successfully."


class PennsieveClient:
    def stage_dataset(self, *, atlas_dataset_id: str, destination: str, token: str | None = None) -> PennsieveStageResult:
        settings = get_settings()
        safe_id = quote(atlas_dataset_id, safe="")
        manifest_url = f"{settings.pennsieve_base_url.rstrip('/')}{settings.pennsieve_manifest_path_template.format(dataset_id=safe_id)}"
        staged_path = f"{destination}/{atlas_dataset_id}/dataset"

        if settings.atlas_integration_mode == "live" and settings.pennsieve_api_token:
            auth = token or settings.pennsieve_api_token
            try:
                response = requests.get(
                    manifest_url,
                    headers={"Authorization": f"Bearer {auth}", "Accept": "application/json"},
                    timeout=settings.pennsieve_timeout_seconds,
                )
                response.raise_for_status()
                logger.info("Pennsieve manifest fetched for dataset %s (status %s)", atlas_dataset_id, response.status_code)
            except requests.RequestException as exc:
                logger.warning("Pennsieve live manifest fetch failed, falling back to mock paths: %s", exc)

        if settings.atlas_integration_mode == "mock" or not settings.pennsieve_api_token:
            manifest_url = f"{settings.pennsieve_base_url.rstrip('/')}/manifests/{safe_id}.json"

        return PennsieveStageResult(
            manifest_url=manifest_url,
            staged_dataset_path=staged_path,
            message="Pennsieve staging reference resolved (mock or live).",
        )
