from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.atlas_phase_c import router

app = FastAPI()
app.include_router(router, prefix="/api/v1")
client = TestClient(app)


def test_prepare_route():
    response = client.post(
        "/api/v1/atlas/phase-c/prepare",
        json={"request_id": "REQ-10", "atlas_dataset_id": "ATLAS-FCD-1"},
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["status"] in {"staged", "approval_pending"}


def test_staging_status_route():
    response = client.get("/api/v1/atlas/phase-c/requests/REQ-10/staging-status")
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["request_id"] == "REQ-10"
