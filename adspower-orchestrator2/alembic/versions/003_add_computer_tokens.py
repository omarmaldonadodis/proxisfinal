"""Add computer tokens and scheduled warmings

Revision ID: 003
Revises: 002
Create Date: 2024-01-03 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

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
    
    # Create scheduled_warmings table
    op.create_table(
        'scheduled_warmings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('script_id', sa.Integer(), nullable=False),
        sa.Column('profile_ids', sa.JSON(), nullable=False),
        sa.Column('frequency', sa.Enum('ONCE', 'DAILY', 'WEEKLY', 'MONTHLY', 'CUSTOM_CRON', name='schedulefrequency'), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('cron_expression', sa.String(length=100), nullable=True),
        sa.Column('timezone', sa.String(length=50), nullable=True, server_default='UTC'),
        sa.Column('days_of_week', sa.JSON(), nullable=True),
        sa.Column('time_of_day', sa.String(length=5), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED', 'PAUSED', name='scheduledwarmingstatus'), nullable=True, server_default='PENDING'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('last_execution_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_execution_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('execution_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('success_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('failure_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('max_executions', sa.Integer(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('notes', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['script_id'], ['warming_scripts.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add scheduled_warming_id to warming_executions
    op.add_column('warming_executions', sa.Column('scheduled_warming_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_warming_executions_scheduled_warming',
        'warming_executions', 'scheduled_warmings',
        ['scheduled_warming_id'], ['id']
    )
    
    # Make hostname and ip_address nullable in computers
    op.alter_column('computers', 'hostname', nullable=True)
    op.alter_column('computers', 'ip_address', nullable=True)

def downgrade() -> None:
    # Drop FK first
    op.drop_constraint('fk_warming_executions_scheduled_warming', 'warming_executions', type_='foreignkey')
    op.drop_column('warming_executions', 'scheduled_warming_id')
    
    # Drop tables
    op.drop_table('scheduled_warmings')
    op.drop_index(op.f('ix_computer_tokens_token'), table_name='computer_tokens')
    op.drop_table('computer_tokens')
    
    # Restore columns
    op.alter_column('computers', 'hostname', nullable=False)
    op.alter_column('computers', 'ip_address', nullable=False)
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS schedulefrequency')
    op.execute('DROP TYPE IF EXISTS scheduledwarmingstatus')