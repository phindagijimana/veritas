from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ReportStatus


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("evaluation_requests.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default=ReportStatus.pending.value)
    pdf_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    json_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    csv_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    metrics_summary_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    request = relationship("EvaluationRequest", back_populates="reports")
    artifacts = relationship("ReportArtifact", back_populates="report", cascade="all, delete-orphan")
