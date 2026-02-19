# alembic/versions/001_initial_migration.py
"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create computers table
    op.create_table(
        'computers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('hostname', sa.String(length=255), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=False),
        sa.Column('adspower_api_url', sa.String(length=512), nullable=False),
        sa.Column('adspower_api_key', sa.String(length=512), nullable=False),
        sa.Column('status', sa.Enum('ONLINE', 'OFFLINE', 'MAINTENANCE', 'ERROR', name='computerstatus'), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('max_profiles', sa.Integer(), nullable=True),
        sa.Column('current_profiles', sa.Integer(), nullable=True),
        sa.Column('cpu_cores', sa.Integer(), nullable=True),
        sa.Column('ram_gb', sa.Integer(), nullable=True),
        sa.Column('os_info', sa.String(length=255), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('meta_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_computers_name'), 'computers', ['name'], unique=True)
    
    # Create proxies table
    op.create_table(
        'proxies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('proxy_type', sa.Enum('MOBILE', 'RESIDENTIAL', 'DATACENTER', name='proxytype'), nullable=False),
        sa.Column('host', sa.String(length=255), nullable=False),
        sa.Column('port', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=512), nullable=True),
        sa.Column('password', sa.String(length=512), nullable=True),
        sa.Column('country', sa.String(length=2), nullable=True),
        sa.Column('region', sa.String(length=255), nullable=True),
        sa.Column('city', sa.String(length=255), nullable=True),
        sa.Column('session_id', sa.String(length=255), nullable=True),
        sa.Column('session_lifetime', sa.Integer(), nullable=True),
        sa.Column('sticky_session', sa.Boolean(), nullable=True),
        sa.Column('status', sa.Enum('ACTIVE', 'INACTIVE', 'CHECKING', 'FAILED', name='proxystatus'), nullable=True),
        sa.Column('is_available', sa.Boolean(), nullable=True),
        sa.Column('last_check_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_success_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('success_rate', sa.Float(), nullable=True),
        sa.Column('avg_response_time', sa.Float(), nullable=True),
        sa.Column('total_checks', sa.Integer(), nullable=True),
        sa.Column('failed_checks', sa.Integer(), nullable=True),
        sa.Column('detected_ip', sa.String(length=45), nullable=True),
        sa.Column('detected_country', sa.String(length=2), nullable=True),
        sa.Column('detected_city', sa.String(length=255), nullable=True),
        sa.Column('detected_isp', sa.String(length=255), nullable=True),
        sa.Column('profiles_count', sa.Integer(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('meta_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_proxies_proxy_type'), 'proxies', ['proxy_type'])
    op.create_index(op.f('ix_proxies_country'), 'proxies', ['country'])
    op.create_index(op.f('ix_proxies_status'), 'proxies', ['status'])
    op.create_index(op.f('ix_proxies_session_id'), 'proxies', ['session_id'], unique=True)
    
    # Create profiles table
    op.create_table(
        'profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('adspower_id', sa.String(length=255), nullable=False),
        sa.Column('computer_id', sa.Integer(), nullable=False),
        sa.Column('proxy_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('age', sa.Integer(), nullable=True),
        sa.Column('gender', sa.String(length=10), nullable=True),
        sa.Column('country', sa.String(length=2), nullable=True),
        sa.Column('city', sa.String(length=255), nullable=True),
        sa.Column('timezone', sa.String(length=100), nullable=True),
        sa.Column('language', sa.String(length=10), nullable=True),
        sa.Column('device_type', sa.Enum('DESKTOP', 'MOBILE', name='devicetype'), nullable=True),
        sa.Column('device_name', sa.String(length=255), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('screen_resolution', sa.String(length=50), nullable=True),
        sa.Column('viewport', sa.String(length=50), nullable=True),
        sa.Column('pixel_ratio', sa.String(length=10), nullable=True),
        sa.Column('hardware_concurrency', sa.Integer(), nullable=True),
        sa.Column('device_memory', sa.Integer(), nullable=True),
        sa.Column('platform', sa.String(length=50), nullable=True),
        sa.Column('interests', sa.JSON(), nullable=True),
        sa.Column('browsing_history', sa.JSON(), nullable=True),
        sa.Column('status', sa.Enum('CREATING', 'READY', 'WARMING', 'ACTIVE', 'BUSY', 'ERROR', 'DELETED', name='profilestatus'), nullable=True),
        sa.Column('is_warmed', sa.Boolean(), nullable=True),
        sa.Column('warmup_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_opened_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_sessions', sa.Integer(), nullable=True),
        sa.Column('total_duration_seconds', sa.Integer(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('meta_data', sa.JSON(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['computer_id'], ['computers.id'], ),
        sa.ForeignKeyConstraint(['proxy_id'], ['proxies.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_profiles_adspower_id'), 'profiles', ['adspower_id'], unique=True)
    op.create_index(op.f('ix_profiles_computer_id'), 'profiles', ['computer_id'])
    op.create_index(op.f('ix_profiles_proxy_id'), 'profiles', ['proxy_id'])
    op.create_index(op.f('ix_profiles_country'), 'profiles', ['country'])
    op.create_index(op.f('ix_profiles_status'), 'profiles', ['status'])
    
    # Create tasks table
    op.create_table(
        'tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_type', sa.Enum('CREATE_PROFILE', 'WARMUP_PROFILE', 'PARALLEL_SEARCH', 'PARALLEL_NAVIGATION', 'BULK_CREATE', 'HEALTH_CHECK', 'BACKUP', name='tasktype'), nullable=False),
        sa.Column('celery_task_id', sa.String(length=255), nullable=True),
        sa.Column('profile_id', sa.Integer(), nullable=True),
        sa.Column('computer_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED', name='taskstatus'), nullable=True),
        sa.Column('progress', sa.Integer(), nullable=True),
        sa.Column('input_data', sa.JSON(), nullable=True),
        sa.Column('result_data', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.Column('max_retries', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['computer_id'], ['computers.id'], ),
        sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tasks_celery_task_id'), 'tasks', ['celery_task_id'], unique=True)
    op.create_index(op.f('ix_tasks_profile_id'), 'tasks', ['profile_id'])
    op.create_index(op.f('ix_tasks_computer_id'), 'tasks', ['computer_id'])
    op.create_index(op.f('ix_tasks_task_type'), 'tasks', ['task_type'])
    op.create_index(op.f('ix_tasks_status'), 'tasks', ['status'])
    
    # Create health_checks table
    op.create_table(
        'health_checks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('computer_id', sa.Integer(), nullable=False),
        sa.Column('is_healthy', sa.Boolean(), nullable=True),
        sa.Column('response_time_ms', sa.Float(), nullable=True),
        sa.Column('adspower_status', sa.String(length=20), nullable=True),
        sa.Column('database_status', sa.String(length=20), nullable=True),
        sa.Column('redis_status', sa.String(length=20), nullable=True),
        sa.Column('cpu_usage', sa.Float(), nullable=True),
        sa.Column('memory_usage', sa.Float(), nullable=True),
        sa.Column('disk_usage', sa.Float(), nullable=True),
        sa.Column('active_profiles', sa.Integer(), nullable=True),
        sa.Column('checks_details', sa.JSON(), nullable=True),
        sa.Column('errors', sa.JSON(), nullable=True),
        sa.Column('checked_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['computer_id'], ['computers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_health_checks_computer_id'), 'health_checks', ['computer_id'])
    op.create_index(op.f('ix_health_checks_checked_at'), 'health_checks', ['checked_at'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_health_checks_checked_at'), table_name='health_checks')
    op.drop_index(op.f('ix_health_checks_computer_id'), table_name='health_checks')
    op.drop_table('health_checks')
    
    op.drop_index(op.f('ix_tasks_status'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_task_type'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_computer_id'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_profile_id'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_celery_task_id'), table_name='tasks')
    op.drop_table('tasks')
    
    op.drop_index(op.f('ix_profiles_status'), table_name='profiles')
    op.drop_index(op.f('ix_profiles_country'), table_name='profiles')
    op.drop_index(op.f('ix_profiles_proxy_id'), table_name='profiles')
    op.drop_index(op.f('ix_profiles_computer_id'), table_name='profiles')
    op.drop_index(op.f('ix_profiles_adspower_id'), table_name='profiles')
    op.drop_table('profiles')
    
    op.drop_index(op.f('ix_proxies_session_id'), table_name='proxies')
    op.drop_index(op.f('ix_proxies_status'), table_name='proxies')
    op.drop_index(op.f('ix_proxies_country'), table_name='proxies')
    op.drop_index(op.f('ix_proxies_proxy_type'), table_name='proxies')
    op.drop_table('proxies')
    
    op.drop_index(op.f('ix_computers_name'), table_name='computers')
    op.drop_table('computers')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS computerstatus')
    op.execute('DROP TYPE IF EXISTS proxytype')
    op.execute('DROP TYPE IF EXISTS proxystatus')
    op.execute('DROP TYPE IF EXISTS devicetype')
    op.execute('DROP TYPE IF EXISTS profilestatus')
    op.execute('DROP TYPE IF EXISTS tasktype')
    op.execute('DROP TYPE IF EXISTS taskstatus')
