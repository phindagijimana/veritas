from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    disease_group: Mapped[str] = mapped_column(String(64), index=True)
    collection_name: Mapped[str] = mapped_column(String(120), default="Default Collection")
    version: Mapped[str] = mapped_column(String(24), default="v1")
    modality: Mapped[str] = mapped_column(String(32), default="MRI")
    source: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    subject_count: Mapped[int] = mapped_column(Integer, default=0)
    hpc_root_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    manifest_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    label_schema: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    qc_status: Mapped[str] = mapped_column(String(32), default="Curated")
    benchmark_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
