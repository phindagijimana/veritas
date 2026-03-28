from fastapi.testclient import TestClient

from app.main import create_app


def _admin_headers() -> dict[str, str]:
    return {"X-Internal-Api-Key": "test-internal-key"}


def test_admin_grant_crud_flow() -> None:
    with TestClient(create_app()) as client:
        r = client.get("/api/v1/admin/grants", headers=_admin_headers())
        assert r.status_code == 200
        initial = len(r.json()["data"])

        c = client.post(
            "/api/v1/admin/grants",
            headers=_admin_headers(),
            json={
                "dataset_id": "openneuro-ds1",
                "principal_type": "user",
                "principal_id": "grant-test-user",
                "access_level": "read",
            },
        )
        assert c.status_code == 201
        gid = c.json()["data"]["id"]

        u = client.patch(
            f"/api/v1/admin/grants/{gid}",
            headers=_admin_headers(),
            json={"access_level": "write"},
        )
        assert u.status_code == 200
        assert u.json()["data"]["access_level"] == "write"

        d = client.delete(f"/api/v1/admin/grants/{gid}", headers=_admin_headers())
        assert d.status_code == 204

        r2 = client.get("/api/v1/admin/grants", headers=_admin_headers())
        assert len(r2.json()["data"]) == initial


def test_admin_audit_events_list() -> None:
    with TestClient(create_app()) as client:
        r = client.get("/api/v1/admin/audit-events?limit=5", headers=_admin_headers())
        assert r.status_code == 200
        assert "data" in r.json()
