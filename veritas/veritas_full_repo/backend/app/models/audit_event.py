from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditEvent(Base):
    """Append-only record of state-changing actions. Compliance-grade audit
    trail: who did what to which subject and when, with optional payload diff.
    Never updated or deleted by application code — admins can read but not edit."""

    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    actor_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    actor_role: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    auth_method: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    subject_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    subject_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, index=True)
    http_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    route: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    detail: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
