"""expand datasets into disease registry

Revision ID: 0003_dataset_registry
Revises: 0002_hpc_connections
Create Date: 2026-03-07
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0003_dataset_registry"
down_revision = "0002_hpc_connections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("datasets", sa.Column("code", sa.String(length=32), nullable=True))
    op.add_column("datasets", sa.Column("disease_group", sa.String(length=64), nullable=True))
    op.add_column("datasets", sa.Column("collection_name", sa.String(length=120), nullable=True, server_default="Default Collection"))
    op.add_column("datasets", sa.Column("version", sa.String(length=24), nullable=True, server_default="v1"))
    op.add_column("datasets", sa.Column("source", sa.String(length=120), nullable=True))
    op.add_column("datasets", sa.Column("subject_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("datasets", sa.Column("hpc_root_path", sa.String(length=255), nullable=True))
    op.add_column("datasets", sa.Column("manifest_path", sa.String(length=255), nullable=True))
    op.add_column("datasets", sa.Column("label_schema", sa.String(length=120), nullable=True))
    op.add_column("datasets", sa.Column("qc_status", sa.String(length=32), nullable=False, server_default="Curated"))
    op.add_column("datasets", sa.Column("benchmark_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_index("ix_datasets_code", "datasets", ["code"], unique=True)
    op.create_index("ix_datasets_disease_group", "datasets", ["disease_group"], unique=False)

    op.execute(
        """
        UPDATE datasets
        SET code = UPPER(REPLACE(REPLACE(name, ' ', '_'), '-', '_')),
            disease_group = COALESCE(disease_group, 'General'),
            collection_name = COALESCE(collection_name, name),
            version = COALESCE(version, 'v1'),
            qc_status = COALESCE(qc_status, 'Curated')
        """
    )

    op.alter_column("datasets", "code", nullable=False)
    op.alter_column("datasets", "disease_group", nullable=False)
    op.alter_column("datasets", "collection_name", nullable=False)
    op.alter_column("datasets", "version", nullable=False)


def downgrade() -> None:
    op.drop_index("ix_datasets_disease_group", table_name="datasets")
    op.drop_index("ix_datasets_code", table_name="datasets")
    op.drop_column("datasets", "benchmark_enabled")
    op.drop_column("datasets", "qc_status")
    op.drop_column("datasets", "label_schema")
    op.drop_column("datasets", "manifest_path")
    op.drop_column("datasets", "hpc_root_path")
    op.drop_column("datasets", "subject_count")
    op.drop_column("datasets", "source")
    op.drop_column("datasets", "version")
    op.drop_column("datasets", "collection_name")
    op.drop_column("datasets", "disease_group")
    op.drop_column("datasets", "code")
