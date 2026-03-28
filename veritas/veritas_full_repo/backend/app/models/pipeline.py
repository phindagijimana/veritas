from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Pipeline(Base):
    __tablename__ = "pipelines"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(160))
    image: Mapped[str] = mapped_column(String(255), index=True)
    modality: Mapped[str] = mapped_column(String(32), default="MRI")
    description: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    yaml_definition: Mapped[str] = mapped_column(Text())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
