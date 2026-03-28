
from __future__ import annotations

from pathlib import Path

from app.schemas.atlas import (
    AtlasStagingManifest,
    AtlasStagingResponse,
    AtlasSubmissionContext,
)
from app.services.atlas_execution_service import AtlasExecutionService
from app.services.dataset_staging_service import DatasetStagingService


class FakeAtlasClient:
    def __init__(self, status: str = "approved") -> None:
        self.status = status

    def request_staging(self, request):
        return AtlasStagingResponse(
            atlas_staging_id="STAGE-2001",
            atlas_dataset_id=request.atlas_dataset_id,
            status=self.status,
            token="stage-token" if self.status == "approved" else None,
            manifest_url="https://atlas.example.org/manifests/STAGE-2001" if self.status == "approved" else None,
            source="pennsieve",
        )

    def get_staging_manifest(self, atlas_staging_id: str):
        return AtlasStagingManifest(
            atlas_staging_id=atlas_staging_id,
            atlas_dataset_id="ATLAS-HS-001",
            files=[{"path": "sub-001/anat/sub-001_T1w.nii.gz"}],
            source="pennsieve",
        )


def test_prepare_submission_writes_stage_files(tmp_path: Path):
    service = AtlasExecutionService(
        atlas_client=FakeAtlasClient(status="approved"),
        staging_service=DatasetStagingService(staging_root=str(tmp_path)),
    )
    bundle = service.prepare_submission(
        AtlasSubmissionContext(
            request_id="REQ-2001",
            atlas_dataset_id="ATLAS-HS-001",
            pipeline_id="pipe-1",
            user_id="user-1",
        )
    )
    assert bundle.staging_status == "prepared"
    assert bundle.staged_dataset_path.endswith("/REQ-2001/ATLAS-HS-001/dataset")
    assert bundle.stage_script_path is not None
    assert Path(bundle.stage_script_path).exists()
    assert bundle.stage_env_path is not None
    assert Path(bundle.stage_env_path).exists()
    preamble = service.build_runtime_preamble(bundle)
    assert "VERITAS_STAGED_DATASET_PATH" in preamble


def test_prepare_submission_handles_pending_approval(tmp_path: Path):
    service = AtlasExecutionService(
        atlas_client=FakeAtlasClient(status="pending_approval"),
        staging_service=DatasetStagingService(staging_root=str(tmp_path)),
    )
    bundle = service.prepare_submission(
        AtlasSubmissionContext(
            request_id="REQ-2002",
            atlas_dataset_id="ATLAS-FCD-001",
        )
    )
    assert bundle.staging_status == "pending_approval"
    assert bundle.stage_script_path is None
    assert "not ready" in (bundle.message or "").lower()
