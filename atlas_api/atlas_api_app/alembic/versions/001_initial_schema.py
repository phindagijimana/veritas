"""Initial schema from SQLAlchemy models.

Revision ID: 001_initial
Revises:
Create Date: 2026-03-28
"""

from __future__ import annotations

from alembic import op

from app.db.base import Base
from app.models import AtlasDataset, DatasetPermissionGrant, StagingSession  # noqa: F401

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
