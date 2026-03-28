from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from app.core.config import get_settings
from app.services.pennsieve_client import PennsieveClient
from app.schemas.atlas_phase_c import StagingStatusResponse

@dataclass
class AtlasPhaseCBundle:
    request_id: str
    atlas_dataset_id: str
    atlas_staging_id: str
    status: str
    approval_status: str
    staged_dataset_path: str | None = None
    manifest_url: str | None = None
    message: str | None = None

class AtlasPhaseCService:
    def __init__(self, pennsieve_client: Optional[PennsieveClient] = None):
        self.pennsieve_client = pennsieve_client or PennsieveClient()

    def prepare_and_stage(self, *, request_id: str, atlas_dataset_id: str, approval_status: str = "approved") -> AtlasPhaseCBundle:
        if approval_status != "approved":
            return AtlasPhaseCBundle(
                request_id=request_id,
                atlas_dataset_id=atlas_dataset_id,
                atlas_staging_id=f"AST-{request_id}",
                status="approval_pending",
                approval_status=approval_status,
                message="Atlas approval is still pending.",
            )
        staging_root = get_settings().dataset_staging_root.rstrip("/")
        staged = self.pennsieve_client.stage_dataset(
            atlas_dataset_id=atlas_dataset_id,
            destination=f"{staging_root}/{request_id}",
            token=get_settings().pennsieve_api_token or None,
        )
        return AtlasPhaseCBundle(
            request_id=request_id,
            atlas_dataset_id=atlas_dataset_id,
            atlas_staging_id=f"AST-{request_id}",
            status=staged.status,
            approval_status="approved",
            staged_dataset_path=staged.staged_dataset_path,
            manifest_url=staged.manifest_url,
            message=staged.message,
        )

    def to_response(self, bundle: AtlasPhaseCBundle) -> StagingStatusResponse:
        return StagingStatusResponse(
            request_id=bundle.request_id,
            atlas_dataset_id=bundle.atlas_dataset_id,
            atlas_staging_id=bundle.atlas_staging_id,
            status=bundle.status,
            approval_status=bundle.approval_status,
            staged_dataset_path=bundle.staged_dataset_path,
            manifest_url=bundle.manifest_url,
            message=bundle.message,
        )
