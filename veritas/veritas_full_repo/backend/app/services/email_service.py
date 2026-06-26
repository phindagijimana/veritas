"""SMTP fan-out for notifications.

Design:
    * Best-effort only. Email failures must NEVER bubble up to the API request
      that triggered the notification — the in-app bell is the source of truth.
    * Synchronous send via stdlib smtplib (no extra deps). For high-volume
      deployments a future change can dispatch this to Celery; the current
      shape — one email per notify() call — is fine for the report-ready
      cadence (minutes to hours per user).
    * Email is OFF by default (`EMAIL_ENABLED=false`). Deployments opt in.
"""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _build_absolute_link(link_page: Optional[str], link_anchor: Optional[str]) -> Optional[str]:
    if not link_page:
        return None
    s = get_settings()
    base = (s.email_app_base_url or "").rstrip("/")
    # Map the in-app `link_page` id to the same paths the UI router uses.
    paths = {
        "home": "/",
        "user": "/dashboard",
        "pipeline": "/pipeline",
        "leaderboard": "/leaderboard",
        "atlas_api": "/atlas/api",
        "atlas_admin": "/atlas/admin",
        "admin": "/admin",
        "tokens": "/tokens",
        "help": "/help",
    }
    path = paths.get(link_page, "/")
    # Anchor (e.g. request_code) is rendered as a path suffix for /leaderboard/:id
    # or a #fragment for other pages.
    if link_anchor:
        if link_page == "leaderboard":
            path = f"/leaderboard/{link_anchor}"
        else:
            path = f"{path}#{link_anchor}"
    return base + path


def _build_message(*, to: str, subject: str, body_text: str, body_html: Optional[str] = None) -> EmailMessage:
    s = get_settings()
    msg = EmailMessage()
    msg["From"] = s.email_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body_text)
    if body_html:
        msg.add_alternative(body_html, subtype="html")
    return msg


def _open_smtp() -> smtplib.SMTP:
    s = get_settings()
    cls = smtplib.SMTP_SSL if s.email_smtp_use_ssl else smtplib.SMTP
    conn = cls(s.email_smtp_host, s.email_smtp_port, timeout=s.email_smtp_timeout_seconds)
    if s.email_smtp_use_tls and not s.email_smtp_use_ssl:
        conn.starttls()
    if s.email_smtp_username:
        conn.login(s.email_smtp_username, s.email_smtp_password)
    return conn


def send_email(*, to: str, subject: str, body_text: str, body_html: Optional[str] = None) -> bool:
    """Send a single message. Returns True on success, False on any failure
    (with the reason logged). Never raises to the caller."""
    if not to:
        return False
    s = get_settings()
    if not s.email_enabled:
        return False
    try:
        msg = _build_message(to=to, subject=subject, body_text=body_text, body_html=body_html)
        conn = _open_smtp()
        try:
            conn.send_message(msg)
        finally:
            try:
                conn.quit()
            except Exception:
                pass
        return True
    except Exception as exc:  # SMTP, DNS, auth, timeout — best-effort
        logger.warning("email send to %r failed: %s", to, exc)
        return False


def send_notification_email(
    *,
    user_email: str,
    kind: str,
    title: str,
    body: Optional[str],
    link_page: Optional[str],
    link_anchor: Optional[str],
) -> bool:
    """Render a notification as an email and try to send it.

    Subject = title. Text body = title + body + optional "Open in Veritas" URL.
    HTML mirrors the same shape with a real anchor tag.
    """
    if not get_settings().email_enabled:
        return False
    link_url = _build_absolute_link(link_page, link_anchor)
    text_lines = [title]
    if body:
        text_lines += ["", body]
    if link_url:
        text_lines += ["", f"Open in Veritas: {link_url}"]
    text_body = "\n".join(text_lines)

    safe_body = (body or "").replace("<", "&lt;").replace(">", "&gt;")
    safe_title = title.replace("<", "&lt;").replace(">", "&gt;")
    html_parts = [
        '<div style="font-family:system-ui,-apple-system,Segoe UI,sans-serif;color:#16325c;">',
        f'<h2 style="margin:0 0 0.5em 0;color:#0f2f6b;">{safe_title}</h2>',
    ]
    if safe_body:
        html_parts.append(f'<p style="margin:0 0 1em 0;">{safe_body}</p>')
    if link_url:
        html_parts.append(
            f'<p><a href="{link_url}" style="background:#0f2f6b;color:#fff;'
            f'padding:0.6em 1em;border-radius:0.5em;text-decoration:none;display:inline-block;">'
            f'Open in Veritas</a></p>'
        )
    html_parts.append(
        '<p style="margin-top:1.5em;color:#5e7394;font-size:0.85em;">'
        "You're receiving this because Veritas notifications are enabled for your account. "
        "Reply to this address only if you're an admin — researchers should use the UI."
        "</p>"
    )
    html_parts.append("</div>")
    body_html = "".join(html_parts)
    return send_email(to=user_email, subject=title, body_text=text_body, body_html=body_html)
