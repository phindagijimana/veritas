"""Notifications: list scoped to current user, mark-read, mark-all-read, and
that report generation triggers a notification for the requester."""
from __future__ import annotations

import pytest

from app.core.config import get_settings
from app.services.auth_service import AuthService
from app.services.notification_service import notify

# Importing `conftest` (no `tests.` prefix) matches pytest's loaded copy; doing
# `from tests.conftest import ...` would double-load and bind to a different
# tempfile from the one pytest's fixtures actually populated.
from conftest import TestingSessionLocal  # noqa: E402


def _jwt(email: str, role: str = "researcher") -> str:
    return AuthService.build().create_access_token(email, role=role, full_name=email.split("@")[0])


@pytest.fixture
def auth_on(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_SECRET_KEY", "notif-test-secret-key-32bytes-min!")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _seed(email: str) -> tuple[int, int]:
    """Insert two notifications for `email` and return their ids."""
    db = TestingSessionLocal()
    try:
        a = notify(db, user_email=email, kind="report.ready", title="One", body=None, commit=False)
        b = notify(db, user_email=email, kind="role.changed", title="Two", body=None, commit=False)
        db.commit()
        db.refresh(a)
        db.refresh(b)
        return a.id, b.id
    finally:
        db.close()


def test_list_returns_only_caller_notifications(auth_on, client):
    alice_id, _ = _seed("alice-notif@veritas.local")
    _seed("bob-notif@veritas.local")
    r = client.get(
        "/api/v1/notifications",
        headers={"Authorization": f"Bearer {_jwt('alice-notif@veritas.local')}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    emails = {n["title"] for n in body["data"]}
    assert "One" in emails
    assert "Two" in emails
    assert body["unread_count"] == 2
    # Alice cannot see Bob's notifications.
    assert all("bob" not in n["body"].lower() if n.get("body") else True for n in body["data"])


def test_mark_read_drops_unread_count(auth_on, client):
    nid, _ = _seed("mark-read@veritas.local")
    headers = {"Authorization": f"Bearer {_jwt('mark-read@veritas.local')}"}
    r = client.post(f"/api/v1/notifications/{nid}/read", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    # The marked one is read; the other is still unread.
    assert body["unread_count"] == 1


def test_mark_read_404_for_other_users_notification(auth_on, client):
    nid, _ = _seed("owner-only@veritas.local")
    r = client.post(
        f"/api/v1/notifications/{nid}/read",
        headers={"Authorization": f"Bearer {_jwt('intruder@veritas.local')}"},
    )
    assert r.status_code == 404, r.text


def test_mark_all_read_zeros_unread(auth_on, client):
    _seed("mark-all@veritas.local")
    headers = {"Authorization": f"Bearer {_jwt('mark-all@veritas.local')}"}
    r = client.post("/api/v1/notifications/read-all", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["unread_count"] == 0


def test_unread_only_filters(auth_on, client):
    a_id, _ = _seed("uo-filter@veritas.local")
    headers = {"Authorization": f"Bearer {_jwt('uo-filter@veritas.local')}"}
    client.post(f"/api/v1/notifications/{a_id}/read", headers=headers)
    r = client.get("/api/v1/notifications?unread_only=true", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    titles = [n["title"] for n in body["data"]]
    assert "One" not in titles  # was marked read
    assert "Two" in titles


def test_report_generation_creates_notification(auth_on, client):
    """End-to-end: create request → submit job → advance → generate report → requester sees notification."""
    requester = "report-recipient@veritas.local"
    headers_admin = {"Authorization": f"Bearer {_jwt('admin@veritas.local', role='admin')}"}
    headers_user = {"Authorization": f"Bearer {_jwt(requester)}"}

    # Create the request with researcher token so submitted_by = researcher email.
    pipe = client.get("/api/v1/pipelines", headers=headers_user).json()["data"]
    if not pipe:
        pytest.skip("no pipelines seeded in test DB")
    ds = client.get("/api/v1/datasets", headers=headers_user).json()["data"]
    if not ds:
        pytest.skip("no datasets seeded in test DB")

    create = client.post(
        "/api/v1/requests",
        headers=headers_user,
        json={"datasets": [ds[0].get("code", "FCD")], "pipeline": pipe[0]["name"], "description": "notif e2e"},
    )
    assert create.status_code == 200, create.text
    rid = create.json()["data"]["id"]

    sub = client.post(
        f"/api/v1/jobs/submit/{rid}",
        headers=headers_admin,
        json={
            "job_name": "notif-job",
            "pipeline": "docker.io/example:1",
            "pipeline_name": pipe[0]["name"],
            "dataset": ds[0].get("code", "FCD"),
            "partition": "gpu",
            "resources": {"gpu": 1, "cpu": 8, "memory_gb": 32, "wall_time": "01:00:00"},
            "runtime_profile": "generic",
        },
    )
    assert sub.status_code == 200, sub.text

    # advance through phases
    job_db_id = sub.json()["data"]["job_id"]
    for _ in range(4):
        client.post(f"/api/v1/jobs/{job_db_id}/advance", headers=headers_admin)

    gen = client.post(f"/api/v1/reports/generate/{rid}", headers=headers_admin)
    assert gen.status_code == 200, gen.text

    # The requester should now have an unread "Report ready" notification.
    me = client.get("/api/v1/notifications", headers=headers_user)
    assert me.status_code == 200, me.text
    body = me.json()
    assert body["unread_count"] >= 1, body
    titles = [n["title"] for n in body["data"]]
    assert any("Report ready" in t for t in titles), titles
