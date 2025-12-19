# app/tasks/proxy_health_tasks.py
"""
Tareas Celery para monitoreo automático de proxies
Se ejecutan en background sin intervención manual
"""
from celery import Task
from app.database import AsyncSessionLocal
from app.services.proxy_health_service import ProxyHealthService
from loguru import logger
import asyncio

def get_celery_app():
    from app.tasks import celery_app
    return celery_app

celery_app = get_celery_app()


@celery_app.task(name='tasks.monitor_all_proxies', bind=True)
def monitor_all_proxies_task(self: Task):
    """
    ⏰ Monitoreo completo de todos los proxies
    Se ejecuta cada 15 minutos
    """
    
    logger.info("Starting automated proxy health monitoring")
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    async def _monitor():
        async with AsyncSessionLocal() as db:
            service = ProxyHealthService(db)
            
            # Ejecutar health check en todos los proxies activos
            results = await service.health_check_all_proxies(
                only_active=True,
                max_concurrent=10  # 10 proxies en paralelo
            )
            
            logger.info(
                f"✓ Proxy monitoring completed: "
                f"{results['healthy']} healthy, "
                f"{results['degraded']} degraded, "
                f"{results['unhealthy']} unhealthy, "
                f"{results['offline']} offline"
            )
            
            # Alertas si hay muchos proxies caídos
            offline_percentage = (results['offline'] / results['total'] * 100) if results['total'] > 0 else 0
            
            if offline_percentage > 20:
                logger.warning(
                    f"⚠️  HIGH PROXY FAILURE RATE: {offline_percentage:.1f}% offline"
                )
                
                # Aquí podrías enviar alerta por email/slack/discord
                # await send_alert(f"High proxy failure rate: {offline_percentage:.1f}%")
            
            return results
    
    try:
        return loop.run_until_complete(_monitor())
    finally:
        pass


@celery_app.task(name='tasks.deep_proxy_check', bind=True)
def deep_proxy_check_task(self: Task, proxy_id: int):
    """
    🔍 Verificación profunda de un proxy específico
    Incluye test con múltiples sesiones
    """
    
    logger.info(f"Starting deep check for proxy {proxy_id}")
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    async def _deep_check():
        async with AsyncSessionLocal() as db:
            service = ProxyHealthService(db)
            
            result = await service.comprehensive_health_check(
                proxy_id=proxy_id,
                test_multiple_sessions=True  # ✅ Test con 3 sesiones
            )
            
            logger.info(
                f"Deep check completed for proxy {proxy_id}: "
                f"Status={result['overall_status']}, Score={result['overall_score']}"
            )
            
            return result
    
    try:
        return loop.run_until_complete(_deep_check())
    finally:
        pass


@celery_app.task(name='tasks.cleanup_blacklisted_proxies', bind=True)
def cleanup_blacklisted_proxies_task(self: Task):
    """
    🧹 Limpieza de proxies blacklisted
    - Intenta recuperarlos automáticamente
    - Marca como inactivos si fallan múltiples veces
    """
    
    logger.info("Starting blacklisted proxies cleanup")
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    async def _cleanup():
        from sqlalchemy import select, and_
        from app.models.proxy import Proxy
        from app.models.proxy_health import ProxyScore
        from datetime import datetime, timedelta
        
        async with AsyncSessionLocal() as db:
            # Obtener proxies blacklisted hace más de 1 hora
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            
            result = await db.execute(
                select(Proxy, ProxyScore)
                .join(ProxyScore)
                .where(
                    and_(
                        ProxyScore.is_blacklisted == True,
                        ProxyScore.blacklisted_at < one_hour_ago,
                        Proxy.is_available == True
                    )
                )
            )
            
            blacklisted = list(result.all())
            
            if not blacklisted:
                logger.info("No blacklisted proxies to recover")
                return {"recovered": 0, "failed": 0}
            
            logger.info(f"Found {len(blacklisted)} blacklisted proxies to recover")
            
            service = ProxyHealthService(db)
            
            recovered = 0
            failed = 0
            
            for proxy, score in blacklisted:
                try:
                    logger.info(f"Attempting recovery for proxy {proxy.id}")
                    
                    # Intentar recuperación
                    await service._attempt_auto_recovery(proxy)
                    
                    # Re-verificar
                    result = await service.comprehensive_health_check(
                        proxy.id,
                        test_multiple_sessions=False
                    )
                    
                    if result["overall_status"] == "healthy":
                        # Quitar blacklist
                        score.is_blacklisted = False
                        score.blacklist_reason = None
                        score.blacklisted_at = None
                        score.consecutive_failures = 0
                        
                        recovered += 1
                        logger.info(f"✓ Proxy {proxy.id} recovered")
                    
                    else:
                        failed += 1
                        
                        # Si falló muchas veces, marcar como inactivo
                        if score.consecutive_failures >= 10:
                            proxy.is_available = False
                            logger.warning(f"Proxy {proxy.id} marked as unavailable")
                
                except Exception as e:
                    logger.error(f"Recovery failed for proxy {proxy.id}: {e}")
                    failed += 1
            
            await db.commit()
            
            logger.info(f"Cleanup completed: {recovered} recovered, {failed} failed")
            
            return {"recovered": recovered, "failed": failed}
    
    try:
        return loop.run_until_complete(_cleanup())
    finally:
        pass


