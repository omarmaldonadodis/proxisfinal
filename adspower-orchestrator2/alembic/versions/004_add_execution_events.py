# adspower-orchestrator2/alembic/versions/004_add_execution_events.py
"""Add execution events table

Revision ID: 004
Revises: 003
Create Date: 2025-01-15 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create execution_events table
    op.create_table(
        'execution_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.String(length=255), nullable=False),
        sa.Column('execution_id', sa.Integer(), nullable=False),
        sa.Column('computer_id', sa.Integer(), nullable=False),
        sa.Column('profile_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.Enum('critical', 'warning', 'info', 'debug', name='eventseveritydb'), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('current_url', sa.Text(), nullable=True),
        sa.Column('page_title', sa.String(length=500), nullable=True),
        sa.Column('screenshot_path', sa.String(length=500), nullable=True),
        sa.Column('requires_manual_intervention', sa.Boolean(), nullable=True),
        sa.Column('can_retry', sa.Boolean(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('suggested_action', sa.Text(), nullable=True),
        sa.Column('action_index', sa.Integer(), nullable=True),
        sa.Column('action_type', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['execution_id'], ['warming_executions.id'], ),
        sa.ForeignKeyConstraint(['computer_id'], ['computers.id'], ),
        sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index(op.f('ix_execution_events_event_id'), 'execution_events', ['event_id'], unique=True)
    op.create_index(op.f('ix_execution_events_execution_id'), 'execution_events', ['execution_id'])
    op.create_index(op.f('ix_execution_events_computer_id'), 'execution_events', ['computer_id'])
    op.create_index(op.f('ix_execution_events_profile_id'), 'execution_events', ['profile_id'])
    op.create_index(op.f('ix_execution_events_event_type'), 'execution_events', ['event_type'])
    op.create_index(op.f('ix_execution_events_severity'), 'execution_events', ['severity'])
    op.create_index(op.f('ix_execution_events_requires_manual'), 'execution_events', ['requires_manual_intervention'])
    op.create_index(op.f('ix_execution_events_created_at'), 'execution_events', ['created_at'])

def downgrade() -> None:
    op.drop_index(op.f('ix_execution_events_created_at'), table_name='execution_events')
    op.drop_index(op.f('ix_execution_events_requires_manual'), table_name='execution_events')
    op.drop_index(op.f('ix_execution_events_severity'), table_name='execution_events')
    op.drop_index(op.f('ix_execution_events_event_type'), table_name='execution_events')
    op.drop_index(op.f('ix_execution_events_profile_id'), table_name='execution_events')
    op.drop_index(op.f('ix_execution_events_computer_id'), table_name='execution_events')
    op.drop_index(op.f('ix_execution_events_execution_id'), table_name='execution_events')
    op.drop_index(op.f('ix_execution_events_event_id'), table_name='execution_events')
    op.drop_table('execution_events')
    
    op.execute('DROP TYPE IF EXISTS eventseveritydb')