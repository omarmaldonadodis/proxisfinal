# app/api/v1/proxy_rotation.py - INTEGRACIÓN CON NUEVO SISTEMA
"""
API endpoints actualizados para usar SmartProxyRotator BLINDADO
"""
from fastapi import APIRouter, Depends, Query, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.database import get_db
from app.services.smart_proxy_rotator import SmartProxyRotator
from loguru import logger
from datetime import datetime


router = APIRouter(prefix="/proxy-rotation", tags=["🔄 Proxy Rotation"])


@router.post("/{proxy_id}/check-and-rotate")
async def check_and_rotate_proxy(
    proxy_id: int,
    test_urls: Optional[List[str]] = Query(
        None, 
        description="URLs to test (default: Google + Ecuabet)"
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    🎯 Verifica proxy y rota INTELIGENTEMENTE si hay problemas
    
    ✅ NUEVO SISTEMA:
    - Ping real antes de decidir
    - Jerarquía geográfica correcta
    - NO crea duplicados
    - Rollback si falla
    """
    
    if not test_urls:
        test_urls = [
            "https://www.google.com",
            "https://www.ecuabet.com"
        ]
    
    rotator = SmartProxyRotator(db)
    
    try:
        result = await rotator.detect_and_rotate_if_needed(
            proxy_id=proxy_id,
            test_urls=test_urls
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Rotation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-fix-slow-proxies")
async def auto_fix_slow_proxies(
    max_latency_ms: int = Query(2000, description="Max latency threshold"),
    db: AsyncSession = Depends(get_db)
):
    """
    🔧 AUTO-FIX: Rota TODAS las proxies lentas
    
    ✅ Proceso:
    1. Busca proxies con latencia > threshold
    2. Para cada una: ping + rotar si es necesario
    3. Retorna estadísticas
    """
    
    from sqlalchemy import select
    from app.models.proxy import Proxy
    from app.models.proxy_health import ProxyScore
    
    # Obtener proxies lentas
    result = await db.execute(
        select(Proxy, ProxyScore)
        .outerjoin(ProxyScore, Proxy.id == ProxyScore.proxy_id)
        .where(
            (ProxyScore.avg_latency > max_latency_ms) |
            (ProxyScore.avg_latency == None)
        )
    )
    
    candidates = list(result.all())
    
    logger.info(f"🔧 Found {len(candidates)} slow/unscored proxies")
    
    rotator = SmartProxyRotator(db)
    
    stats = {
        "total_checked": len(candidates),
        "rotated": 0,
        "already_optimal": 0,
        "failed": 0,
        "details": []
    }
    
    for proxy, score in candidates:
        try:
            result = await rotator.detect_and_rotate_if_needed(
                proxy_id=proxy.id,
                test_urls=["https://www.google.com"]
            )
            
            if result.get("rotated"):
                stats["rotated"] += 1
            else:
                stats["already_optimal"] += 1
            
            stats["details"].append({
                "proxy_id": proxy.id,
                "location": f"{proxy.city}, {proxy.region}",
                "result": result
            })
        
        except Exception as e:
            logger.error(f"Failed to fix proxy {proxy.id}: {e}")
            stats["failed"] += 1
    
    return stats


@router.post("/recover-blacklisted")
async def recover_blacklisted_proxies(
    db: AsyncSession = Depends(get_db)
):
    """
    🚑 RECOVER: Intenta recuperar proxies blacklisted
    
    ✅ Proceso:
    1. Encuentra proxies blacklisted
    2. Para cada una: rotar a ubicación óptima
    3. Si exitoso, quitar blacklist
    """
    
    from sqlalchemy import select, and_
    from app.models.proxy import Proxy
    from app.models.proxy_health import ProxyScore
    
    result = await db.execute(
        select(Proxy, ProxyScore)
        .join(ProxyScore)
        .where(ProxyScore.is_blacklisted == True)
    )
    
    blacklisted = list(result.all())
    
    if not blacklisted:
        return {
            "message": "No blacklisted proxies found",
            "recovered": 0
        }
    
    logger.info(f"🚑 Attempting to recover {len(blacklisted)} blacklisted proxies")
    
    rotator = SmartProxyRotator(db)
    
    stats = {
        "total": len(blacklisted),
        "recovered": 0,
        "still_failed": 0,
        "details": []
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
            
            stats["details"].append({
                "proxy_id": proxy.id,
                "old_location": f"{proxy.city}, {proxy.region}",
                "result": result
            })
        
        except Exception as e:
            logger.error(f"Recovery failed for proxy {proxy.id}: {e}")
            stats["still_failed"] += 1
    
    await db.commit()
    
    return stats


@router.get("/health-report")
async def get_health_report(
    db: AsyncSession = Depends(get_db)
):
    """
    📊 REPORT: Estado detallado de TODAS las proxies
    
    ✅ Incluye:
    - Ping real de cada proxy
    - Latencia actual
    - Sugerencias de rotación
    """
    
    from sqlalchemy import select
    from app.models.proxy import Proxy
    from app.models.proxy_health import ProxyScore
    
    result = await db.execute(
        select(Proxy, ProxyScore)
        .outerjoin(ProxyScore, Proxy.id == ProxyScore.proxy_id)
    )
    
    proxies_data = list(result.all())
    
    rotator = SmartProxyRotator(db)
    
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "total_proxies": len(proxies_data),
        "optimal": 0,
        "needs_rotation": 0,
        "offline": 0,
        "proxies": []
    }
    
    for proxy, score in proxies_data:
        # Ping real
        ping_result = await rotator._ping_proxy(proxy)
        
        status = "offline"
        recommendation = "rotate"
        
        if ping_result["success"]:
            latency = ping_result["latency_ms"]
            
            if latency < rotator.OPTIMAL_LATENCY_MS:
                status = "optimal"
                recommendation = "keep"
                report["optimal"] += 1
            else:
                status = "slow"
                recommendation = "rotate"
                report["needs_rotation"] += 1
        else:
            report["offline"] += 1
        
        report["proxies"].append({
            "id": proxy.id,
            "location": f"{proxy.city}, {proxy.region}",
            "status": status,
            "current_latency_ms": ping_result.get("latency_ms"),
            "stored_avg_latency_ms": score.avg_latency if score else None,
            "uptime": score.uptime_percentage if score else None,
            "is_blacklisted": score.is_blacklisted if score else False,
            "recommendation": recommendation,
            "error": ping_result.get("error")
        })
    
    return report


@router.post("/batch-optimize")
async def batch_optimize_all_proxies(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    🚀 BATCH OPTIMIZE: Optimiza TODAS las proxies en background
    
    ✅ Proceso:
    1. Ping todas
    2. Rotar las lentas/offline
    3. Se ejecuta en background
    """
    
    async def _optimize():
        from sqlalchemy import select
        from app.models.proxy import Proxy
        
        async with AsyncSessionLocal() as bg_db:
            result = await bg_db.execute(select(Proxy))
            proxies = list(result.scalars().all())
            
            rotator = SmartProxyRotator(bg_db)
            
            logger.info(f"🚀 Starting batch optimization for {len(proxies)} proxies")
            
            stats = {
                "total": len(proxies),
                "rotated": 0,
                "optimal": 0,
                "failed": 0
            }
            
            for proxy in proxies:
                try:
                    result = await rotator.detect_and_rotate_if_needed(
                        proxy_id=proxy.id
                    )
                    
                    if result.get("rotated"):
                        stats["rotated"] += 1
                    else:
                        stats["optimal"] += 1
                
                except Exception as e:
                    logger.error(f"Failed to optimize proxy {proxy.id}: {e}")
                    stats["failed"] += 1
                
                # Rate limiting
                await asyncio.sleep(2)
            
            logger.info(
                f"✅ Batch optimization complete: "
                f"{stats['rotated']} rotated, "
                f"{stats['optimal']} optimal, "
                f"{stats['failed']} failed"
            )
    
    from app.database import AsyncSessionLocal
    import asyncio
    
    background_tasks.add_task(_optimize)
    
    return {
        "message": "Batch optimization started in background",
        "note": "Check logs for progress"
    }


# ========================================
# TASK CELERY ACTUALIZADO
# ========================================

@router.get("/trigger-auto-fix")
async def trigger_auto_fix_task():
    """🔧 Trigger tarea Celery para auto-fix periódico"""
    
    from app.tasks.proxy_rotation_tasks import auto_fix_all_proxies_task
    
    task = auto_fix_all_proxies_task.delay()
    
    return {
        "message": "Auto-fix task triggered",
        "task_id": task.id
    }


# ========================================
# ESTADÍSTICAS (mantener compatibilidad)
# ========================================

@router.get("/rotation-stats")
async def get_rotation_stats(db: AsyncSession = Depends(get_db)):
    """
    📊 Estadísticas de rotación (COMPATIBILIDAD)
    """
    from sqlalchemy import select, func
    from app.models.proxy import Proxy, ProxyStatus
    from app.models.proxy_health import ProxyScore
    
    # Total proxies
    result = await db.execute(select(func.count(Proxy.id)))
    total_proxies = result.scalar()
    
    # Conteo por status
    result = await db.execute(
        select(
            Proxy.status,
            func.count(Proxy.id).label('count')
        )
        .group_by(Proxy.status)
    )
    
    status_distribution = {row.status.value: row.count for row in result.all()}
    
    # Health distribution
    result = await db.execute(
        select(
            Proxy.id,
            Proxy.city,
            Proxy.region,
            Proxy.status,
            Proxy.is_available,
            ProxyScore.overall_score,
            ProxyScore.avg_latency,
            ProxyScore.uptime_percentage,
            ProxyScore.is_blacklisted
        )
        .outerjoin(ProxyScore, Proxy.id == ProxyScore.proxy_id)
    )
    
    proxies_data = result.all()
    
    # Clasificar
    healthy = 0
    degraded = 0
    unhealthy = 0
    no_score = 0
    offline = 0
    
    distribution = []
    
    for row in proxies_data:
        proxy_info = {
            "id": row.id,
            "location": f"{row.city or 'N/A'}, {row.region or 'N/A'}",
            "status": row.status.value,
            "is_available": row.is_available,
            "score": row.overall_score,
            "latency_ms": row.avg_latency,
            "uptime": row.uptime_percentage,
            "is_blacklisted": row.is_blacklisted
        }
        
        # Clasificación
        if row.status == ProxyStatus.FAILED or row.is_blacklisted:
            offline += 1
            proxy_info["health_status"] = "offline"
        elif row.overall_score is None:
            no_score += 1
            proxy_info["health_status"] = "no_score"
        elif row.overall_score >= 80:
            healthy += 1
            proxy_info["health_status"] = "healthy"
        elif row.overall_score >= 60:
            degraded += 1
            proxy_info["health_status"] = "degraded"
        else:
            unhealthy += 1
            proxy_info["health_status"] = "unhealthy"
        
        distribution.append(proxy_info)
    
    # Promedios
    result = await db.execute(
        select(
            func.avg(ProxyScore.overall_score),
            func.avg(ProxyScore.avg_latency),
            func.avg(ProxyScore.uptime_percentage)
        )
    )
    averages = result.one()
    
    return {
        "summary": {
            "total_proxies": total_proxies,
            "by_status": status_distribution,
            "health_distribution": {
                "healthy": healthy,
                "degraded": degraded,
                "unhealthy": unhealthy,
                "no_score": no_score,
                "offline": offline
            }
        },
        "averages": {
            "overall_score": round(averages[0] or 0, 2),
            "avg_latency_ms": round(averages[1] or 0, 2),
            "uptime_percentage": round(averages[2] or 0, 2)
        },
        "proxies_detail": distribution
    }



@router.get("/health-monitor")
async def get_health_monitor_data(
    db: AsyncSession = Depends(get_db)
):
    """
    📊 Datos para dashboard de monitoreo en tiempo real
    
    ✅ MUESTRA TODAS LAS PROXIES (no solo activas)
    
    Retorna:
    - Estado de cada proxy
    - Problemas detectados
    - Rotaciones recientes
    """
    
    from sqlalchemy import select
    from app.models.proxy import Proxy
    from app.models.proxy_health import ProxyScore
    from datetime import datetime
    
    # ✅ SIN FILTRO - Todas las proxies
    result = await db.execute(
        select(Proxy, ProxyScore)
        .outerjoin(ProxyScore, Proxy.id == ProxyScore.proxy_id)
    )
    
    proxies_data = []
    
    for proxy, score in result.all():
        issues = []
        
        # Detectar problemas
        if score:
            if score.avg_latency and score.avg_latency > 3000:
                issues.append("slow")
            if score.uptime_percentage < 80:
                issues.append("unstable")
            if score.geo_mismatch_count > 2:
                issues.append("geo_mismatch")
            if score.is_blacklisted:
                issues.append("blacklisted")
        
        # ✅ Agregar indicador si está FAILED
        if proxy.status.value == "failed":
            issues.append("offline")
        
        proxies_data.append({
            "id": proxy.id,
            "location": f"{proxy.city or 'N/A'}, {proxy.region or 'N/A'}",
            "status": proxy.status.value,
            "is_available": proxy.is_available,
            "score": score.overall_score if score else None,
            "latency": score.avg_latency if score else None,
            "uptime": score.uptime_percentage if score else None,
            "issues": issues,
            "profiles_count": proxy.profiles_count or 0
        })
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "total_proxies": len(proxies_data),
        "proxies": proxies_data
    }


@router.get("/rotation-details/{proxy_id}")
async def get_rotation_details(
    proxy_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    📊 Detalles completos de rotación de un proxy
    
    Muestra:
    - Profiles asignados
    - Ubicación actual
    - Score del proxy
    - Historial de rotaciones
    """
    
    from sqlalchemy import select
    from app.models.proxy import Proxy
    from app.models.proxy_health import ProxyScore
    from app.models.profile import Profile
    
    # Obtener proxy
    result = await db.execute(
        select(Proxy).where(Proxy.id == proxy_id)
    )
    proxy = result.scalar_one_or_none()
    
    if not proxy:
        return {"error": "Proxy not found"}
    
    # Obtener score
    result = await db.execute(
        select(ProxyScore).where(ProxyScore.proxy_id == proxy_id)
    )
    score = result.scalar_one_or_none()
    
    # Obtener profiles asignados
    result = await db.execute(
        select(Profile).where(Profile.proxy_id == proxy_id)
    )
    profiles = list(result.scalars().all())
    
    return {
        "proxy": {
            "id": proxy.id,
            "location": f"{proxy.city or 'N/A'}, {proxy.region or 'N/A'}",
            "status": proxy.status.value,
            "is_available": proxy.is_available,
            "session_id": proxy.session_id
        },
        "score": {
            "overall": score.overall_score if score else None,
            "latency_ms": score.avg_latency if score else None,
            "uptime": score.uptime_percentage if score else None,
            "is_blacklisted": score.is_blacklisted if score else False
        } if score else None,
        "profiles": [
            {
                "id": p.id,
                "name": p.name,
                "adspower_id": p.adspower_id,
                "computer_id": p.computer_id
            }
            for p in profiles
        ],
        "profiles_count": len(profiles)
    }


@router.post("/recover-failed-proxies")
async def recover_failed_proxies(
    max_attempts: int = Query(5, ge=1, le=20, description="Max proxies to attempt recovery"),
    db: AsyncSession = Depends(get_db)
):
    """
    🔄 Intenta recuperar proxies FAILED
    
    Proceso:
    1. Encuentra proxies con status FAILED
    2. Rota sesión (nueva IP)
    3. Re-verifica health
    4. Si exitoso, marca como ACTIVE
    """
    
    from sqlalchemy import select
    from app.models.proxy import Proxy, ProxyStatus
    from app.services.proxy_health_service import ProxyHealthService
    
    # Obtener proxies FAILED
    result = await db.execute(
        select(Proxy)
        .where(Proxy.status == ProxyStatus.FAILED)
        .limit(max_attempts)
    )
    
    failed_proxies = list(result.scalars().all())
    
    if not failed_proxies:
        return {
            "message": "No failed proxies found",
            "recovered": 0,
            "still_failed": 0
        }
    
    health_service = ProxyHealthService(db)
    
    recovered = 0
    still_failed = 0
    
    for proxy in failed_proxies:
        try:
            # Intentar recuperación
            await health_service._attempt_auto_recovery(proxy)
            
            # Re-verificar
            check_result = await health_service.comprehensive_health_check(
                proxy_id=proxy.id,
                test_multiple_sessions=False
            )
            
            if check_result["overall_status"] == "healthy":
                # Marcar como ACTIVE
                proxy.status = ProxyStatus.ACTIVE
                proxy.is_available = True
                recovered += 1
            else:
                still_failed += 1
        
        except Exception as e:
            still_failed += 1
    
    await db.commit()
    
    return {
        "message": f"Recovery attempt completed",
        "total_attempted": len(failed_proxies),
        "recovered": recovered,
        "still_failed": still_failed
    }


@router.post("/check-all-no-score")
async def health_check_no_score_proxies(
    max_concurrent: int = Query(5, ge=1, le=10),
    db: AsyncSession = Depends(get_db)
):
    """
    🏥 Health Check para proxies SIN SCORE
    
    Útil para inicializar scores de proxies nuevos
    """
    
    from sqlalchemy import select
    from app.models.proxy import Proxy
    from app.models.proxy_health import ProxyScore
    
    # Buscar proxies sin score
    result = await db.execute(
        select(Proxy)
        .outerjoin(ProxyScore, Proxy.id == ProxyScore.proxy_id)
        .where(ProxyScore.proxy_id.is_(None))
    )
    
    no_score_proxies = list(result.scalars().all())
    
    if not no_score_proxies:
        return {
            "message": "All proxies have scores",
            "total": 0,
            "results": []
        }
    
    logger.info(f"Found {len(no_score_proxies)} proxies without score")
    
    service = ProxyHealthService(db)
    
    # Ejecutar health checks en paralelo
    import asyncio
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def check_with_semaphore(proxy):
        async with semaphore:
            try:
                result = await service.comprehensive_health_check(
                    proxy_id=proxy.id,
                    test_multiple_sessions=False
                )
                return {
                    "proxy_id": proxy.id,
                    "location": f"{proxy.city}, {proxy.region or proxy.country}",
                    "status": result["overall_status"],
                    "score": result.get("overall_score"),
                    "success": True
                }
            except Exception as e:
                logger.error(f"Health check failed for proxy {proxy.id}: {e}")
                return {
                    "proxy_id": proxy.id,
                    "location": f"{proxy.city}, {proxy.region or proxy.country}",
                    "status": "error",
                    "error": str(e),
                    "success": False
                }
    
    tasks = [check_with_semaphore(proxy) for proxy in no_score_proxies]
    results = await asyncio.gather(*tasks)
    
    # Estadísticas
    successful = sum(1 for r in results if r["success"])
    failed = len(results) - successful
    
    return {
        "message": f"Health check completed for {len(results)} proxies",
        "total": len(results),
        "successful": successful,
        "failed": failed,
        "results": results
    }