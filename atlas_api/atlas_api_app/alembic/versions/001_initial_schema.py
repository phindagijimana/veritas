"""Initial schema: explicit DDL for Atlas tables.

Revision ID: 001_initial
Revises:
Create Date: 2026-03-28

Replaces earlier metadata.create_all bootstrap so upgrades/downgrades are reviewable.
Revision id is unchanged; existing deployments keep their alembic stamp.

`002_audit_ops` remains for databases that applied an older 001 (partial metadata)
and still need the audit table or staging columns — it is idempotent.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "atlas_datasets",
        sa.Column("dataset_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("visibility", sa.String(length=32), nullable=False),
        sa.Column("access_class", sa.String(length=32), nullable=False),
        sa.Column("storage_provider", sa.String(length=32), nullable=False),
        sa.Column("canonical_source", sa.String(length=64), nullable=False, server_default="pennsieve"),
        sa.Column("download_url", sa.Text(), nullable=True),
        sa.Column("staging_allowed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("allowed_compute_targets", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("pennsieve_package_id", sa.String(length=256), nullable=True),
        sa.PrimaryKeyConstraint("dataset_id"),
    )

    op.create_table(
        "dataset_permission_grants",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("dataset_id", sa.String(length=128), nullable=False),
        sa.Column("principal_type", sa.String(length=32), nullable=False),
        sa.Column("principal_id", sa.String(length=256), nullable=False),
        sa.Column("access_level", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "dataset_id",
            "principal_type",
            "principal_id",
            "access_level",
            name="uq_dataset_principal_access",
        ),
    )
    op.create_index(
        op.f("ix_dataset_permission_grants_dataset_id"),
        "dataset_permission_grants",
        ["dataset_id"],
        unique=False,
    )

    op.create_table(
        "atlas_staging_sessions",
        sa.Column("staging_id", sa.String(length=64), nullable=False),
        sa.Column("dataset_id", sa.String(length=128), nullable=False),
        sa.Column("request_id", sa.String(length=256), nullable=True),
        sa.Column("compute_target", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("token", sa.Text(), nullable=True),
        sa.Column("manifest_url", sa.Text(), nullable=True),
        sa.Column("principal_id", sa.String(length=256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("transfer_status", sa.String(length=32), nullable=False, server_default="ready"),
        sa.Column("transfer_log", sa.Text(), nullable=True),
        sa.Column("manifest_files_json", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pennsieve_export_job_id", sa.String(length=256), nullable=True),
        sa.PrimaryKeyConstraint("staging_id"),
    )
    op.create_index(
        op.f("ix_atlas_staging_sessions_dataset_id"),
        "atlas_staging_sessions",
        ["dataset_id"],
        unique=False,
    )

    op.create_table(
        "atlas_audit_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("actor_principal_id", sa.String(length=256), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=512), nullable=False),
        sa.Column("detail_json", sa.Text(), nullable=True),
        sa.Column("staging_id", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_atlas_audit_events_created_at"),
        "atlas_audit_events",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_atlas_audit_events_action"),
        "atlas_audit_events",
        ["action"],
        unique=False,
    )
    op.create_index(
        op.f("ix_atlas_audit_events_staging_id"),
        "atlas_audit_events",
        ["staging_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_atlas_audit_events_staging_id"), table_name="atlas_audit_events")
    op.drop_index(op.f("ix_atlas_audit_events_action"), table_name="atlas_audit_events")
    op.drop_index(op.f("ix_atlas_audit_events_created_at"), table_name="atlas_audit_events")
    op.drop_table("atlas_audit_events")

    op.drop_index(op.f("ix_atlas_staging_sessions_dataset_id"), table_name="atlas_staging_sessions")
    op.drop_table("atlas_staging_sessions")

    op.drop_index(op.f("ix_dataset_permission_grants_dataset_id"), table_name="dataset_permission_grants")
    op.drop_table("dataset_permission_grants")

    op.drop_table("atlas_datasets")
