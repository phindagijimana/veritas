from app.services.atlas_phase_c_service import AtlasPhaseCService

def test_prepare_and_stage_approved():
    service = AtlasPhaseCService()
    bundle = service.prepare_and_stage(request_id="REQ-1", atlas_dataset_id="ATLAS-HS-1")
    assert bundle.status == "staged"
    assert bundle.approval_status == "approved"
    assert "ATLAS-HS-1" in bundle.staged_dataset_path

def test_prepare_and_stage_pending():
    service = AtlasPhaseCService()
    bundle = service.prepare_and_stage(request_id="REQ-2", atlas_dataset_id="ATLAS-HS-2", approval_status="pending")
    assert bundle.status == "approval_pending"
    assert bundle.staged_dataset_path is None
