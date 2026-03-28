"""atlas phase c staging detail fields"""
from alembic import op
import sqlalchemy as sa

revision = "0012_atlas_phase_c"
down_revision = "0011_atlas_phase_b"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("evaluation_requests", sa.Column("staging_message", sa.String(length=255), nullable=True))
    op.add_column("jobs", sa.Column("pennsieve_manifest_url", sa.String(length=512), nullable=True))

def downgrade():
    op.drop_column("jobs", "pennsieve_manifest_url")
    op.drop_column("evaluation_requests", "staging_message")
