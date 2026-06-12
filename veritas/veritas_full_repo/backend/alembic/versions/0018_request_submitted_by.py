"""evaluation_requests.submitted_by — persist requester email for notifications"""
from alembic import op
import sqlalchemy as sa

revision = "0018_request_submitted_by"
down_revision = "0017_notifications"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("evaluation_requests") as batch_op:
        batch_op.add_column(sa.Column("submitted_by", sa.String(length=255), nullable=True))
    op.create_index(
        "ix_evaluation_requests_submitted_by",
        "evaluation_requests",
        ["submitted_by"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_evaluation_requests_submitted_by", table_name="evaluation_requests")
    with op.batch_alter_table("evaluation_requests") as batch_op:
        batch_op.drop_column("submitted_by")
