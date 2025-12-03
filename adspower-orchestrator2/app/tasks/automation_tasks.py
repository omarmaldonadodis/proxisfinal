# app/tasks/automation_tasks.py
from app.tasks import celery_app
from app.database import AsyncSessionLocal
from app.services.automation_service import AutomationService
from loguru import logger

@celery_app.task(name='tasks.parallel_search', bind=True)
def parallel_search_task(self, profile_ids: list, search_query: str, max_parallel: int):
    """Tarea para búsqueda paralela"""
    import asyncio
    
    async def _parallel_search():
        async with AsyncSessionLocal() as db:
            service = AutomationService(db)
            
            try:
                result = await service.parallel_search(
                    profile_ids=profile_ids,
                    search_query=search_query,
                    max_parallel=max_parallel
                )
                
                logger.info(f"Parallel search completed: {result['successful']}/{result['total']} successful")
                return result
                
            except Exception as e:
                logger.error(f"Parallel search failed: {e}")
                raise
    
    return asyncio.run(_parallel_search())

@celery_app.task(name='tasks.parallel_navigation', bind=True)
def parallel_navigation_task(
    self,
    profile_ids: list,
    urls: list,
    stay_duration_min: int,
    stay_duration_max: int,
    max_parallel: int,
    randomize_order: bool
):
    """Tarea para navegación paralela"""
    import asyncio
    
    async def _parallel_navigation():
        async with AsyncSessionLocal() as db:
            service = AutomationService(db)
            
            try:
                result = await service.parallel_navigation(
                    profile_ids=profile_ids,
                    urls=urls,
                    stay_duration_min=stay_duration_min,
                    stay_duration_max=stay_duration_max,
                    max_parallel=max_parallel,
                    randomize_order=randomize_order
                )
                
                logger.info(f"Parallel navigation completed: {result['successful']}/{result['total']} successful")
                return result
                
            except Exception as e:
                logger.error(f"Parallel navigation failed: {e}")
                raise
    
    return asyncio.run(_parallel_navigation())