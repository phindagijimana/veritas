from __future__ import annotations


def test_atlas_datasets_list_on_main_app(client):
    response = client.get("/api/v1/atlas/datasets")
    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)
    assert data[0]["atlas_dataset_id"] == "mock-ds-001"


def test_atlas_phase_c_on_main_app(client):
    r = client.post(
        "/api/v1/atlas/phase-c/prepare",
        json={"request_id": "REQ-xyz", "atlas_dataset_id": "ATLAS-1"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["request_id"] == "REQ-xyz"
