from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.atlas_phase_d import router

app = FastAPI()
app.include_router(router, prefix="/api/v1")
client = TestClient(app)


def test_execute_stage_route(tmp_path):
    response = client.post(
        "/api/v1/atlas/phase-d/execute-stage",
        json={
            "request_id": "REQ-200",
            "atlas_dataset_id": "ATLAS-TSC-1",
            "destination_root": str(tmp_path),
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "staged"


def test_validate_route(tmp_path):
    client.post(
        "/api/v1/atlas/phase-d/execute-stage",
        json={
            "request_id": "REQ-201",
            "atlas_dataset_id": "ATLAS-TSC-2",
            "destination_root": str(tmp_path),
        },
    )
    response = client.post("/api/v1/atlas/phase-d/requests/REQ-201/staging-validate")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["validation_status"] == "validated"
