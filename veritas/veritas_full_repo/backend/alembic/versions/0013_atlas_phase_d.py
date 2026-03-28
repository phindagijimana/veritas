"""atlas phase d transfer validation fields"""
from alembic import op
import sqlalchemy as sa

revision = "0013_atlas_phase_d"
down_revision = "0012_atlas_phase_c"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("jobs", sa.Column("transfer_log", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("validation_status", sa.String(length=64), nullable=True))
    op.add_column("evaluation_requests", sa.Column("staging_validated_at", sa.DateTime(), nullable=True))

def downgrade():
    op.drop_column("evaluation_requests", "staging_validated_at")
    op.drop_column("jobs", "validation_status")
    op.drop_column("jobs", "transfer_log")
