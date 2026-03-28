from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LeaderboardEntry(Base):
    __tablename__ = "leaderboard_entries"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("evaluation_requests.id"), unique=True, index=True)
    report_id: Mapped[Optional[int]] = mapped_column(ForeignKey("reports.id"), nullable=True, index=True)
    consented: Mapped[bool] = mapped_column(Boolean, default=True)
    pipeline_name: Mapped[str] = mapped_column(String(255))
    dataset_name: Mapped[str] = mapped_column(String(255))
    disease_group: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    biomarker_group: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    primary_metric: Mapped[str] = mapped_column(String(64), default="overall_score")
    score: Mapped[float] = mapped_column(Numeric(10, 4), default=0.0)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    request = relationship("EvaluationRequest")
    report = relationship("Report")
