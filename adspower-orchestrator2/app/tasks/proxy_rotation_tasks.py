# app/tasks/proxy_rotation_tasks.py - VERSIÓN ULTRA-MEJORADA
"""
Tareas Celery CORREGIDAS:
- Auto-fix cada 15 minutos
- Recuperación de blacklisted
- Detección proactiva de proxies lentas
"""
from celery import Task
from app.database import AsyncSessionLocal
from app.services.smart_proxy_rotator import SmartProxyRotator
from app.services.proxy_health_service import ProxyHealthService
from loguru import logger
import asyncio

def get_celery_app():
    from app.tasks import celery_app
    return celery_app

celery_app = get_celery_app()


@celery_app.task(name='tasks.auto_fix_all_proxies_v2', bind=True)
def auto_fix_all_proxies_task(self: Task):
    """
    ✅ AUTO-FIX MEJORADO (cada 15 min)
    
    1. Health check de TODAS las proxies
    2. Rota automáticamente las que estén:
       - Offline
       - Latencia > 2000ms
       - Failed status
    """
    
    logger.info("🔧 [AUTO-FIX] Starting intelligent proxy optimization")
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    async def _auto_fix():
        from sqlalchemy import select
        from app.models.proxy import Proxy, ProxyStatus
        from app.models.proxy_health import ProxyScore
        
        async with AsyncSessionLocal() as db:
            # ========================================
            # 1. OBTENER TODAS LAS PROXIES
            # ========================================
            result = await db.execute(select(Proxy))
            proxies = list(result.scalars().all())
            
            logger.info(f"🔍 Analyzing {len(proxies)} proxies...")
            
            health_service = ProxyHealthService(db)
            rotator = SmartProxyRotator(db)
            
            stats = {
                "total_checked": len(proxies),
                "healthy": 0,
                "rotated": 0,
                "failed": 0,
                "already_optimal": 0
            }
            
            for proxy in proxies:
                try:
                    # ========================================
                    # 2. HEALTH CHECK
                    # ========================================
                    health = await health_service.comprehensive_health_check(
                        proxy_id=proxy.id,
                        test_multiple_sessions=False
                    )
                    
                    status = health["overall_status"]
                    score = health["overall_score"]
                    
                    # ========================================
                    # 3. DECISIÓN DE ROTACIÓN
                    # ========================================
                    needs_rotation = False
                    reason = ""
                    
                    # A) Offline o unhealthy
                    if status in ["offline", "unhealthy"]:
                        needs_rotation = True
                        reason = f"status={status}"
                    
                    # B) Latencia muy alta
                    elif health["speed_test"].get("latency_ms", 0) > 2000:
                        needs_rotation = True
                        reason = f"high_latency={health['speed_test']['latency_ms']:.0f}ms"
                    
                    # C) Score bajo
                    elif score < 60:
                        needs_rotation = True
                        reason = f"low_score={score}"
                    
                    # D) Failed status
                    elif proxy.status == ProxyStatus.FAILED:
                        needs_rotation = True
                        reason = "failed_status"
                    
                    # ========================================
                    # 4. EJECUTAR ROTACIÓN SI ES NECESARIO
                    # ========================================
                    if needs_rotation:
                        logger.warning(
                            f"🔄 Proxy {proxy.id} needs rotation: {reason}"
                        )
                        
                        rotation_result = await rotator.detect_and_rotate_if_needed(
                            proxy_id=proxy.id,
                            test_urls=["https://httpbin.org/ip"]
                        )
                        
                        if rotation_result.get("rotated"):
                            stats["rotated"] += 1
                            
                            logger.info(
                                f"✅ Rotated: Proxy {proxy.id} "
                                f"({rotation_result['old_location']} → "
                                f"{rotation_result['new_location']})"
                            )
                        else:
                            stats["failed"] += 1
                            logger.error(
                                f"❌ Rotation failed: Proxy {proxy.id}"
                            )
                    else:
                        stats["already_optimal"] += 1
                        stats["healthy"] += 1
                
                except Exception as e:
                    logger.error(f"Error processing proxy {proxy.id}: {e}")
                    stats["failed"] += 1
                
                # Rate limiting
                await asyncio.sleep(2)
            
            # ========================================
            # 5. RESUMEN
            # ========================================
            logger.info(
                f"✅ [AUTO-FIX] Complete: "
                f"{stats['healthy']} healthy, "
                f"{stats['rotated']} rotated, "
                f"{stats['failed']} failed"
            )
            
            return stats
    
    try:
        return loop.run_until_complete(_auto_fix())
    finally:
        pass


