"""leaderboard

Revision ID: 0007_leaderboard
Revises: 0006_runtime_metrics_storage
Create Date: 2026-03-07
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_leaderboard"
down_revision = "0006_runtime_metrics_storage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "leaderboard_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.Integer(), sa.ForeignKey("evaluation_requests.id"), nullable=False),
        sa.Column("report_id", sa.Integer(), sa.ForeignKey("reports.id"), nullable=True),
        sa.Column("consented", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("pipeline_name", sa.String(length=255), nullable=False),
        sa.Column("dataset_name", sa.String(length=255), nullable=False),
        sa.Column("primary_metric", sa.String(length=64), nullable=False, server_default="overall_score"),
        sa.Column("score", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("request_id"),
    )
    op.create_index(op.f("ix_leaderboard_entries_id"), "leaderboard_entries", ["id"], unique=False)
    op.create_index(op.f("ix_leaderboard_entries_request_id"), "leaderboard_entries", ["request_id"], unique=False)
    op.create_index(op.f("ix_leaderboard_entries_report_id"), "leaderboard_entries", ["report_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_leaderboard_entries_report_id"), table_name="leaderboard_entries")
    op.drop_index(op.f("ix_leaderboard_entries_request_id"), table_name="leaderboard_entries")
    op.drop_index(op.f("ix_leaderboard_entries_id"), table_name="leaderboard_entries")
    op.drop_table("leaderboard_entries")
