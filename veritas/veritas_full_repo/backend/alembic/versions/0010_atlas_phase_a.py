"""atlas phase a

Revision ID: 0010_atlas_phase_a
Revises: 0009_leaderboard_backfill
Create Date: 2026-03-10
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_atlas_phase_a"
down_revision = "0009_leaderboard_backfill"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("evaluation_requests", sa.Column("atlas_dataset_id", sa.String(), nullable=True))
    op.add_column("evaluation_requests", sa.Column("atlas_dataset_version", sa.String(), nullable=True))
    op.add_column("evaluation_requests", sa.Column("dataset_source", sa.String(), nullable=False, server_default="atlas"))
    op.add_column("evaluation_requests", sa.Column("dataset_access_status", sa.String(), nullable=False, server_default="pending"))

    op.add_column("jobs", sa.Column("atlas_staging_id", sa.String(), nullable=True))
    op.add_column("jobs", sa.Column("staging_status", sa.String(), nullable=False, server_default="not_requested"))
    op.add_column("jobs", sa.Column("staged_dataset_path", sa.String(), nullable=True))
    op.add_column("jobs", sa.Column("staging_started_at", sa.DateTime(), nullable=True))
    op.add_column("jobs", sa.Column("staging_completed_at", sa.DateTime(), nullable=True))
    op.add_column("jobs", sa.Column("staging_credentials_ref", sa.String(), nullable=True))
    op.add_column("jobs", sa.Column("atlas_manifest_ref", sa.String(), nullable=True))


def downgrade():
    op.drop_column("jobs", "atlas_manifest_ref")
    op.drop_column("jobs", "staging_credentials_ref")
    op.drop_column("jobs", "staging_completed_at")
    op.drop_column("jobs", "staging_started_at")
    op.drop_column("jobs", "staged_dataset_path")
    op.drop_column("jobs", "staging_status")
    op.drop_column("jobs", "atlas_staging_id")

    op.drop_column("evaluation_requests", "dataset_access_status")
    op.drop_column("evaluation_requests", "dataset_source")
    op.drop_column("evaluation_requests", "atlas_dataset_version")
    op.drop_column("evaluation_requests", "atlas_dataset_id")
