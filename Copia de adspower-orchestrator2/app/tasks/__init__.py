# app/tasks/__init__.py
from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown
from app.config import settings
import asyncio
from loguru import logger

celery_app = Celery(
    'adspower_orchestrator',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        'app.tasks.backup_tasks',
        'app.tasks.health_tasks',
        'app.tasks.scheduled_warming_tasks',
        'app.tasks.proxy_rotation_tasks',  
    ]
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    task_soft_time_limit=3000,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)

# ========================================
# Inicialización Redis Pub/Sub
# ========================================
@worker_process_init.connect
def init_worker(**kwargs):
    logger.info("🚀 Celery worker process initializing...")
    from app.core.redis_messaging import redis_messaging
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.run_until_complete(redis_messaging.connect())
    logger.info("✓ Redis Pub/Sub connected in Celery worker")

@worker_process_shutdown.connect
def shutdown_worker(**kwargs):
    logger.info("🛑 Celery worker process shutting down...")
    from app.core.redis_messaging import redis_messaging
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(redis_messaging.stop())
        logger.info("✓ Redis Pub/Sub disconnected")
    except Exception as e:
        logger.error(f"Error disconnecting Redis: {e}")

# ========================================
# Configurar Beat Schedule después de cargar módulos
# ========================================
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    from app.tasks.scheduled_warming_tasks import BEAT_SCHEDULE
    sender.conf.beat_schedule = BEAT_SCHEDULE
    logger.info("✓ Celery Beat schedule configured")
