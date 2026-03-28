from __future__ import annotations

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DatasetPermissionGrant(Base):
    """
    DB-backed grants for restricted/private datasets (Phase 3).
    Public datasets do not require rows here.
    """

    __tablename__ = "dataset_permission_grants"
    __table_args__ = (
        UniqueConstraint(
            "dataset_id",
            "principal_type",
            "principal_id",
            "access_level",
            name="uq_dataset_principal_access",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dataset_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    principal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    principal_id: Mapped[str] = mapped_column(String(256), nullable=False)
    access_level: Mapped[str] = mapped_column(String(32), nullable=False)
