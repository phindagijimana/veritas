"""Authenticated job-log viewer: returns last 256 KB of stdout/stderr."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import get_settings
from app.db.session import get_db
from app.main import app
from app.models.job import Job
from app.services.auth_service import AuthService
from app.services.request_service import RequestService


def _jwt(role: str = "researcher", email: str | None = None) -> str:
    email = email or f"{role}@veritas.local"
    return AuthService.build().create_access_token(email, role=role, full_name=role.title())


@pytest.fixture
def auth_on(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_SECRET_KEY", "job-logs-test-secret-key-32bytes!!")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _open_test_session():
    override = app.dependency_overrides[get_db]
    gen = override()
    return next(gen), gen


def _seed_job(tmp_path, request_code: str, stdout_text: str, stderr_text: str | None = None) -> int:
    db, gen = _open_test_session()
    try:
        req = RequestService._resolve(db, request_code)
        assert req is not None, f"missing seeded request {request_code}"
        log_dir = tmp_path / "logs" / request_code
        log_dir.mkdir(parents=True, exist_ok=True)
        out = log_dir / "stdout.log"
        out.write_text(stdout_text, encoding="utf-8")
        err = log_dir / "stderr.log"
        if stderr_text is not None:
            err.write_text(stderr_text, encoding="utf-8")
        job = Job(
            scheduler_job_id="TEST-JOB-1",
            job_name=f"test-{request_code.lower()}",
            request_id=req.id,
            status="RUNNING",
            stdout_path=str(out),
            stderr_path=str(err) if stderr_text is not None else None,
        )
        db.add(job)
        db.commit()
        return job.id
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def test_logs_returns_stdout(auth_on, tmp_path, client):
    job_id = _seed_job(tmp_path, "REQ-2002", stdout_text="line 1\nline 2\nDONE\n")
    r = client.get(
        f"/api/v1/jobs/{job_id}/logs?stream=stdout",
        headers={"Authorization": f"Bearer {_jwt()}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["available"] is True
    assert data["stream"] == "stdout"
    assert data["truncated"] is False
    assert "line 1" in data["content"]
    assert "DONE" in data["content"]


def test_logs_returns_stderr(auth_on, tmp_path, client):
    job_id = _seed_job(tmp_path, "REQ-2003", stdout_text="x", stderr_text="boom: traceback")
    r = client.get(
        f"/api/v1/jobs/{job_id}/logs?stream=stderr",
        headers={"Authorization": f"Bearer {_jwt()}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["available"] is True
    assert data["content"].startswith("boom:")


def test_logs_reports_missing_path_gracefully(auth_on, tmp_path, client):
    job_id = _seed_job(tmp_path, "REQ-2001", stdout_text="something", stderr_text=None)
    r = client.get(
        f"/api/v1/jobs/{job_id}/logs?stream=stderr",
        headers={"Authorization": f"Bearer {_jwt()}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["available"] is False
    assert "No stderr path recorded" in data["message"]


def test_logs_truncates_large_files(auth_on, tmp_path, client):
    # 300 KB of content, endpoint caps at 256 KB
    big = "x" * (300 * 1024) + "\nFINAL-LINE\n"
    job_id = _seed_job(tmp_path, "REQ-2090", stdout_text=big)
    r = client.get(
        f"/api/v1/jobs/{job_id}/logs?stream=stdout",
        headers={"Authorization": f"Bearer {_jwt()}"},
    )
    data = r.json()["data"]
    assert data["truncated"] is True
    assert data["size"] > 256 * 1024
    # The tail is what gets returned, so the final marker must be present.
    assert "FINAL-LINE" in data["content"]


def test_logs_requires_auth(auth_on, client):
    r = client.get("/api/v1/jobs/9999/logs?stream=stdout")
    assert r.status_code == 401, r.text


def test_logs_404_for_unknown_job(auth_on, client):
    r = client.get(
        "/api/v1/jobs/999999/logs?stream=stdout",
        headers={"Authorization": f"Bearer {_jwt()}"},
    )
    assert r.status_code == 404, r.text


def test_logs_rejects_invalid_stream(auth_on, client):
    # Pydantic regex on the Query param should 422 a bad value.
    r = client.get(
        "/api/v1/jobs/1/logs?stream=trash",
        headers={"Authorization": f"Bearer {_jwt()}"},
    )
    assert r.status_code == 422, r.text
