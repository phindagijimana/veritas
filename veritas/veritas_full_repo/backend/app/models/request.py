from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ReportStatus, RequestStatus


class EvaluationRequest(Base):
    __tablename__ = "evaluation_requests"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    request_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=RequestStatus.submitted.value)
    report_status: Mapped[str] = mapped_column(String(32), default=ReportStatus.pending.value)
    pipeline_id: Mapped[int] = mapped_column(ForeignKey("pipelines.id"), index=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    admin_note: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)

    pipeline = relationship("Pipeline")
    dataset = relationship("Dataset")
    jobs = relationship("Job", back_populates="request", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="request", cascade="all, delete-orphan")
