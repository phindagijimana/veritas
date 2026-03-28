"""add hpc connections

Revision ID: 0002_hpc_connections
Revises: 0001_initial
Create Date: 2026-03-07 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0002_hpc_connections'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'hpc_connections',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('hostname', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=120), nullable=False),
        sa.Column('port', sa.Integer(), nullable=False, server_default='22'),
        sa.Column('ssh_key_reference', sa.String(length=255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='connected'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)')),
    )
    op.create_index(op.f('ix_hpc_connections_id'), 'hpc_connections', ['id'], unique=False)
    op.create_index(op.f('ix_hpc_connections_hostname'), 'hpc_connections', ['hostname'], unique=False)
    op.create_index(op.f('ix_hpc_connections_username'), 'hpc_connections', ['username'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_hpc_connections_username'), table_name='hpc_connections')
    op.drop_index(op.f('ix_hpc_connections_hostname'), table_name='hpc_connections')
    op.drop_index(op.f('ix_hpc_connections_id'), table_name='hpc_connections')
    op.drop_table('hpc_connections')
