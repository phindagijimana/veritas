from app.services.atlas_phase_d_service import AtlasPhaseDService

def main():
    service = AtlasPhaseDService()
    state = service.execute_stage(request_id="REQ-SMOKE", atlas_dataset_id="ATLAS-HS-1", destination_root="/tmp/veritas/staging")
    result = service.validate_stage(request_id="REQ-SMOKE", staged_dataset_path=state.staged_dataset_path)
    print("execute_status:", state.status)
    print("staged_dataset_path:", state.staged_dataset_path)
    print("validation_status:", result.validation_status)
    print("message:", result.message)

if __name__ == "__main__":
    main()
