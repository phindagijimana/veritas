"""Audit events and staging operation columns (legacy incremental revision).

Revision ID: 002_audit_ops
Revises: 001_initial
Create Date: 2026-03-28

`001_initial` now creates `atlas_audit_events` and full `atlas_staging_sessions`
(including retry/export columns), so this revision is usually a no-op on upgrade.

It remains **idempotent** for databases that applied an older `001` (metadata
bootstrap without audit or without staging ops columns).

Downgrade is a **no-op**: reversing this revision does not drop columns or the
audit table, because current `001` already includes that schema; `001`'s
downgrade drops the tables wholesale.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "002_audit_ops"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    tables = insp.get_table_names()

    if "atlas_audit_events" not in tables:
        op.create_table(
            "atlas_audit_events",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("actor_principal_id", sa.String(256), nullable=False),
            sa.Column("action", sa.String(64), nullable=False),
            sa.Column("resource_type", sa.String(64), nullable=False),
            sa.Column("resource_id", sa.String(512), nullable=False),
            sa.Column("detail_json", sa.Text(), nullable=True),
            sa.Column("staging_id", sa.String(64), nullable=True),
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
    if "atlas_staging_sessions" in tables:
        cols = {c["name"] for c in insp.get_columns("atlas_staging_sessions")}
        if "retry_count" not in cols:
            op.add_column(
                "atlas_staging_sessions",
                sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
            )
        if "last_attempt_at" not in cols:
            op.add_column(
                "atlas_staging_sessions",
                sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
            )
        if "pennsieve_export_job_id" not in cols:
            op.add_column(
                "atlas_staging_sessions",
                sa.Column("pennsieve_export_job_id", sa.String(256), nullable=True),
            )


def downgrade() -> None:
    pass
