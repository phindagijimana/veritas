from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.models.notification import Notification
from app.schemas.notification import NotificationListResponse, NotificationRead

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _to_read(row: Notification) -> NotificationRead:
    return NotificationRead(
        id=row.id,
        kind=row.kind,
        title=row.title,
        body=row.body,
        link_page=row.link_page,
        link_anchor=row.link_anchor,
        created_at=row.created_at,
        read_at=row.read_at,
        is_read=row.read_at is not None,
    )


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    limit: int = Query(50, ge=1, le=200),
    unread_only: bool = Query(False),
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    email = current.email.lower()
    q = db.query(Notification).filter(Notification.user_email == email)
    if unread_only:
        q = q.filter(Notification.read_at.is_(None))
    rows = q.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit).all()
    unread_count = (
        db.query(Notification)
        .filter(Notification.user_email == email, Notification.read_at.is_(None))
        .count()
    )
    return {"data": [_to_read(r) for r in rows], "unread_count": unread_count}


@router.post("/{notification_id}/read", response_model=NotificationListResponse)
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    row = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_email == current.email.lower(),
        )
        .one_or_none()
    )
    if row is None:
        # Don't disclose existence of other users' notifications.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")
    if row.read_at is None:
        row.read_at = datetime.utcnow()
        db.add(row)
        db.commit()
    return list_notifications(limit=50, unread_only=False, db=db, current=current)


@router.post("/read-all", response_model=NotificationListResponse)
def mark_all_read(
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    email = current.email.lower()
    now = datetime.utcnow()
    db.query(Notification).filter(
        Notification.user_email == email, Notification.read_at.is_(None)
    ).update({Notification.read_at: now})
    db.commit()
    return list_notifications(limit=50, unread_only=False, db=db, current=current)
