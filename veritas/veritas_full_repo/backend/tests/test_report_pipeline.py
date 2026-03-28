from pathlib import Path

from app.core.config import get_settings


def test_generate_report_creates_artifacts(client):
    response = client.post("/api/v1/reports/generate/REQ-2001")
    assert response.status_code == 200
    detail = client.get("/api/v1/reports/REQ-2001")
    assert detail.status_code == 200
    artifacts = detail.json()["data"]["artifacts"]
    assert len(artifacts) >= 3
    assert {artifact["type"] for artifact in artifacts} >= {"PDF", "JSON", "CSV"}


def test_publish_report_marks_ready(client):
    response = client.post("/api/v1/reports/publish/REQ-2002")
    assert response.status_code == 200
    detail = client.get("/api/v1/reports/REQ-2002")
    assert detail.status_code == 200
    data = detail.json()["data"]
    assert data["status"] == "Ready"
    assert data["published_at"] is not None


def test_download_report_link_payload(client):
    client.post("/api/v1/reports/generate/REQ-2001")
    response = client.get("/api/v1/reports/REQ-2001/download", params={"format": "pdf"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["artifact_type"] == "PDF"
    assert data["status"] == "ready"
    assert "/static/" in data["url"]


def test_report_generator_writes_files(client):
    client.post("/api/v1/reports/generate/REQ-2001")
    settings = get_settings()
    root = Path(settings.artifact_root_dir)
    assert list(root.rglob("report.pdf"))
    assert list(root.rglob("report.json"))
    assert list(root.rglob("results.csv"))
