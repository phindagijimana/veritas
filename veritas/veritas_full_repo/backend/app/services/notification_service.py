"""In-app notification delivery + best-effort SMTP fan-out.

Every call to notify() writes a DB row (the source of truth surfaced in the
UI bell) and then, if EMAIL_ENABLED, tries to send a matching email. SMTP
failures are swallowed — the in-app notification is considered delivered as
soon as the DB write commits.
"""

from __future__ import annotations

import logging
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.services.email_service import send_notification_email

logger = logging.getLogger(__name__)


def notify(
    db: Session,
    *,
    user_email: str,
    kind: str,
    title: str,
    body: Optional[str] = None,
    link_page: Optional[str] = None,
    link_anchor: Optional[str] = None,
    commit: bool = True,
    send_email: bool = True,
) -> Notification:
    """Insert a notification row. Caller may pass commit=False to batch with
    other writes inside a request handler's session.

    If commit=True and send_email=True, also fires send_notification_email()
    once the DB row is durable. Email failures are logged but never raised.
    """
    user_email_norm = (user_email or "").strip().lower()
    row = Notification(
        user_email=user_email_norm,
        kind=kind,
        title=title,
        body=body,
        link_page=link_page,
        link_anchor=link_anchor,
    )
    db.add(row)
    if commit:
        db.commit()
        db.refresh(row)
        if send_email and user_email_norm:
            try:
                send_notification_email(
                    user_email=user_email_norm,
                    kind=kind,
                    title=title,
                    body=body,
                    link_page=link_page,
                    link_anchor=link_anchor,
                )
            except Exception:  # belt-and-suspenders; send_notification_email already swallows
                logger.exception("notification email dispatch failed; in-app delivery succeeded")
    return row


def notify_many(db: Session, recipients: Iterable[str], **kwargs) -> list[Notification]:
    rows = []
    for email in {(e or "").strip().lower() for e in recipients if e}:
        rows.append(notify(db, user_email=email, commit=False, send_email=False, **kwargs))
    if rows:
        db.commit()
    return rows
