from __future__ import annotations
from dataclasses import dataclass
from app.services.pennsieve_transfer_service import PennsieveTransferService
from app.schemas.atlas_phase_d import StageValidationResponse

@dataclass
class StageState:
    request_id: str
    atlas_dataset_id: str
    status: str
    staged_dataset_path: str | None = None
    transfer_log: str | None = None
    validation_status: str = ""
    message: str | None = None
    manifest_url: str | None = None

class AtlasPhaseDService:
    def __init__(self, transfer_service: PennsieveTransferService | None = None):
        self.transfer_service = transfer_service or PennsieveTransferService()

    def execute_stage(self, *, request_id: str, atlas_dataset_id: str, destination_root: str | None = None) -> StageState:
        result = self.transfer_service.execute_transfer(
            request_id=request_id,
            atlas_dataset_id=atlas_dataset_id,
            destination_root=destination_root,
        )
        return StageState(
            request_id=request_id,
            atlas_dataset_id=atlas_dataset_id,
            status=result.status,
            staged_dataset_path=result.staged_dataset_path,
            transfer_log=result.transfer_log,
            message=result.message,
            manifest_url=result.manifest_url,
        )

    def validate_stage(self, *, request_id: str, staged_dataset_path: str) -> StageValidationResponse:
        validation_status, message = self.transfer_service.validate_stage(staged_dataset_path=staged_dataset_path)
        return StageValidationResponse(
            request_id=request_id,
            status="staged" if validation_status == "validated" else "failed",
            validation_status=validation_status,
            staged_dataset_path=staged_dataset_path,
            transfer_log=message,
            message=message,
        )
