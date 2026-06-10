"""Append-only audit log: writes are recorded, GETs are not, /admin/audit returns them."""
from __future__ import annotations

import pytest

from app.core.config import get_settings
from app.db.session import get_db
from app.main import app
from app.models.audit_event import AuditEvent
from app.services.auth_service import AuthService


def _jwt(role: str = "admin", email: str | None = None) -> str:
    email = email or f"{role}@veritas.local"
    return AuthService.build().create_access_token(email, role=role, full_name=role.title())


@pytest.fixture
def auth_on(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_SECRET_KEY", "audit-log-test-secret-key-32b!!!")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _open_test_session():
    override = app.dependency_overrides[get_db]
    gen = override()
    return next(gen), gen


def _wipe_audit():
    db, gen = _open_test_session()
    try:
        db.query(AuditEvent).delete()
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _audit_rows(**filters):
    db, gen = _open_test_session()
    try:
        q = db.query(AuditEvent)
        for k, v in filters.items():
            q = q.filter(getattr(AuditEvent, k) == v)
        return q.order_by(AuditEvent.id.asc()).all()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def test_post_writes_audit_row_with_actor(auth_on, client):
    _wipe_audit()
    token = _jwt(email="audit-actor@veritas.local")
    r = client.post(
        "/api/v1/pipelines",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "audited", "title": "Audited", "image": "img:0", "modality": "MRI"},
    )
    # 200 or 400 depending on payload validation; the audit row should exist either way.
    rows = _audit_rows(action="pipeline.create")
    assert len(rows) >= 1
    row = rows[-1]
    assert row.actor_email == "audit-actor@veritas.local"
    assert row.actor_role == "admin"
    assert row.auth_method == "jwt"
    assert row.http_status == r.status_code
    assert "POST" in (row.route or "")


def test_get_requests_do_not_create_audit_rows(auth_on, client):
    _wipe_audit()
    client.get("/api/v1/pipelines", headers={"Authorization": f"Bearer {_jwt()}"})
    client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {_jwt()}"})
    rows = _audit_rows()
    assert rows == []


def test_subject_extracted_for_request_routes(auth_on, client):
    _wipe_audit()
    r = client.post(
        "/api/v1/jobs/preview/REQ-2002",
        headers={"Authorization": f"Bearer {_jwt(role='researcher')}"},
        json={
            "job_name": "audit-preview",
            "pipeline": "img:0",
            "pipeline_name": "x",
            "dataset": "IDEAS",
            "partition": "gpu",
            "resources": {"gpu": 1, "cpu": 4, "memory_gb": 8, "wall_time": "01:00:00"},
            "runtime_profile": "generic",
        },
    )
    rows = _audit_rows(action="job.preview")
    assert len(rows) == 1
    assert rows[0].subject_type == "request"
    assert rows[0].subject_id == "REQ-2002"
    assert rows[0].http_status == r.status_code


def test_pat_actor_recorded_as_pat_method(auth_on, client):
    _wipe_audit()
    # Create a PAT via JWT
    create = client.post(
        "/api/v1/auth/tokens",
        headers={"Authorization": f"Bearer {_jwt(email='pat-audit@veritas.local')}"},
        json={"label": "audit"},
    )
    assert create.status_code == 201, create.text
    plaintext = create.json()["token"]

    # Use the PAT for a write (rejected by anti-pivot guard — but the audit row
    # should still record auth_method='pat').
    client.post(
        "/api/v1/auth/tokens",
        headers={"Authorization": f"Bearer {plaintext}"},
        json={"label": "pivot"},
    )
    pivots = _audit_rows(action="auth.token.create")
    # The first one (create) was via JWT; the second attempt via PAT.
    methods = [r.auth_method for r in pivots]
    assert "jwt" in methods
    assert "pat" in methods


def test_admin_audit_endpoint_requires_admin(auth_on, client):
    r = client.get("/api/v1/admin/audit", headers={"Authorization": f"Bearer {_jwt(role='researcher')}"})
    assert r.status_code == 403, r.text


def test_admin_audit_endpoint_filters_and_lists(auth_on, client):
    _wipe_audit()
    # Seed two audit events via real calls.
    client.post(
        "/api/v1/pipelines",
        headers={"Authorization": f"Bearer {_jwt(email='filter1@veritas.local')}"},
        json={"name": "p1", "title": "p1", "image": "img:0", "modality": "MRI"},
    )
    client.post(
        "/api/v1/datasets",
        headers={"Authorization": f"Bearer {_jwt(email='filter2@veritas.local')}"},
        json={"code": "TEST", "name": "Test DS"},
    )

    r = client.get(
        "/api/v1/admin/audit?action=pipeline.create",
        headers={"Authorization": f"Bearer {_jwt(email='audit-reader@veritas.local')}"},
    )
    assert r.status_code == 200, r.text
    items = r.json()["data"]
    assert all(it["action"] == "pipeline.create" for it in items)

    r2 = client.get(
        "/api/v1/admin/audit?actor_email=filter2@veritas.local",
        headers={"Authorization": f"Bearer {_jwt(email='audit-reader@veritas.local')}"},
    )
    assert r2.status_code == 200, r2.text
    items2 = r2.json()["data"]
    assert all(it["actor_email"] == "filter2@veritas.local" for it in items2)
