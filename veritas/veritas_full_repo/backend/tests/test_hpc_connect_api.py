"""HPC SSH connect uses real Paramiko validation; tests monkeypatch SSH."""

from app.services.ssh_service import SSHService


def test_hpc_connect_persists_when_ssh_ok(client, monkeypatch):
    monkeypatch.setattr(SSHService, "validate_connection", lambda self, c: None)
    r = client.post(
        "/api/v1/hpc/connect",
        json={"hostname": "cluster.example.edu", "username": "researcher", "port": 22},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["status"] == "connected"
    assert data["hostname"] == "cluster.example.edu"
    assert data["username"] == "researcher"


def test_hpc_connect_400_when_ssh_fails(client, monkeypatch):
    def fail(self, connection):
        raise ValueError("SSH authentication failed: denied")

    monkeypatch.setattr(SSHService, "validate_connection", fail)
    r = client.post(
        "/api/v1/hpc/connect",
        json={"hostname": "cluster.example.edu", "username": "researcher", "port": 22},
    )
    assert r.status_code == 400
    assert "denied" in r.json()["detail"]
