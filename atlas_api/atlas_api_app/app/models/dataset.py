from __future__ import annotations

from typing import Any, List, Optional

from sqlalchemy import JSON, Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AtlasDataset(Base):
    __tablename__ = "atlas_datasets"

    dataset_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(512))
    visibility: Mapped[str] = mapped_column(String(32))
    access_class: Mapped[str] = mapped_column(String(32))
    storage_provider: Mapped[str] = mapped_column(String(32))
    canonical_source: Mapped[str] = mapped_column(String(64), default="pennsieve")
    download_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    staging_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    allowed_compute_targets: Mapped[List[Any]] = mapped_column(JSON, default=list)
    pennsieve_package_id: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
