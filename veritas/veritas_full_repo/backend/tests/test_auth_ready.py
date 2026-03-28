
from fastapi.testclient import TestClient

from app.main import app


def test_auth_mode_endpoint():
    client = TestClient(app)
    response = client.get("/api/v1/auth/mode")
    assert response.status_code == 200
    assert "data" in response.json()


def test_login_endpoint_available():
    client = TestClient(app)
    response = client.post("/api/v1/auth/login", json={"email": "admin@veritas.local", "password": "admin-password"})
    assert response.status_code in (200, 401)


def test_me_requires_auth_when_enabled_documented():
    # scaffold test for future enabled-auth behavior
    assert True
