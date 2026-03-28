
from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.core.config import get_settings
from app.schemas.atlas import (
    AtlasExecutionBundle,
    AtlasStagingManifest,
    AtlasStagingRequest,
    AtlasStagingResponse,
    AtlasSubmissionContext,
)
from app.services.atlas_client import build_atlas_client
from app.services.dataset_staging_service import DatasetStagingService


class AtlasExecutionService:
    """
    Phase B service that connects Atlas approvals/staging to HPC runtime preparation.
    It prepares a job-scoped stage script and env file that can be invoked before
    the pipeline runtime starts.
    """

    def __init__(
        self,
        atlas_client: Optional[object] = None,
        staging_service: Optional[DatasetStagingService] = None,
    ) -> None:
        self.atlas_client = atlas_client or build_atlas_client()
        self.staging_service = staging_service or DatasetStagingService()

    def prepare_submission(self, context: AtlasSubmissionContext) -> AtlasExecutionBundle:
        staging_request = AtlasStagingRequest(
            request_id=context.request_id,
            atlas_dataset_id=context.atlas_dataset_id,
            user_id=context.user_id,
            pipeline_id=context.pipeline_id,
            purpose="benchmark_validation",
        )
        staging = self.atlas_client.request_staging(staging_request)

        if staging.status.lower() not in {"approved", "credentials_issued", "ready", "staged"}:
            return AtlasExecutionBundle(
                atlas_dataset_id=context.atlas_dataset_id,
                atlas_staging_id=staging.atlas_staging_id,
                atlas_approval_status=staging.status,
                staging_status=staging.status,
                source=staging.source,
                manifest_url=staging.manifest_url,
                message="Atlas approval exists but staging is not ready yet.",
            )

        manifest = self._safe_manifest(staging)
        plan = self.staging_service.build_staging_plan(
            request_id=context.request_id,
            atlas_dataset_id=context.atlas_dataset_id,
            staging=staging,
            manifest=manifest,
        )
        self.staging_service.ensure_local_dirs(plan)
        destination_root = Path(plan.destination_root)
        cfg = get_settings()
        stage_script_path = destination_root / cfg.atlas_stage_script_name
        stage_env_path = destination_root / cfg.atlas_stage_env_filename

        stage_script_path.write_text(plan.stage_script)
        stage_script_path.chmod(0o755)
        stage_env_path.write_text("\n".join(f"{k}={v}" for k, v in plan.env.items()) + "\n")

        return AtlasExecutionBundle(
            atlas_dataset_id=context.atlas_dataset_id,
            atlas_staging_id=staging.atlas_staging_id,
            atlas_approval_status="approved",
            staging_status="prepared",
            source=staging.source,
            staged_dataset_path=plan.staged_dataset_path,
            stage_script_path=str(stage_script_path),
            stage_env_path=str(stage_env_path),
            manifest_url=staging.manifest_url,
            message="Atlas staging plan prepared for HPC execution.",
            env=plan.env,
        )

    def build_runtime_preamble(self, bundle: AtlasExecutionBundle) -> str:
        if not bundle.stage_script_path or not bundle.stage_env_path:
            return 'echo "Atlas staging not ready yet"; exit 1'
        return f"""set -euo pipefail
source "{bundle.stage_env_path}"
bash "{bundle.stage_script_path}"
export VERITAS_STAGED_DATASET_PATH="{bundle.staged_dataset_path}"
echo "Atlas dataset staged into $VERITAS_STAGED_DATASET_PATH"
"""

    def _safe_manifest(self, staging: AtlasStagingResponse) -> AtlasStagingManifest:
        if staging.manifest_url:
            return self.atlas_client.get_staging_manifest(staging.atlas_staging_id)
        return AtlasStagingManifest(
            atlas_staging_id=staging.atlas_staging_id,
            atlas_dataset_id=staging.atlas_dataset_id,
            files=[],
            source=staging.source,
        )
