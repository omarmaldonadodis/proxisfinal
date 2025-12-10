# adspower-orchestrator2/app/tasks/scheduled_warming_tasks.py
"""
Tareas Celery para ejecutar warmings programados automáticamente
"""
from celery import Task
from app.tasks import celery_app
from app.database import AsyncSessionLocal
from app.services.scheduler_service import SchedulerService
from loguru import logger
import asyncio


@celery_app.task(name='tasks.execute_scheduled_warmings', bind=True)
def execute_scheduled_warmings_task(self: Task):
    """
    ⏰ Tarea que se ejecuta cada minuto para verificar warmings programados
    
    Esta tarea:
    1. Busca warmings cuya next_execution_at <= now
    2. Los ejecuta
    3. Calcula próxima ejecución (si es recurrente)
    4. Actualiza estado
    """
    
    async def _execute():
        async with AsyncSessionLocal() as db:
            scheduler_service = SchedulerService(db)
            
            # Obtener warmings pendientes
            pending = await scheduler_service.get_pending_executions()
            
            if not pending:
                logger.debug("No scheduled warmings to execute")
                return {
                    "executed": 0,
                    "message": "No pending warmings"
                }
            
            logger.info(f"Found {len(pending)} scheduled warmings to execute")
            
            executed_count = 0
            failed_count = 0
            
            for scheduled_warming in pending:
                try:
                    logger.info(f"Executing scheduled warming {scheduled_warming.id}")
                    
                    # Ejecutar warming
                    result = await scheduler_service.execute_scheduled_warming(
                        scheduled_warming
                    )
                    
                    if result.get("success"):
                        executed_count += 1
                        logger.info(
                            f"✓ Scheduled warming {scheduled_warming.id} executed. "
                            f"Next execution: {scheduled_warming.next_execution_at}"
                        )
                    else:
                        failed_count += 1
                        logger.error(
                            f"✗ Scheduled warming {scheduled_warming.id} failed: "
                            f"{result.get('error')}"
                        )
                
                except Exception as e:
                    logger.error(f"Error executing scheduled warming {scheduled_warming.id}: {e}")
                    failed_count += 1
            
            return {
                "executed": executed_count,
                "failed": failed_count,
                "total": len(pending)
            }
    
    return asyncio.run(_execute())


@celery_app.task(name='app.tasks.cleanup_expired_scheduled_warmings')
def cleanup_expired_scheduled_warmings_task():
    """
    🧹 Limpia warmings programados expirados
    
    Se ejecuta diariamente para desactivar:
    - Warmings cuyo expires_at ha pasado
    - Warmings que alcanzaron max_executions
    """
    
    async def _cleanup():
        from sqlalchemy import select, and_, or_
        from app.models.scheduled_warming import ScheduledWarming
        from datetime import datetime
        
        async with AsyncSessionLocal() as db:
            now = datetime.utcnow()
            
            # Buscar warmings a desactivar
            result = await db.execute(
                select(ScheduledWarming).where(
                    and_(
                        ScheduledWarming.is_active == True,
                        or_(
                            # Expiró por fecha
                            and_(
                                ScheduledWarming.expires_at.isnot(None),
                                ScheduledWarming.expires_at <= now
                            ),
                            # Alcanzó máximo de ejecuciones
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
                logger.info(f"Deactivated expired warming {scheduled.id}")
            
            await db.commit()
            
            return {"cleaned": len(expired)}
    
    return asyncio.run(_cleanup())

# ✅ SOLO EL SCHEDULE AQUÍ, SIN IMPORTAR celery_app
BEAT_SCHEDULE = {
    'execute-scheduled-warmings': {
        'task': 'app.tasks.scheduled_warming_tasks.execute_scheduled_warmings_task',
        'schedule': 60.0,
    },
    'cleanup-expired-warmings': {
        'task': 'app.tasks.scheduled_warming_tasks.cleanup_expired_scheduled_warmings_task',
        'schedule': 86400.0,
    },
}


