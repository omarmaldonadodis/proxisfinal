# app/tasks/proxy_rotation_tasks.py - TAREA ACTUALIZADA
"""
Tarea Celery que usa el NUEVO sistema de rotación blindado
Se ejecuta cada 15 minutos para mantener proxies óptimas
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


@celery_app.task(name='tasks.auto_fix_all_proxies', bind=True)
def auto_fix_all_proxies_task(self: Task):
    """
    🔧 AUTO-FIX INTELIGENTE de TODAS las proxies
    
    ✅ NUEVO SISTEMA:
    - Ping real antes de decidir
    - Rota solo si latencia > 1000ms o offline
    - NO crea duplicados
    - Rollback si falla
    
    Se ejecuta cada 15 minutos
    """
    
    logger.info("🔧 Starting intelligent auto-fix for all proxies")
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    async def _auto_fix():
        from sqlalchemy import select
        from app.models.proxy import Proxy
        
        async with AsyncSessionLocal() as db:
            # Obtener TODAS las proxies
            result = await db.execute(select(Proxy))
            proxies = list(result.scalars().all())
            
            logger.info(f"🔍 Checking {len(proxies)} proxies...")
            
            rotator = SmartProxyRotator(db)
            
            stats = {
                "total_checked": len(proxies),
                "rotated": 0,
                "already_optimal": 0,
                "failed": 0,
                "details": []
            }
            
            for proxy in proxies:
                try:
                    # ========================================
                    # 1. PING PROXY
                    # ========================================
                    ping_result = await rotator._ping_proxy(proxy)
                    
                    # Si es óptima, skip
                    if (ping_result["success"] and 
                        ping_result["latency_ms"] < rotator.OPTIMAL_LATENCY_MS):
                        
                        logger.debug(
                            f"✅ Proxy {proxy.id} optimal "
                            f"({ping_result['latency_ms']}ms)"
                        )
                        stats["already_optimal"] += 1
                        continue
                    
                    # ========================================
                    # 2. NECESITA ROTACIÓN
                    # ========================================
                    logger.info(
                        f"🔄 Proxy {proxy.id} needs rotation: "
                        f"latency={ping_result.get('latency_ms', 'N/A')}ms, "
                        f"success={ping_result['success']}"
                    )
                    
                    result = await rotator.detect_and_rotate_if_needed(
                        proxy_id=proxy.id,
                        test_urls=["https://www.google.com"]
                    )
                    
                    if result.get("rotated"):
                        stats["rotated"] += 1
                        
                        logger.info(
                            f"✅ Rotated proxy {proxy.id}: "
                            f"{result['old_location']} → {result['new_location']} "
                            f"({result['old_latency_ms']}ms → {result['new_latency_ms']}ms)"
                        )
                        
                        stats["details"].append({
                            "proxy_id": proxy.id,
                            "action": "rotated",
                            "old_location": result["old_location"],
                            "new_location": result["new_location"],
                            "improvement_ms": (
                                result.get("old_latency_ms", 0) - 
                                result.get("new_latency_ms", 0)
                            )
                        })
                    else:
                        logger.warning(
                            f"⚠️ Proxy {proxy.id} rotation failed: "
                            f"{result.get('error', result.get('message'))}"
                        )
                        stats["failed"] += 1
                
                except Exception as e:
                    logger.error(f"Error processing proxy {proxy.id}: {e}")
                    stats["failed"] += 1
                
                # Rate limiting para no saturar
                await asyncio.sleep(1)
            
            # ========================================
            # RESUMEN FINAL
            # ========================================
            logger.info(
                f"✅ Auto-fix complete: "
                f"{stats['rotated']} rotated, "
                f"{stats['already_optimal']} optimal, "
                f"{stats['failed']} failed"
            )
            
            return stats
    
    try:
        return loop.run_until_complete(_auto_fix())
    finally:
        pass


@celery_app.task(name='tasks.fix_blacklisted_proxies', bind=True)
def fix_blacklisted_proxies_task(self: Task):
    """
    🚑 Recupera proxies blacklisted
    Se ejecuta cada hora
    """
    
    logger.info("🚑 Attempting to recover blacklisted proxies")
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    async def _fix_blacklisted():
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
            
            rotator = SmartProxyRotator(db)
            
            stats = {
                "total": len(blacklisted),
                "recovered": 0,
                "still_failed": 0
            }
            
            for proxy, score in blacklisted:
                try:
                    # Intentar rotación
                    result = await rotator.detect_and_rotate_if_needed(
                        proxy_id=proxy.id
                    )
                    
                    if result.get("rotated") and result.get("new_latency_ms"):
                        # Exitoso - quitar blacklist
                        score.is_blacklisted = False
                        score.blacklist_reason = None
                        score.blacklisted_at = None
                        score.consecutive_failures = 0
                        
                        stats["recovered"] += 1
                        
                        logger.info(
                            f"✅ Recovered proxy {proxy.id}: "
                            f"{result['new_location']} ({result['new_latency_ms']}ms)"
                        )
                    else:
                        stats["still_failed"] += 1
                
                except Exception as e:
                    logger.error(f"Recovery failed for proxy {proxy.id}: {e}")
                    stats["still_failed"] += 1
                
                await asyncio.sleep(2)
            
            await db.commit()
            
            logger.info(
                f"Recovery complete: {stats['recovered']} recovered, "
                f"{stats['still_failed']} still failed"
            )
            
            return stats
    
    try:
        return loop.run_until_complete(_fix_blacklisted())
    finally:
        pass