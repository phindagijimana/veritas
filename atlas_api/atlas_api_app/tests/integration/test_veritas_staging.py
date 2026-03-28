from fastapi.testclient import TestClient

from app.main import create_app


def _auth_headers() -> dict[str, str]:
    return {
        "X-Principal-Id": "user-123",
        "X-Principal-Type": "user",
        "X-Principal-Roles": "researcher",
    }


def test_datasets_list_includes_veritas_data_envelope() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/datasets", headers=_auth_headers())
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "data" in body
    assert isinstance(body["data"], list)
    assert body["data"][0]["atlas_dataset_id"] == body["items"][0]["dataset_id"]
    assert "disease_group" in body["data"][0]


def test_dataset_detail_includes_nested_veritas_data() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/datasets/clinical-mri-a", headers=_auth_headers())
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["atlas_dataset_id"] == "clinical-mri-a"
    assert body["dataset_id"] == "clinical-mri-a"


def test_veritas_staging_request_and_manifest() -> None:
    with TestClient(create_app()) as client:
        r = client.post(
            "/api/v1/staging/request",
            headers=_auth_headers(),
            json={
                "request_id": "REQ-INTEG-1",
                "atlas_dataset_id": "clinical-mri-a",
                "purpose": "benchmark_validation",
            },
        )
        assert r.status_code == 200
        staging = r.json()["data"]
        sid = staging["atlas_staging_id"]
        assert staging["status"] == "approved"
        assert staging["atlas_dataset_id"] == "clinical-mri-a"
        assert staging["metadata"]["transfer_status"] == "ready"
        assert staging["token"]
        assert "/manifest" in (staging["manifest_url"] or "")

        m = client.get(f"/api/v1/staging/{sid}/manifest", headers=_auth_headers())
        assert m.status_code == 200
        man = m.json()["data"]
        assert man["atlas_staging_id"] == sid
        assert len(man["files"]) >= 1

        s = client.get(f"/api/v1/staging/{sid}", headers=_auth_headers())
        assert s.status_code == 200
        assert s.json()["data"]["atlas_staging_id"] == sid


def test_veritas_service_headers_when_secret_configured(monkeypatch) -> None:
    from app.core import config as config_module

    monkeypatch.setenv("ATLAS_VERITAS_CLIENT_SECRET", "integration-secret")
    config_module.get_settings.cache_clear()
    try:
        with TestClient(create_app()) as client:
            r = client.get(
                "/api/v1/datasets",
                headers={
                    "X-Atlas-Client-Id": "veritas",
                    "X-Atlas-Client-Secret": "integration-secret",
                },
            )
        assert r.status_code == 200
        assert r.json()["principal_id"] == "veritas-service"
    finally:
        monkeypatch.delenv("ATLAS_VERITAS_CLIENT_SECRET", raising=False)
        config_module.get_settings.cache_clear()
