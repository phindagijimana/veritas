
from __future__ import annotations

from typing import Any, Dict

from app.schemas.atlas import AtlasSubmissionContext
from app.services.atlas_execution_service import AtlasExecutionService


def build_phase_b_job_submission_payload(
    *,
    request_id: str,
    atlas_dataset_id: str,
    pipeline_id: str | None = None,
    user_id: str | None = None,
) -> Dict[str, Any]:
    """
    Integration helper for the existing job submission layer.

    This function is intended to be called from the real job service before
    Slurm script generation. It prepares Atlas staging and returns extra
    runtime metadata that can be merged into the job record.
    """
    service = AtlasExecutionService()
    bundle = service.prepare_submission(
        AtlasSubmissionContext(
            request_id=request_id,
            atlas_dataset_id=atlas_dataset_id,
            pipeline_id=pipeline_id,
            user_id=user_id,
        )
    )
    return {
        "atlas_staging_id": bundle.atlas_staging_id,
        "staging_status": bundle.staging_status,
        "staged_dataset_path": bundle.staged_dataset_path,
        "staging_credentials_ref": bundle.env.get("ATLAS_STAGING_TOKEN", ""),
        "atlas_manifest_ref": bundle.manifest_url,
        "dataset_access_status": bundle.atlas_approval_status,
        "runtime_preamble": service.build_runtime_preamble(bundle),
        "stage_script_path": bundle.stage_script_path,
        "stage_env_path": bundle.stage_env_path,
    }
