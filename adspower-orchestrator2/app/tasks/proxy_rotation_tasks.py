# app/tasks/proxy_rotation_tasks.py - SIMPLIFICADO
from app.tasks import celery_app
from app.database import AsyncSessionLocal
from app.services.proxy_rotation_service import ProxyRotationService
from loguru import logger
import asyncio


@celery_app.task(name='tasks.auto_rotate_slow_proxies')
def auto_rotate_slow_proxies_task():
    """⏰ Se ejecuta cada 15 minutos"""
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    async def _rotate():
        async with AsyncSessionLocal() as db:
            service = ProxyRotationService(db)
            stats = await service.check_and_rotate_all_proxies()
            
            logger.info(
                f"✅ Auto-rotación completa: "
                f"{stats['rotated']} rotados, "
                f"{stats['optimal']} óptimos"
            )
            
            return stats
    
    return loop.run_until_complete(_rotate())