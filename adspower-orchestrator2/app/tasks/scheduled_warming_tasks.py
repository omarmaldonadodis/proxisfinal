# app/tasks/scheduled_warming_tasks.py - VERSIÓN ACTUALIZADA CON PROXY ROTATION
"""
Tareas Celery programadas (Beat Schedule)
Incluye: warming automático + rotación de proxies + health checks
"""
from celery import Task
from app.database import AsyncSessionLocal
from app.services.scheduler_service import SchedulerService
from loguru import logger
import asyncio

def get_celery_app():
    from app.tasks import celery_app
    return celery_app

celery_app = get_celery_app()

@celery_app.task(name='tasks.execute_scheduled_warmings', bind=True)
def execute_scheduled_warmings_task(self: Task):
    """⏰ Ejecuta warmings programados cada minuto"""
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    async def _execute():
        async with AsyncSessionLocal() as db:
            scheduler_service = SchedulerService(db)
            
            pending = await scheduler_service.get_pending_executions()
            
            if not pending:
                logger.debug("No scheduled warmings to execute")
                return {"executed": 0, "message": "No pending warmings"}
            
            logger.info(f"Found {len(pending)} scheduled warmings to execute")
            
            executed_count = 0
            failed_count = 0
            
            for scheduled_warming in pending:
                try:
                    logger.info(f"Executing scheduled warming {scheduled_warming.id}")
                    
                    result = await scheduler_service.execute_scheduled_warming(
                        scheduled_warming
                    )
                    
                    if result.get("success"):
                        executed_count += 1
                    else:
                        failed_count += 1
                
                except Exception as e:
                    logger.error(f"Error executing scheduled warming {scheduled_warming.id}: {e}")
                    failed_count += 1
            
            return {
                "executed": executed_count,
                "failed": failed_count,
                "total": len(pending)
            }
    
    try:
        return loop.run_until_complete(_execute())
    finally:
        pass


@celery_app.task(name='tasks.cleanup_expired_scheduled_warmings')
def cleanup_expired_scheduled_warmings_task():
    """🧹 Limpia warmings programados expirados"""
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    async def _cleanup():
        from sqlalchemy import select, and_, or_
        from app.models.scheduled_warming import ScheduledWarming
        from datetime import datetime
        
        async with AsyncSessionLocal() as db:
            now = datetime.utcnow()
            
            result = await db.execute(
                select(ScheduledWarming).where(
                    and_(
                        ScheduledWarming.is_active == True,
                        or_(
                            and_(
                                ScheduledWarming.expires_at.isnot(None),
                                ScheduledWarming.expires_at <= now
                            ),
                            and_(
                                ScheduledWarming.max_executions.isnot(None),
                                ScheduledWarming.execution_count >= ScheduledWarming.max_executions
                            )
                        )
                    )
                )
            )
            
            expired = list(result.scalars().all())
            
            if not expired:
                logger.debug("No expired scheduled warmings to clean")
                return {"cleaned": 0}
            
            logger.info(f"Cleaning {len(expired)} expired scheduled warmings")
            
            for scheduled in expired:
                scheduled.is_active = False
            
            await db.commit()
            
            return {"cleaned": len(expired)}
    
    try:
        return loop.run_until_complete(_cleanup())
    finally:
        pass


# ========================================
# ✅ BEAT SCHEDULE COMPLETO
# ========================================

BEAT_SCHEDULE = {
    # ========================================
    # WARMING AUTOMÁTICO
    # ========================================
    'execute-scheduled-warmings': {
        'task': 'tasks.execute_scheduled_warmings',
        'schedule': 60.0,  # Cada 60 segundos
    },
    'cleanup-expired-warmings': {
        'task': 'tasks.cleanup_expired_scheduled_warmings',
        'schedule': 86400.0,  # Cada 24 horas
    },
    
    # ========================================
    # ✅ ROTACIÓN AUTOMÁTICA DE PROXIES (NUEVO)
    # ========================================
    'auto-rotate-proxies': {
        'task': 'tasks.auto_rotate_problematic_proxies',
        'schedule': 1800.0,  # Cada 30 minutos
    },
    
    # ========================================
    # PROXY HEALTH MONITORING
    # ========================================
    'monitor-all-proxies': {
        'task': 'tasks.monitor_all_proxies',
        'schedule': 900.0,  # 15 minutos
    },
    'cleanup-blacklisted-proxies': {
        'task': 'tasks.cleanup_blacklisted_proxies',
        'schedule': 3600.0,  # 1 hora
    },
    'rotate-slow-proxies': {
        'task': 'tasks.rotate_slow_proxies',
        'schedule': 1800.0,  # 30 minutos
    },
    
    # ========================================
    # BACKUPS
    # ========================================
    'backup-database-daily': {
        'task': 'tasks.backup_database',
        'schedule': 86400.0,  # Cada 24 horas
    },
}