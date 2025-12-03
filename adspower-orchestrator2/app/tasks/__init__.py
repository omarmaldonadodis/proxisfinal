# app/tasks/__init__.py
from celery import Celery
from app.config import settings

celery_app = Celery(
    'adspower_orchestrator',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        'app.tasks.profile_tasks',
        'app.tasks.automation_tasks',
        'app.tasks.health_tasks',
        'app.tasks.backup_tasks'
    ]
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3000,  # 50 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)