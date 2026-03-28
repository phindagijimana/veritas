from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HPCConnection(Base):
    __tablename__ = "hpc_connections"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    hostname: Mapped[str] = mapped_column(String(255), index=True)
    username: Mapped[str] = mapped_column(String(120), index=True)
    port: Mapped[int] = mapped_column(default=22)
    ssh_key_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="connected")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
