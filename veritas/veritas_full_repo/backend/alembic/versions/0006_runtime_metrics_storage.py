"""runtime metrics storage

Revision ID: 0006_runtime_metrics_storage
Revises: 0005_hpc_execution_layer
Create Date: 2026-03-07
"""

from alembic import op
import sqlalchemy as sa

revision = "0006_runtime_metrics_storage"
down_revision = "0005_hpc_execution_layer"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("pipeline_ref", sa.String(length=255), nullable=True))
    op.add_column("jobs", sa.Column("dataset_name", sa.String(length=255), nullable=True))
    op.add_column("jobs", sa.Column("runtime_engine", sa.String(length=32), nullable=True))
    op.add_column("jobs", sa.Column("runtime_manifest_path", sa.String(length=512), nullable=True))
    op.add_column("jobs", sa.Column("metrics_path", sa.String(length=512), nullable=True))
    op.add_column("jobs", sa.Column("results_csv_path", sa.String(length=512), nullable=True))
    op.add_column("jobs", sa.Column("report_path", sa.String(length=512), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "report_path")
    op.drop_column("jobs", "results_csv_path")
    op.drop_column("jobs", "metrics_path")
    op.drop_column("jobs", "runtime_manifest_path")
    op.drop_column("jobs", "runtime_engine")
    op.drop_column("jobs", "dataset_name")
    op.drop_column("jobs", "pipeline_ref")
