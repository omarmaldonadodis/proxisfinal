# alembic/versions/005_add_proxy_health_monitoring.py
"""Add proxy health monitoring tables

Revision ID: 005
Revises: 004
Create Date: 2025-12-15 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create proxy_health_checks table
    op.create_table(
        'proxy_health_checks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('proxy_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('check_type', sa.String(length=50), nullable=False),
        
        # Speed metrics
        sa.Column('latency_ms', sa.Float(), nullable=True),
        sa.Column('download_speed_mbps', sa.Float(), nullable=True),
        sa.Column('upload_speed_mbps', sa.Float(), nullable=True),
        
        # Geo verification
        sa.Column('detected_ip', sa.String(length=45), nullable=True),
        sa.Column('detected_country', sa.String(length=2), nullable=True),
        sa.Column('detected_city', sa.String(length=255), nullable=True),
        sa.Column('detected_isp', sa.String(length=255), nullable=True),
        sa.Column('geo_match', sa.Boolean(), nullable=True),
        
        # Availability
        sa.Column('is_available', sa.Boolean(), nullable=True),
        sa.Column('response_code', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        
        # Session test
        sa.Column('session_id', sa.String(length=255), nullable=True),
        sa.Column('session_test_result', sa.JSON(), nullable=True),
        
        # Metadata
        sa.Column('test_urls', sa.JSON(), nullable=True),
        sa.Column('raw_response', sa.JSON(), nullable=True),
        
        # Timestamp
        sa.Column('checked_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        
        sa.ForeignKeyConstraint(['proxy_id'], ['proxies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index(op.f('ix_proxy_health_checks_proxy_id'), 'proxy_health_checks', ['proxy_id'])
    op.create_index(op.f('ix_proxy_health_checks_status'), 'proxy_health_checks', ['status'])
    op.create_index(op.f('ix_proxy_health_checks_checked_at'), 'proxy_health_checks', ['checked_at'])
    
    # Create proxy_scores table
    op.create_table(
        'proxy_scores',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('proxy_id', sa.Integer(), nullable=False),
        
        # Scores
        sa.Column('overall_score', sa.Float(), default=100.0),
        sa.Column('speed_score', sa.Float(), default=100.0),
        sa.Column('availability_score', sa.Float(), default=100.0),
        sa.Column('geo_accuracy_score', sa.Float(), default=100.0),
        sa.Column('stability_score', sa.Float(), default=100.0),
        
        # Statistics
        sa.Column('total_checks', sa.Integer(), default=0),
        sa.Column('successful_checks', sa.Integer(), default=0),
        sa.Column('failed_checks', sa.Integer(), default=0),
        sa.Column('timeout_checks', sa.Integer(), default=0),
        
        # Latency
        sa.Column('avg_latency', sa.Float(), nullable=True),
        sa.Column('min_latency', sa.Float(), nullable=True),
        sa.Column('max_latency', sa.Float(), nullable=True),
        
        # Uptime
        sa.Column('uptime_percentage', sa.Float(), default=100.0),
        
        # Geo
        sa.Column('geo_mismatch_count', sa.Integer(), default=0),
        
        # Blacklist
        sa.Column('is_blacklisted', sa.Boolean(), default=False),
        sa.Column('blacklist_reason', sa.Text(), nullable=True),
        sa.Column('blacklisted_at', sa.DateTime(timezone=True), nullable=True),
        
        # Auto-recovery
        sa.Column('consecutive_failures', sa.Integer(), default=0),
        sa.Column('last_recovery_attempt', sa.DateTime(timezone=True), nullable=True),
        
        # Timestamps
        sa.Column('last_check_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('score_updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        
        sa.ForeignKeyConstraint(['proxy_id'], ['proxies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('proxy_id')
    )
    
    op.create_index(op.f('ix_proxy_scores_proxy_id'), 'proxy_scores', ['proxy_id'], unique=True)
    op.create_index(op.f('ix_proxy_scores_overall_score'), 'proxy_scores', ['overall_score'])
    op.create_index(op.f('ix_proxy_scores_is_blacklisted'), 'proxy_scores', ['is_blacklisted'])

def downgrade() -> None:
    op.drop_index(op.f('ix_proxy_scores_is_blacklisted'), table_name='proxy_scores')
    op.drop_index(op.f('ix_proxy_scores_overall_score'), table_name='proxy_scores')
    op.drop_index(op.f('ix_proxy_scores_proxy_id'), table_name='proxy_scores')
    op.drop_table('proxy_scores')
    
    op.drop_index(op.f('ix_proxy_health_checks_checked_at'), table_name='proxy_health_checks')
    op.drop_index(op.f('ix_proxy_health_checks_status'), table_name='proxy_health_checks')
    op.drop_index(op.f('ix_proxy_health_checks_proxy_id'), table_name='proxy_health_checks')
    op.drop_table('proxy_health_checks')