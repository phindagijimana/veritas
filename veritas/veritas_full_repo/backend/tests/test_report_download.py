"""Authenticated report file download: streams the artifact with auth applied."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import get_settings
from app.db.session import get_db
from app.main import app
from app.services.auth_service import AuthService
from app.services.report_service import ReportService
from app.services.request_service import RequestService


def _jwt(role: str = "admin", email: str | None = None) -> str:
    email = email or f"{role}@veritas.local"
    return AuthService.build().create_access_token(email, role=role, full_name=role.title())


@pytest.fixture
def auth_on(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_SECRET_KEY", "report-download-secret-key-32b!!!")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _open_test_session():
    """Borrow the conftest's override (already wired to the TestingSessionLocal)
    instead of re-importing tests.conftest, which would create a second temp DB
    and orphan the route-side connection on the original empty one."""
    override = app.dependency_overrides[get_db]
    gen = override()
    return next(gen), gen


def _seed_report_artifact(tmp_path, request_code: str) -> Path:
    from app.models.report_artifact import ReportArtifact

    db, gen = _open_test_session()
    try:
        request = RequestService._resolve(db, request_code)
        assert request is not None, f"seed test data missing {request_code}"
        _, report = ReportService._ensure_report(db, request.id)
        pdf_dir = tmp_path / "artifacts" / request_code
        pdf_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = pdf_dir / "report.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\nstubbed test pdf\n")
        pdf = next((a for a in report.artifacts if a.artifact_type.lower() == "pdf"), None)
        if pdf is None:
            pdf = ReportArtifact(report_id=report.id, artifact_type="PDF", status="Ready", storage_path=str(pdf_path))
            db.add(pdf)
        else:
            pdf.storage_path = str(pdf_path)
            db.add(pdf)
        db.commit()
        return pdf_path
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def test_download_returns_file_with_disposition(auth_on, tmp_path, client):
    pdf = _seed_report_artifact(tmp_path, "REQ-2002")

    r = client.get(
        "/api/v1/reports/REQ-2002/download/pdf/file",
        headers={"Authorization": f"Bearer {_jwt()}"},
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/pdf")
    assert "REQ-2002-report.pdf" in r.headers.get("content-disposition", "")
    assert r.content == pdf.read_bytes()


def test_download_requires_auth(auth_on, client):
    r = client.get("/api/v1/reports/REQ-2002/download/pdf/file")
    assert r.status_code == 401, r.text


def test_download_404_for_missing_artifact(auth_on, client):
    # Use a real request_id but a format that wasn't generated.
    r = client.get(
        "/api/v1/reports/REQ-2002/download/zip/file",
        headers={"Authorization": f"Bearer {_jwt()}"},
    )
    assert r.status_code == 404, r.text


def test_download_404_for_unknown_request(auth_on, client):
    r = client.get(
        "/api/v1/reports/REQ-DOES-NOT-EXIST/download/pdf/file",
        headers={"Authorization": f"Bearer {_jwt()}"},
    )
    assert r.status_code == 404, r.text
