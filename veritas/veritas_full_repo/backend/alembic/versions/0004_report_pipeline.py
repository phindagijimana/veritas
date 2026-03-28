
"""report pipeline architecture

Revision ID: 0004_report_pipeline
Revises: 0003_dataset_registry
Create Date: 2026-03-07
"""

from alembic import op
import sqlalchemy as sa

revision = '0004_report_pipeline'
down_revision = '0003_dataset_registry'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('reports', sa.Column('metrics_summary_json', sa.Text(), nullable=True))
    op.add_column('reports', sa.Column('published_at', sa.DateTime(), nullable=True))
    op.create_table(
        'report_artifacts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('report_id', sa.Integer(), sa.ForeignKey('reports.id'), nullable=False),
        sa.Column('artifact_type', sa.String(length=32), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('storage_path', sa.String(length=255), nullable=True),
        sa.Column('download_url', sa.String(length=255), nullable=True),
        sa.Column('size_label', sa.String(length=64), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index(op.f('ix_report_artifacts_id'), 'report_artifacts', ['id'], unique=False)
    op.create_index(op.f('ix_report_artifacts_report_id'), 'report_artifacts', ['report_id'], unique=False)
    op.create_index(op.f('ix_report_artifacts_artifact_type'), 'report_artifacts', ['artifact_type'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_report_artifacts_artifact_type'), table_name='report_artifacts')
    op.drop_index(op.f('ix_report_artifacts_report_id'), table_name='report_artifacts')
    op.drop_index(op.f('ix_report_artifacts_id'), table_name='report_artifacts')
    op.drop_table('report_artifacts')
    op.drop_column('reports', 'published_at')
    op.drop_column('reports', 'metrics_summary_json')
