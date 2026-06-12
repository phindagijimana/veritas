"""notifications table (in-app delivery)"""
from alembic import op
import sqlalchemy as sa

revision = "0017_notifications"
down_revision = "0016_audit_events"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_email", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.String(length=2048), nullable=True),
        sa.Column("link_page", sa.String(length=64), nullable=True),
        sa.Column("link_anchor", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("read_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_notifications_id", "notifications", ["id"], unique=False)
    op.create_index("ix_notifications_user_email", "notifications", ["user_email"], unique=False)
    op.create_index("ix_notifications_user_unread", "notifications", ["user_email", "read_at"], unique=False)


def downgrade():
    op.drop_index("ix_notifications_user_unread", table_name="notifications")
    op.drop_index("ix_notifications_user_email", table_name="notifications")
    op.drop_index("ix_notifications_id", table_name="notifications")
    op.drop_table("notifications")
