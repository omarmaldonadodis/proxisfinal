# app/tasks/__init__.py
from celery import Celery
from app.config import settings

celery_app = Celery(
    'adspower_orchestrator',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        'app.tasks.health_tasks',
        'app.tasks.backup_tasks',
        'app.tasks.scheduled_warming_tasks'
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
    # ✅ NO IMPORTAR BEAT_SCHEDULE AQUÍ
    # Se configurará directamente en celery beat
)

# ✅ Configurar beat_schedule DESPUÉS de que todos los módulos se carguen
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Configurar tareas periódicas después de inicializar Celery"""
    from app.tasks.scheduled_warming_tasks import BEAT_SCHEDULE
    sender.conf.beat_schedule = BEAT_SCHEDULE