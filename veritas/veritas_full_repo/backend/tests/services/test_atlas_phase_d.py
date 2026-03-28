from app.services.atlas_phase_d_service import AtlasPhaseDService

def test_execute_stage_creates_path(tmp_path):
    service = AtlasPhaseDService()
    state = service.execute_stage(request_id="REQ-100", atlas_dataset_id="ATLAS-AD-1", destination_root=str(tmp_path))
    assert state.status == "staged"
    assert "ATLAS-AD-1" in state.staged_dataset_path

def test_validate_stage(tmp_path):
    service = AtlasPhaseDService()
    state = service.execute_stage(request_id="REQ-101", atlas_dataset_id="ATLAS-FCD-1", destination_root=str(tmp_path))
    result = service.validate_stage(request_id="REQ-101", staged_dataset_path=state.staged_dataset_path)
    assert result.validation_status == "validated"