@celery_app.task(name='tasks.rotate_slow_proxies', bind=True)
def rotate_slow_proxies_task(self: Task):
    """
    🔄 Rotación automática de proxies lentos
    Si un proxy tiene latencia alta consistentemente, rota su sesión
    """
    
    logger.info("Starting slow proxies rotation")
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    async def _rotate():
        from sqlalchemy import select, and_
        from app.models.proxy import Proxy
        from app.models.proxy_health import ProxyScore
        
        async with AsyncSessionLocal() as db:
            # Obtener proxies con latencia alta
            result = await db.execute(
                select(Proxy, ProxyScore)
                .join(ProxyScore)
                .where(
                    and_(
                        ProxyScore.avg_latency > 2000,  # > 2 segundos
                        ProxyScore.is_blacklisted == False,
                        Proxy.is_available == True
                    )
                )
            )
            
            slow_proxies = list(result.all())
            
            if not slow_proxies:
                logger.info("No slow proxies found")
                return {"rotated": 0}
            
            logger.info(f"Found {len(slow_proxies)} slow proxies")
            
            service = ProxyHealthService(db)
            rotated = 0
            
            for proxy, score in slow_proxies:
                try:
                    logger.info(
                        f"Rotating proxy {proxy.id} "
                        f"(avg latency: {score.avg_latency:.0f}ms)"
                    )
                    
                    # Rotar sesión
                    await service._attempt_auto_recovery(proxy)
                    
                    rotated += 1
                
                except Exception as e:
                    logger.error(f"Rotation failed for proxy {proxy.id}: {e}")
            
            logger.info(f"Rotation completed: {rotated} proxies rotated")
            
            return {"rotated": rotated}
    
    try:
        return loop.run_until_complete(_rotate())
    finally:
        pass

# adspower-orchestrator2/app/tasks/proxy_health_tasks.py

@celery_app.task(name='tasks.auto_recover_and_verify')
def auto_recover_and_verify_task():
    """
    🔄 Tarea automática que:
    1. Verifica salud de todos los proxies
    2. Recupera los que fallan
    3. Actualiza AdsPower
    
    Se ejecuta cada 15 minutos
    """
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    async def _recover():
        from sqlalchemy import select
        from app.models.proxy import Proxy, ProxyStatus
        from app.services.proxy_health_service import ProxyHealthService
        from app.services.smart_proxy_rotator import SmartProxyRotator
        
        async with AsyncSessionLocal() as db:
            # ========================================
            # 1. HEALTH CHECK TODOS LOS PROXIES
            # ========================================
            health_service = ProxyHealthService(db)
            
            results = await health_service.health_check_all_proxies(
                only_active=False,  # ✅ Verificar TODOS
                max_concurrent=5
            )
            
            logger.info(
                f"Health check: {results['healthy']} healthy, "
                f"{results['offline']} offline"
            )
            
            # ========================================
            # 2. RECUPERAR PROXIES FAILED
            # ========================================
            result = await db.execute(
                select(Proxy).where(Proxy.status == ProxyStatus.FAILED)
            )
            failed_proxies = list(result.scalars().all())
            
            if not failed_proxies:
                logger.info("No failed proxies to recover")
                return {"recovered": 0, "failed": 0}
            
            logger.info(f"Found {len(failed_proxies)} failed proxies")
            
            rotator = SmartProxyRotator(db)
            recovered = 0
            still_failed = 0
            
            for proxy in failed_proxies:
                try:
                    # Intentar recuperar (reutilizando proxies existentes)
                    result = await rotator.detect_and_rotate_if_needed(
                        proxy_id=proxy.id,
                        test_urls=["https://www.google.com"]
                    )
                    
                    if result.get("rotated"):
                        # ✅ Actualizar profiles en AdsPower
                        if result.get("new_proxy_id"):
                            await rotator._update_profiles_proxy(
                                old_proxy_id=proxy.id,
                                new_proxy_id=result["new_proxy_id"]
                            )
                        
                        recovered += 1
                        logger.info(f"✓ Recovered proxy {proxy.id}")
                    else:
                        still_failed += 1
                
                except Exception as e:
                    logger.error(f"Error recovering proxy {proxy.id}: {e}")
                    still_failed += 1
            
            return {
                "total_checked": results['total'],
                "healthy": results['healthy'],
                "recovered": recovered,
                "still_failed": still_failed
            }
    
    try:
        return loop.run_until_complete(_recover())
    finally:
        pass


# NOTA: Agregar PROXY_HEALTH_SCHEDULE al BEAT_SCHEDULE existente