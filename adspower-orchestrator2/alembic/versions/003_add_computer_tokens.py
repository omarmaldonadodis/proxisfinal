"""Add computer tokens and dynamic IP

Revision ID: 003
Revises: 002
Create Date: 2024-01-03 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create computer_tokens table
    op.create_table(
        'computer_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('computer_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['computer_id'], ['computers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('computer_id'),
        sa.UniqueConstraint('token')
    )
    op.create_index(op.f('ix_computer_tokens_token'), 'computer_tokens', ['token'], unique=True)
    
    # Make hostname and ip_address nullable
    op.alter_column('computers', 'hostname', nullable=True)
    op.alter_column('computers', 'ip_address', nullable=True)

def downgrade() -> None:
    op.drop_index(op.f('ix_computer_tokens_token'), table_name='computer_tokens')
    op.drop_table('computer_tokens')
    op.alter_column('computers', 'hostname', nullable=False)
    op.alter_column('computers', 'ip_address', nullable=False)
