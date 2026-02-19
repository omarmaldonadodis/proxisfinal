"""Add warming scripts tables

Revision ID: 002
Revises: 001
Create Date: 2024-01-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create warming_scripts table
    op.create_table(
        'warming_scripts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('actions', sa.JSON(), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=True, server_default='15'),
        sa.Column('randomize_order', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('repeat_count', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('status', sa.Enum('DRAFT', 'ACTIVE', 'ARCHIVED', name='scriptstatus'), nullable=True, server_default='DRAFT'),
        sa.Column('is_template', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('success_rate', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('times_used', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_warming_scripts_name'), 'warming_scripts', ['name'])
    op.create_index(op.f('ix_warming_scripts_category'), 'warming_scripts', ['category'])
    op.create_index(op.f('ix_warming_scripts_status'), 'warming_scripts', ['status'])
    
    # Create warming_executions table
    op.create_table(
        'warming_executions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('script_id', sa.Integer(), nullable=False),
        sa.Column('profile_id', sa.Integer(), nullable=False),
        sa.Column('computer_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED', name='executionstatus'), nullable=True, server_default='QUEUED'),
        sa.Column('progress', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('actions_completed', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('actions_failed', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('execution_log', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('screenshots', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['script_id'], ['warming_scripts.id'], ),
        sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ),
        sa.ForeignKeyConstraint(['computer_id'], ['computers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_warming_executions_script_id'), 'warming_executions', ['script_id'])
    op.create_index(op.f('ix_warming_executions_profile_id'), 'warming_executions', ['profile_id'])
    op.create_index(op.f('ix_warming_executions_computer_id'), 'warming_executions', ['computer_id'])
    op.create_index(op.f('ix_warming_executions_status'), 'warming_executions', ['status'])
    
    # Create agent_connections table
    op.create_table(
        'agent_connections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('computer_id', sa.Integer(), nullable=False),
        sa.Column('websocket_id', sa.String(length=255), nullable=True),
        sa.Column('is_connected', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('last_heartbeat', sa.DateTime(timezone=True), nullable=True),
        sa.Column('active_browsers', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('max_browsers', sa.Integer(), nullable=True, server_default='10'),
        sa.Column('cpu_usage', sa.Integer(), nullable=True),
        sa.Column('memory_usage', sa.Integer(), nullable=True),
        sa.Column('agent_version', sa.String(length=50), nullable=True),
        sa.Column('capabilities', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['computer_id'], ['computers.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('computer_id'),
        sa.UniqueConstraint('websocket_id')
    )
    op.create_index(op.f('ix_agent_connections_computer_id'), 'agent_connections', ['computer_id'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_agent_connections_computer_id'), table_name='agent_connections')
    op.drop_table('agent_connections')
    
    op.drop_index(op.f('ix_warming_executions_status'), table_name='warming_executions')
    op.drop_index(op.f('ix_warming_executions_computer_id'), table_name='warming_executions')
    op.drop_index(op.f('ix_warming_executions_profile_id'), table_name='warming_executions')
    op.drop_index(op.f('ix_warming_executions_script_id'), table_name='warming_executions')
    op.drop_table('warming_executions')
    
    op.drop_index(op.f('ix_warming_scripts_status'), table_name='warming_scripts')
    op.drop_index(op.f('ix_warming_scripts_category'), table_name='warming_scripts')
    op.drop_index(op.f('ix_warming_scripts_name'), table_name='warming_scripts')
    op.drop_table('warming_scripts')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS scriptstatus')
    op.execute('DROP TYPE IF EXISTS executionstatus')