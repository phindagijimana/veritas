
"""hpc execution layer

Revision ID: 0005_hpc_execution_layer
Revises: 0004_report_pipeline
Create Date: 2026-03-07
"""
from alembic import op
import sqlalchemy as sa


revision = "0005_hpc_execution_layer"
down_revision = "0004_report_pipeline"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.add_column(sa.Column("remote_workdir", sa.String(length=512), nullable=True))
        batch_op.add_column(sa.Column("stdout_path", sa.String(length=512), nullable=True))
        batch_op.add_column(sa.Column("stderr_path", sa.String(length=512), nullable=True))
        batch_op.add_column(sa.Column("last_scheduler_sync_at", sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.drop_column("last_scheduler_sync_at")
        batch_op.drop_column("stderr_path")
        batch_op.drop_column("stdout_path")
        batch_op.drop_column("remote_workdir")
