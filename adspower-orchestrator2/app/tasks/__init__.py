from celery import Celery
from app.config import settings
from loguru import logger

celery_app = Celery(
    'adspower_orchestrator',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        'app.tasks.backup_tasks',
        'app.tasks.health_tasks',
        'app.tasks.proxy_rotation_tasks',
        'app.tasks.profile_verification',
    ]
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.conf.beat_schedule = {
        # Rotación + health check de proxies cada 15 min
        'auto-rotate-slow-proxies': {
            'task': 'tasks.auto_rotate_slow_proxies',
            'schedule': 900.0,
        },
        # Health check de computers cada 5 min
        'health-check-computers': {
            'task': 'tasks.health_check_all_computers',
            'schedule': 300.0,
        },
        # Backup diario
        'backup-database-daily': {
            'task': 'tasks.backup_database',
            'schedule': 86400.0,
        },
        # Verificación de perfiles cada 3 horas
        'verify-all-profiles': {
            'task': 'tasks.verify_all_profiles',
            'schedule': 18000.0,
        },
    }
    logger.info("✓ Celery Beat schedule configured")