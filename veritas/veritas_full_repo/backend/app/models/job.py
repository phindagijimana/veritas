from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import JobStatus


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("evaluation_requests.id"), index=True)
    job_name: Mapped[str] = mapped_column(String(160), index=True)
    scheduler_job_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default=JobStatus.created.value)
    partition: Mapped[str] = mapped_column(String(64), default="gpu")
    resources: Mapped[str] = mapped_column(Text(), default="1 GPU • 16 CPU • 64 GB RAM")
    pipeline_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    dataset_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    runtime_engine: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    sbatch_script: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    remote_workdir: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    stdout_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    stderr_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    runtime_manifest_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    metrics_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    results_csv_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    report_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    last_scheduler_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    request = relationship("EvaluationRequest", back_populates="jobs")
