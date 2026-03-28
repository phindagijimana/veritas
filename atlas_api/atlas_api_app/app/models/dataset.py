from __future__ import annotations

from typing import Any, List, Optional

from sqlalchemy import JSON, Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def dataset_storage_homes(row: "AtlasDataset") -> list[dict[str, Any]]:
    """Primary + optional secondary durable locations for API and Veritas payloads."""
    primary: dict[str, Any] = {
        "role": "primary",
        "storage_provider": row.storage_provider,
        "canonical_source": row.canonical_source,
        "pennsieve_package_id": row.pennsieve_package_id,
        "download_url": row.download_url,
    }
    out = [primary]
    if (row.secondary_storage_provider or "").strip():
        out.append(
            {
                "role": "secondary",
                "storage_provider": (row.secondary_storage_provider or "").strip(),
                "canonical_source": (row.secondary_canonical_source or "").strip() or None,
                "location_ref": (row.secondary_location_ref or "").strip() or None,
            }
        )
    return out


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

    # Optional second permanent home (mirror on HPC, second object store, etc.).
    secondary_storage_provider: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    secondary_canonical_source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    secondary_location_ref: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def storage_homes(self) -> list[dict[str, Any]]:
        return dataset_storage_homes(self)
