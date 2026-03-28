from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StagingSession(Base):
    __tablename__ = "atlas_staging_sessions"

    staging_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(String(128), index=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    compute_target: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32))
    token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    manifest_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    principal_id: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    transfer_status: Mapped[str] = mapped_column(String(32), default="ready", server_default="ready")
    transfer_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    manifest_files_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    pennsieve_export_job_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)