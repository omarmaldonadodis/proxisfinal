# app/tasks/health_tasks.py
from app.tasks import celery_app
from app.database import AsyncSessionLocal
from app.services.computer_service import ComputerService
from app.services.proxy_service import ProxyService
from loguru import logger

@celery_app.task(name='tasks.health_check_all_computers')
def health_check_all_computers_task():
    """Health check de todos los computers"""
    import asyncio
    
    async def _health_check():
        async with AsyncSessionLocal() as db:
            service = ComputerService(db)
            
            # Obtener todos los computers
            computers, _ = await service.list_computers(limit=1000)
            
            results = {
                'total': len(computers),
                'healthy': 0,
                'unhealthy': 0,
                'results': []
            }
            
            for computer in computers:
                try:
                    health = await service.health_check(computer.id)
                    results['results'].append(health)
                    
                    if health['is_healthy']:
                        results['healthy'] += 1
                    else:
                        results['unhealthy'] += 1
                        
                except Exception as e:
                    logger.error(f"Health check failed for computer {computer.id}: {e}")
                    results['unhealthy'] += 1
            
            logger.info(f"Health check completed: {results['healthy']}/{results['total']} healthy")
            return results
    
    return asyncio.run(_health_check())

@celery_app.task(name='tasks.health_check_proxies')
def health_check_proxies_task():
    """Health check de proxies"""
    import asyncio
    
    async def _health_check():
        async with AsyncSessionLocal() as db:
            service = ProxyService(db)
            result = await service.health_check_batch(limit=50)
            
            logger.info(f"Proxy health check: {result['success']}/{result['total']} successful")
            return result
    
    return asyncio.run(_health_check())