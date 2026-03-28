from __future__ import annotations

from app.schemas.atlas import AtlasStagingManifest, AtlasStagingResponse
from app.services.dataset_staging_service import DatasetStagingService


def test_build_staging_plan_contains_expected_env():
    staging = AtlasStagingResponse(
        atlas_staging_id="STAGE-1",
        atlas_dataset_id="DS-HS-001",
        status="approved",
        token="short-lived-token",
        manifest_url="https://atlas.example.org/manifests/STAGE-1",
        expires_at="2026-03-10T12:00:00Z",
        source="pennsieve",
    )
    manifest = AtlasStagingManifest(
        atlas_staging_id="STAGE-1",
        atlas_dataset_id="DS-HS-001",
        files=[{"path": "sub-001/anat/sub-001_T1w.nii.gz"}],
        source="pennsieve",
    )

    service = DatasetStagingService(staging_root="/tmp/veritas-staging")
    plan = service.build_staging_plan(
        request_id="REQ-1001",
        atlas_dataset_id="DS-HS-001",
        staging=staging,
        manifest=manifest,
    )

    assert plan.atlas_dataset_id == "DS-HS-001"
    assert plan.atlas_staging_id == "STAGE-1"
    assert plan.env["ATLAS_STAGING_TOKEN"] == "short-lived-token"
    assert plan.staged_dataset_path.endswith("/REQ-1001/DS-HS-001/dataset")
    assert "Dataset staged successfully" in plan.stage_script


def test_build_stage_script_fails_without_token_reference():
    staging = AtlasStagingResponse(
        atlas_staging_id="STAGE-2",
        atlas_dataset_id="DS-FCD-001",
        status="approved",
        token=None,
        manifest_url=None,
        source="pennsieve",
    )
    manifest = AtlasStagingManifest(
        atlas_staging_id="STAGE-2",
        atlas_dataset_id="DS-FCD-001",
    )

    service = DatasetStagingService(staging_root="/tmp/veritas-staging")
    plan = service.build_staging_plan(
        request_id="REQ-1002",
        atlas_dataset_id="DS-FCD-001",
        staging=staging,
        manifest=manifest,
    )

    assert "Missing ATLAS_STAGING_TOKEN" in plan.stage_script
