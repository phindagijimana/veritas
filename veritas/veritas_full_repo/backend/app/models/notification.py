from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Notification(Base):
    """In-app notification delivered to a single user (by email).

    No FK to users — users may be deleted or referenced before they exist
    (e.g. invites). Reads use the email string directly.
    """

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    # Stable machine name like "report.ready", "role.changed", "password.reset".
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    # Optional in-app navigation target, e.g. "admin" or "tokens".
    link_page: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    link_anchor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


# Composite index used by /notifications (latest unread first per user).
Index("ix_notifications_user_unread", Notification.user_email, Notification.read_at)