@celery_app.task(name='tasks.recover_blacklisted_v2', bind=True)
def recover_blacklisted_task(self: Task):
    """
    ✅ RECUPERA BLACKLISTED (cada hora)
    
    Intenta recuperar proxies blacklisted con:
    - Nueva sesión
    - Re-verificación
    - Reset de contadores si exitoso
    """
    
    logger.info("🚑 [RECOVERY] Starting blacklisted proxy recovery")
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    async def _recover():
        from sqlalchemy import select
        from app.models.proxy import Proxy
        from app.models.proxy_health import ProxyScore
        
        async with AsyncSessionLocal() as db:
            # Obtener blacklisted
            result = await db.execute(
                select(Proxy, ProxyScore)
                .join(ProxyScore)
                .where(ProxyScore.is_blacklisted == True)
            )
            
            blacklisted = list(result.all())
            
            if not blacklisted:
                logger.info("No blacklisted proxies found")
                return {"recovered": 0, "still_failed": 0}
            
            logger.info(f"Found {len(blacklisted)} blacklisted proxies")
            
            health_service = ProxyHealthService(db)
            
            stats = {
                "total": len(blacklisted),
                "recovered": 0,
                "still_failed": 0
            }
            
            for proxy, score in blacklisted:
                try:
                    logger.info(f"Attempting recovery for proxy {proxy.id}")
                    
                    # Intentar auto-recovery
                    await health_service._attempt_auto_recovery_smart(proxy)
                    
                    # Re-verificar
                    health = await health_service.comprehensive_health_check(
                        proxy_id=proxy.id,
                        test_multiple_sessions=False
                    )
                    
                    if health["overall_status"] == "healthy":
                        stats["recovered"] += 1
                        
                        logger.info(
                            f"✅ Recovery successful: Proxy {proxy.id} "
                            f"(score: {health['overall_score']:.1f})"
                        )
                    else:
                        stats["still_failed"] += 1
                
                except Exception as e:
                    logger.error(f"Recovery error for proxy {proxy.id}: {e}")
                    stats["still_failed"] += 1
                
                await asyncio.sleep(3)
            
            logger.info(
                f"✅ [RECOVERY] Complete: "
                f"{stats['recovered']} recovered, "
                f"{stats['still_failed']} still failed"
            )
            
            return stats
    
    try:
        return loop.run_until_complete(_recover())
    finally:
        pass


@celery_app.task(name='tasks.proactive_slow_detection', bind=True)
def proactive_slow_detection_task(self: Task):
    """
    ✅ DETECCIÓN PROACTIVA (cada 10 min)
    
    Detecta y rota proxies lentas ANTES de que fallen
    """
    
    logger.info("🔍 [PROACTIVE] Detecting slow proxies")
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    async def _detect():
        from sqlalchemy import select, and_
        from app.models.proxy import Proxy, ProxyStatus
        from app.models.proxy_health import ProxyScore
        
        async with AsyncSessionLocal() as db:
            # ========================================
            # BUSCAR PROXIES CON LATENCIA > 1500ms
            # ========================================
            result = await db.execute(
                select(Proxy, ProxyScore)
                .join(ProxyScore)
                .where(
                    and_(
                        ProxyScore.avg_latency > 1500,
                        ProxyScore.is_blacklisted == False,
                        Proxy.status == ProxyStatus.ACTIVE
                    )
                )
            )
            
            slow_proxies = list(result.all())
            
            if not slow_proxies:
                logger.info("No slow proxies detected")
                return {"rotated": 0}
            
            logger.warning(
                f"⚠️ Detected {len(slow_proxies)} slow proxies "
                f"(latency > 1500ms)"
            )
            
            rotator = SmartProxyRotator(db)
            
            stats = {"rotated": 0, "failed": 0}
            
            for proxy, score in slow_proxies:
                try:
                    logger.info(
                        f"Rotating slow proxy {proxy.id} "
                        f"(avg: {score.avg_latency:.0f}ms)"
                    )
                    
                    result = await rotator.detect_and_rotate_if_needed(
                        proxy_id=proxy.id
                    )
                    
                    if result.get("rotated"):
                        stats["rotated"] += 1
                    else:
                        stats["failed"] += 1
                
                except Exception as e:
                    logger.error(f"Error rotating proxy {proxy.id}: {e}")
                    stats["failed"] += 1
                
                await asyncio.sleep(2)
            
            logger.info(
                f"✅ [PROACTIVE] Complete: "
                f"{stats['rotated']} rotated"
            )
            
            return stats
    
    try:
        return loop.run_until_complete(_detect())
    finally:
        pass