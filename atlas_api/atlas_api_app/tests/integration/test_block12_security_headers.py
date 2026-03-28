from fastapi.testclient import TestClient

from app.main import create_app


def test_missing_auth_rejected() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/v1/security-demo/me")
    assert response.status_code == 401


def test_forwarded_headers_allowed_for_demo() -> None:
    with TestClient(create_app()) as client:
        response = client.get(
            "/api/v1/security-demo/me",
            headers={
                "X-Principal-Id": "svc-veritas",
                "X-Principal-Type": "service",
                "X-Principal-Roles": "service",
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["principal_id"] == "svc-veritas"
    assert body["principal_type"] == "service"
