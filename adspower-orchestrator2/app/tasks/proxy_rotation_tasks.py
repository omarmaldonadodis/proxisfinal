# app/tasks/proxy_rotation_tasks.py - NUEVA TAREA CELERY
"""
Tareas Celery para rotación automática de proxies
Se ejecuta cada 30 minutos para detectar y rotar IPs problemáticas
"""
from celery import Task
from app.database import AsyncSessionLocal
from app.services.smart_proxy_rotator import SmartProxyRotator
from loguru import logger
import asyncio

def get_celery_app():
    from app.tasks import celery_app
    return celery_app

celery_app = get_celery_app()


@celery_app.task(name='tasks.auto_rotate_problematic_proxies', bind=True)
def auto_rotate_problematic_proxies_task(self: Task):
    """
    🔄 Rotación automática de proxies problemáticos
    
    Detecta:
    - IPs lentas (latencia > 5s)
    - IPs bloqueadas (timeouts, 403)
    - Funcionalidades no disponibles
    
    Se ejecuta cada 30 minutos
    """
    
    logger.info("🔄 Starting automatic proxy rotation task")
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    async def _rotate():
        async with AsyncSessionLocal() as db:
            rotator = SmartProxyRotator(db)
            
            # URLs de test (ajusta según necesidad)
            test_urls = [
                "https://www.google.com",
                "https://www.ecuabet.com"  # ✅ Tu caso de uso
            ]
            
            # Escanear y rotar
            results = await rotator.scan_and_rotate_all_proxies(
                test_urls=test_urls
            )
            
            logger.info(
                f"✓ Auto-rotation completed: "
                f"{results['rotated']} rotated, "
                f"{results['healthy']} healthy, "
                f"{results['errors']} errors"
            )
            
            # ✅ Enviar alerta si muchos proxies fallaron
            failure_rate = (results['rotated'] / results['total_scanned'] * 100) if results['total_scanned'] > 0 else 0
            
            if failure_rate > 20:
                logger.warning(
                    f"⚠️  HIGH PROXY FAILURE RATE: {failure_rate:.1f}% rotated"
                )
                # Aquí podrías enviar notificación por email/slack/discord
            
            return results
    
    try:
        return loop.run_until_complete(_rotate())
    finally:
        pass


@celery_app.task(name='tasks.scan_specific_proxy', bind=True)
def scan_specific_proxy_task(self: Task, proxy_id: int):
    """
    🔍 Escanea un proxy específico y rota si es necesario
    
    Útil para llamar manualmente desde API
    """
    
    logger.info(f"🔍 Scanning proxy {proxy_id}")
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    async def _scan():
        async with AsyncSessionLocal() as db:
            rotator = SmartProxyRotator(db)
            
            result = await rotator.detect_and_rotate_if_needed(
                proxy_id=proxy_id,
                test_urls=["https://www.google.com", "https://www.ecuabet.com"]
            )
            
            logger.info(f"Scan result for proxy {proxy_id}: {result}")
            
            return result
    
    try:
        return loop.run_until_complete(_scan())
    finally:
        pass


