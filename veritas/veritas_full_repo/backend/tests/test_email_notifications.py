"""Email fan-out for notifications.

These tests don't open a real SMTP socket — they replace smtplib.SMTP / SMTP_SSL
with an in-memory fake that captures every send_message call. That lets the
suite cover the wire-format and the on/off toggle without needing aiosmtpd or
network access.
"""
from __future__ import annotations

import smtplib
from email.message import EmailMessage
from unittest.mock import MagicMock

import pytest

from app.core.config import get_settings
from app.services.email_service import (
    _build_absolute_link,
    send_email,
    send_notification_email,
)


# ───────────── fixtures ─────────────


class _CapturingSMTP:
    """Minimal stand-in for smtplib.SMTP that records every message sent."""

    instances: list["_CapturingSMTP"] = []

    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.starttls_called = False
        self.login_args = None
        self.sent: list[EmailMessage] = []
        _CapturingSMTP.instances.append(self)

    def starttls(self):
        self.starttls_called = True

    def login(self, username, password):
        self.login_args = (username, password)

    def send_message(self, msg: EmailMessage):
        self.sent.append(msg)

    def quit(self):
        pass


@pytest.fixture
def email_on(monkeypatch):
    """Enable email + replace SMTP with the capturing fake. Yields the fake
    class so tests can inspect what was sent."""
    monkeypatch.setenv("EMAIL_ENABLED", "true")
    monkeypatch.setenv("EMAIL_SMTP_HOST", "smtp.test")
    monkeypatch.setenv("EMAIL_SMTP_PORT", "25")
    monkeypatch.setenv("EMAIL_FROM", "Veritas <noreply@test>")
    monkeypatch.setenv("EMAIL_APP_BASE_URL", "https://veritas.example.com")
    get_settings.cache_clear()

    _CapturingSMTP.instances.clear()
    monkeypatch.setattr(smtplib, "SMTP", _CapturingSMTP)
    monkeypatch.setattr(smtplib, "SMTP_SSL", _CapturingSMTP)
    yield _CapturingSMTP
    get_settings.cache_clear()


# ───────────── tests ─────────────


def test_send_email_off_by_default(monkeypatch):
    """With EMAIL_ENABLED=false (default), send_email returns False without
    touching SMTP. Notifications must continue to work in this state."""
    monkeypatch.delenv("EMAIL_ENABLED", raising=False)
    get_settings.cache_clear()
    fake = MagicMock(name="SMTP")
    monkeypatch.setattr(smtplib, "SMTP", fake)
    monkeypatch.setattr(smtplib, "SMTP_SSL", fake)
    ok = send_email(to="alice@test", subject="x", body_text="x")
    assert ok is False
    fake.assert_not_called()


def test_send_email_with_smtp_records_message(email_on):
    ok = send_email(to="alice@test", subject="hello", body_text="plain", body_html="<b>html</b>")
    assert ok is True
    assert len(email_on.instances) == 1
    inst = email_on.instances[0]
    assert inst.host == "smtp.test"
    assert inst.port == 25
    assert len(inst.sent) == 1
    msg = inst.sent[0]
    assert msg["To"] == "alice@test"
    assert msg["Subject"] == "hello"
    assert msg["From"] == "Veritas <noreply@test>"
    # Multipart alternative — plain + html
    assert msg.is_multipart() is True
    payload = msg.get_payload()
    types = [p.get_content_type() for p in payload]
    assert "text/plain" in types
    assert "text/html" in types


def test_send_notification_email_renders_open_button(email_on):
    ok = send_notification_email(
        user_email="bob@test",
        kind="report.ready",
        title="Report ready for REQ-42",
        body="Your evaluation finished.",
        link_page="user",
        link_anchor="REQ-42",
    )
    assert ok is True
    msg = email_on.instances[0].sent[0]
    # The plain body contains the absolute link.
    plain = next(p for p in msg.get_payload() if p.get_content_type() == "text/plain")
    text = plain.get_content()
    assert "https://veritas.example.com/dashboard#REQ-42" in text
    html = next(p for p in msg.get_payload() if p.get_content_type() == "text/html")
    html_text = html.get_content()
    assert 'href="https://veritas.example.com/dashboard#REQ-42"' in html_text
    assert "Open in Veritas" in html_text


def test_leaderboard_link_renders_as_path_not_fragment(email_on):
    send_notification_email(
        user_email="lb@test",
        kind="leaderboard.published",
        title="You're on the leaderboard!",
        body=None,
        link_page="leaderboard",
        link_anchor="7",
    )
    msg = email_on.instances[0].sent[0]
    plain = next(p for p in msg.get_payload() if p.get_content_type() == "text/plain")
    assert "https://veritas.example.com/leaderboard/7" in plain.get_content()


def test_build_absolute_link_known_pages():
    assert _build_absolute_link(None, None) is None
    s = get_settings()
    s_base = s.email_app_base_url.rstrip("/")
    # Known pages map through correctly.
    assert _build_absolute_link("admin", None) == f"{s_base}/admin"
    assert _build_absolute_link("tokens", None) == f"{s_base}/tokens"
    # Unknown page falls back to /, anchor still appended.
    assert _build_absolute_link("nope", "X").startswith(s_base + "/")


def test_send_email_smtp_failure_is_swallowed(monkeypatch):
    """If SMTP raises, send_email returns False but never propagates."""
    monkeypatch.setenv("EMAIL_ENABLED", "true")
    monkeypatch.setenv("EMAIL_SMTP_HOST", "smtp.bad")
    monkeypatch.setenv("EMAIL_SMTP_PORT", "25")
    get_settings.cache_clear()

    class _Boom:
        def __init__(self, *args, **kwargs):
            raise OSError("connection refused")

    monkeypatch.setattr(smtplib, "SMTP", _Boom)
    ok = send_email(to="x@test", subject="x", body_text="x")
    assert ok is False  # logged a warning, but never raised
    get_settings.cache_clear()


def test_notify_writes_db_row_and_dispatches_email(email_on, client, monkeypatch):
    """Integration: the notify() helper used by /reports/generate also fans out."""
    # SessionLocal binds to the same DATABASE_URL the session-scoped
    # `setup_database` fixture populated; using it avoids the conftest shadowing
    # that `from conftest import TestingSessionLocal` hits during a full sweep.
    from app.db.session import SessionLocal
    from app.services.notification_service import notify

    db = SessionLocal()
    try:
        row = notify(
            db,
            user_email="end-to-end@test",
            kind="report.ready",
            title="Report ready for REQ-99",
            body="finished",
            link_page="user",
            link_anchor="REQ-99",
        )
    finally:
        db.close()

    assert row.id is not None
    assert len(email_on.instances) == 1
    msg = email_on.instances[0].sent[0]
    assert msg["To"] == "end-to-end@test"
    assert msg["Subject"] == "Report ready for REQ-99"


def test_notify_email_disabled_does_not_send(monkeypatch):
    """With EMAIL_ENABLED=false, notify() still writes the DB row but does NOT
    open SMTP."""
    from app.db.session import SessionLocal
    from app.services.notification_service import notify

    monkeypatch.delenv("EMAIL_ENABLED", raising=False)
    get_settings.cache_clear()
    fake = MagicMock(name="SMTP")
    monkeypatch.setattr(smtplib, "SMTP", fake)
    monkeypatch.setattr(smtplib, "SMTP_SSL", fake)

    db = SessionLocal()
    try:
        row = notify(
            db,
            user_email="quiet@test",
            kind="report.ready",
            title="quiet path",
        )
    finally:
        db.close()
    assert row.id is not None
    fake.assert_not_called()
