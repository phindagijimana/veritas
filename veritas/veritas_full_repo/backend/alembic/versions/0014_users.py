"""users table for real auth (Phase 1)"""
import os

from alembic import op
import sqlalchemy as sa

revision = "0014_users"
down_revision = "0013_atlas_phase_d"
branch_labels = None
depends_on = None


_DEV_SEED = [
    # (email, plain_password, full_name, role)
    ("dev@veritas.local", "dev-password", "Development User", "admin"),
    ("admin@veritas.local", "admin-password", "Veritas Admin", "admin"),
    ("researcher@veritas.local", "researcher-password", "Veritas Researcher", "researcher"),
]


def _is_production() -> bool:
    return (os.environ.get("APP_ENV") or "").strip().lower() == "production"


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="researcher"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    if _is_production():
        return

    from app.core.passwords import hash_password

    bind = op.get_bind()
    users_table = sa.table(
        "users",
        sa.column("email", sa.String),
        sa.column("password_hash", sa.String),
        sa.column("full_name", sa.String),
        sa.column("role", sa.String),
        sa.column("is_active", sa.Boolean),
    )
    rows = [
        {
            "email": email,
            "password_hash": hash_password(password),
            "full_name": full_name,
            "role": role,
            "is_active": True,
        }
        for (email, password, full_name, role) in _DEV_SEED
    ]
    op.bulk_insert(users_table, rows)


def downgrade():
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")
