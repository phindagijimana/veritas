"""leaderboard grouping metadata

Revision ID: 0008_leaderboard_grouping
Revises: 0007_leaderboard
Create Date: 2026-03-07
"""

from alembic import op
import sqlalchemy as sa

revision = "0008_leaderboard_grouping"
down_revision = "0007_leaderboard"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("leaderboard_entries", sa.Column("disease_group", sa.String(length=128), nullable=True))
    op.add_column("leaderboard_entries", sa.Column("biomarker_group", sa.String(length=128), nullable=True))
    op.create_index(op.f("ix_leaderboard_entries_disease_group"), "leaderboard_entries", ["disease_group"], unique=False)
    op.create_index(op.f("ix_leaderboard_entries_biomarker_group"), "leaderboard_entries", ["biomarker_group"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_leaderboard_entries_biomarker_group"), table_name="leaderboard_entries")
    op.drop_index(op.f("ix_leaderboard_entries_disease_group"), table_name="leaderboard_entries")
    op.drop_column("leaderboard_entries", "biomarker_group")
    op.drop_column("leaderboard_entries", "disease_group")
