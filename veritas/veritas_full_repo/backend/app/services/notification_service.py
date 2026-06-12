"""In-app notification delivery. Future: optional SMTP fan-out alongside DB write."""

from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.models.notification import Notification


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
) -> Notification:
    """Insert a notification row. Caller may pass commit=False to batch with
    other writes inside a request handler's session."""
    row = Notification(
        user_email=(user_email or "").strip().lower(),
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
    return row


def notify_many(db: Session, recipients: Iterable[str], **kwargs) -> list[Notification]:
    rows = []
    for email in {(e or "").strip().lower() for e in recipients if e}:
        rows.append(notify(db, user_email=email, commit=False, **kwargs))
    if rows:
        db.commit()
    return rows
