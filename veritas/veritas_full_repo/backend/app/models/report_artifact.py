from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ReportArtifact(Base):
    __tablename__ = "report_artifacts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("reports.id"), index=True)
    artifact_type: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="ready")
    storage_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    download_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    size_label: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    report = relationship("Report", back_populates="artifacts")
