"""initial

Revision ID: 0001_initial
Revises:
Create Date: 2026-03-07 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "datasets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("modality", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_datasets_name", "datasets", ["name"], unique=True)

    op.create_table(
        "pipelines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("image", sa.String(length=255), nullable=False),
        sa.Column("modality", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("yaml_definition", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_pipelines_name", "pipelines", ["name"], unique=True)
    op.create_index("ix_pipelines_image", "pipelines", ["image"], unique=False)

    op.create_table(
        "evaluation_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_code", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("report_status", sa.String(length=32), nullable=False),
        sa.Column("pipeline_id", sa.Integer(), sa.ForeignKey("pipelines.id"), nullable=False),
        sa.Column("dataset_id", sa.Integer(), sa.ForeignKey("datasets.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("admin_note", sa.Text(), nullable=True),
    )
    op.create_index("ix_evaluation_requests_request_code", "evaluation_requests", ["request_code"], unique=True)

    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.Integer(), sa.ForeignKey("evaluation_requests.id"), nullable=False),
        sa.Column("job_name", sa.String(length=160), nullable=False),
        sa.Column("scheduler_job_id", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("partition", sa.String(length=64), nullable=False),
        sa.Column("resources", sa.Text(), nullable=False),
        sa.Column("sbatch_script", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.Integer(), sa.ForeignKey("evaluation_requests.id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("pdf_path", sa.String(length=255), nullable=True),
        sa.Column("json_path", sa.String(length=255), nullable=True),
        sa.Column("csv_path", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("reports")
    op.drop_table("jobs")
    op.drop_index("ix_evaluation_requests_request_code", table_name="evaluation_requests")
    op.drop_table("evaluation_requests")
    op.drop_index("ix_pipelines_image", table_name="pipelines")
    op.drop_index("ix_pipelines_name", table_name="pipelines")
    op.drop_table("pipelines")
    op.drop_index("ix_datasets_name", table_name="datasets")
    op.drop_table("datasets")
