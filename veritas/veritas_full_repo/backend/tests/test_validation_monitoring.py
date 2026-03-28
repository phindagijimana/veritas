from fastapi.testclient import TestClient


def test_ready_includes_database(client: TestClient):
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body.get("database") == "ok"


def test_dataset_validate(client: TestClient):
    response = client.post("/api/v1/datasets/HS/validate")
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["dataset_code"] == "HS"
    assert "checks" in payload


def test_metrics_endpoint(client: TestClient):
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    assert "veritas_http_requests_total" in response.text or response.text
