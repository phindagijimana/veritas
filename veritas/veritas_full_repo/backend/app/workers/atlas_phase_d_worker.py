from __future__ import annotations
from dataclasses import dataclass
from app.services.atlas_phase_d_service import AtlasPhaseDService

@dataclass
class PhaseDWorkerResult:
    request_id: str
    status: str
    message: str

class AtlasPhaseDWorker:
    def __init__(self, service: AtlasPhaseDService | None = None):
        self.service = service or AtlasPhaseDService()

    def run_transfer(self, *, request_id: str, atlas_dataset_id: str) -> PhaseDWorkerResult:
        state = self.service.execute_stage(request_id=request_id, atlas_dataset_id=atlas_dataset_id, destination_root="/tmp/veritas/staging")
        return PhaseDWorkerResult(request_id=request_id, status=state.status, message=state.message or "Transfer completed.")
