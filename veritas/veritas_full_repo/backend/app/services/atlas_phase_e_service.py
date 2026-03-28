from __future__ import annotations
from app.services.hidden_test_service import HiddenTestService
from app.schemas.atlas_phase_e import HiddenTestExecutionResponse

class AtlasPhaseEService:
    def __init__(self, hidden_test_service: HiddenTestService | None = None):
        self.hidden_test_service = hidden_test_service or HiddenTestService()

    def evaluate_hidden_test(self, *, request_id: str, atlas_dataset_id: str, staged_dataset_path: str, pipeline_ref: str) -> HiddenTestExecutionResponse:
        result = self.hidden_test_service.run_hidden_test(
            request_id=request_id,
            atlas_dataset_id=atlas_dataset_id,
            staged_dataset_path=staged_dataset_path,
            pipeline_ref=pipeline_ref,
        )
        return HiddenTestExecutionResponse(
            request_id=result.request_id,
            atlas_dataset_id=result.atlas_dataset_id,
            hidden_test_status=result.hidden_test_status,
            evaluation_bundle_id=result.evaluation_bundle_id,
            metrics=result.metrics,
            dataset_hash=result.dataset_hash,
            pipeline_hash=result.pipeline_hash,
            container_hash=result.container_hash,
            message=result.message,
        )
