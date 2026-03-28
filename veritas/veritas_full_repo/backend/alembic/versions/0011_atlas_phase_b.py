
"""atlas phase b

Revision ID: 0011_atlas_phase_b
Revises: 0010_atlas_phase_a
Create Date: 2026-03-10
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_atlas_phase_b"
down_revision = "0010_atlas_phase_a"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("evaluation_requests", sa.Column("atlas_approval_status", sa.String(length=64), nullable=True))
    op.add_column("evaluation_requests", sa.Column("atlas_last_checked_at", sa.DateTime(), nullable=True))
    op.add_column("jobs", sa.Column("staging_manifest_url", sa.String(length=512), nullable=True))
    op.add_column("jobs", sa.Column("staging_error", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("staging_script_path", sa.String(length=512), nullable=True))
    op.add_column("jobs", sa.Column("stage_env_path", sa.String(length=512), nullable=True))


def downgrade():
    op.drop_column("jobs", "stage_env_path")
    op.drop_column("jobs", "staging_script_path")
    op.drop_column("jobs", "staging_error")
    op.drop_column("jobs", "staging_manifest_url")
    op.drop_column("evaluation_requests", "atlas_last_checked_at")
    op.drop_column("evaluation_requests", "atlas_approval_status")
