from fastapi.testclient import TestClient

from app.main import create_app


def _auth_headers() -> dict[str, str]:
    return {
        "X-Principal-Id": "user-123",
        "X-Principal-Type": "user",
        "X-Principal-Roles": "researcher",
    }


def test_public_dataset_download_allowed() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/datasets/openneuro-ds1/download", headers=_auth_headers())
    assert response.status_code == 200
    body = response.json()
    assert body["dataset_id"] == "openneuro-ds1"
    assert body["downloadable"] is True
    assert body["storage_provider"] == "pennsieve"
    assert body["download_url"].endswith("openneuro-ds1.zip")
    assert body.get("pennsieve_resolved") is False


def test_restricted_dataset_download_forbidden() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/datasets/clinical-mri-a/download", headers=_auth_headers())
    assert response.status_code == 403
    assert "public or open-source" in response.json()["detail"]


def test_private_dataset_download_forbidden() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/datasets/internal-hs-private/download", headers=_auth_headers())
    assert response.status_code == 404
    assert response.json()["detail"] == "Dataset not found"


def test_dataset_listing_marks_only_public_as_downloadable() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/datasets", headers=_auth_headers())
    assert response.status_code == 200
    body = response.json()
    items = {item["dataset_id"]: item for item in body["items"]}
    assert body["count"] == 3
    assert "internal-hs-private" not in items
    assert items["openneuro-ds1"]["downloadable"] is True
    assert items["openneuro-ds1"]["storage_provider"] == "pennsieve"
    assert items["ideas"]["downloadable"] is True
    assert items["ideas"]["storage_provider"] == "pennsieve"
    assert len(items["ideas"]["storage_homes"]) == 2
    assert items["ideas"]["storage_homes"][0]["role"] == "primary"
    assert items["ideas"]["storage_homes"][0]["storage_provider"] == "pennsieve"
    assert items["ideas"]["storage_homes"][1]["role"] == "secondary"
    assert items["ideas"]["storage_homes"][1]["storage_provider"] == "ood_hpc"
    assert len(items["openneuro-ds1"]["storage_homes"]) == 1
    assert "cidur-bids" not in items
    assert items["clinical-mri-a"]["downloadable"] is False
    assert items["clinical-mri-a"]["staging_allowed"] is True
    assert items["clinical-mri-a"]["access_class"] == "validation"


def test_internal_api_key_lists_all_datasets() -> None:
    with TestClient(create_app()) as client:
        response = client.get(
            "/api/v1/datasets",
            headers={"X-Internal-Api-Key": "test-internal-key"},
        )
    assert response.status_code == 200
    assert response.json()["count"] == 5


def test_validation_dataset_stage_authorized_for_urmc_hpc() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/datasets/clinical-mri-a/stage",
            headers=_auth_headers(),
            json={"compute_target": "URMC_HPC", "requested_by": "veritas_service"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "authorized"
    assert body["mode"] == "controlled_validation_staging"
    assert body["storage_provider"] == "pennsieve"


def test_validation_dataset_stage_denied_for_remote_server() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/datasets/clinical-mri-a/stage",
            headers=_auth_headers(),
            json={"compute_target": "REMOTE_SERVER"},
        )
    assert response.status_code == 403
    assert "not approved" in response.json()["detail"]


def test_private_dataset_staging_forbidden() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/datasets/internal-hs-private/stage",
            headers=_auth_headers(),
            json={"compute_target": "URMC_HPC"},
        )
    assert response.status_code == 403
    assert "not eligible" in response.json()["detail"]


def test_public_dataset_staging_allowed_for_cache_or_compute() -> None:
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/datasets/openneuro-ds1/stage",
            headers=_auth_headers(),
            json={"compute_target": "REMOTE_SERVER"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "public_download_or_cache"
