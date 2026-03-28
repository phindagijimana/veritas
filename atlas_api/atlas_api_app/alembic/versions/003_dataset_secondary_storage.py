"""Optional second permanent storage location per dataset.

Revision ID: 003_secondary_storage
Revises: 002_audit_ops
Create Date: 2026-03-27

Primary home remains storage_provider + canonical_source + pennsieve_package_id / download_url.
When set, secondary_* describes an additional durable copy (e.g. HPC POSIX path or mirror id).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "003_secondary_storage"
down_revision = "002_audit_ops"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "atlas_datasets",
        sa.Column("secondary_storage_provider", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "atlas_datasets",
        sa.Column("secondary_canonical_source", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "atlas_datasets",
        sa.Column("secondary_location_ref", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("atlas_datasets", "secondary_location_ref")
    op.drop_column("atlas_datasets", "secondary_canonical_source")
    op.drop_column("atlas_datasets", "secondary_storage_provider")
