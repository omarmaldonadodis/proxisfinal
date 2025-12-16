# app/api/v1/proxy_health.py
"""
API endpoints para health monitoring de proxies
"""
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.database import get_db
from app.services.proxy_health_service import ProxyHealthService

router = APIRouter(prefix="/proxy-health", tags=["🏥 Proxy Health"])


@router.post("/{proxy_id}/check")
async def health_check_proxy(
    proxy_id: int,
    test_sessions: bool = Query(False, description="Test multiple sessions"),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db)
):
    """
    🔍 Verificación completa de un proxy
    
    - Velocidad (latency, download)
    - Disponibilidad
    - Geo-verificación
    - Test con múltiples sesiones (opcional)
    """
    
    service = ProxyHealthService(db)
    
    result = await service.comprehensive_health_check(
        proxy_id=proxy_id,
        test_multiple_sessions=test_sessions
    )
    
    return result


@router.post("/check-all")
async def health_check_all_proxies(
    only_active: bool = Query(True, description="Only check active proxies"),
    max_concurrent: int = Query(10, ge=1, le=50, description="Max concurrent checks"),
    db: AsyncSession = Depends(get_db)
):
    """
    🔍 Verificación de TODOS los proxies
    
    Ejecuta health check en paralelo (max 10 concurrent)
    """
    
    service = ProxyHealthService(db)
    
    results = await service.health_check_all_proxies(
        only_active=only_active,
        max_concurrent=max_concurrent
    )
    
    return results


@router.get("/{proxy_id}/history")
async def get_proxy_health_history(
    proxy_id: int,
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """
    📊 Historial de health checks de un proxy
    """
    
    service = ProxyHealthService(db)
    
    history = await service.get_proxy_health_history(
        proxy_id=proxy_id,
        limit=limit
    )
    
    return {
        "proxy_id": proxy_id,
        "total": len(history),
        "history": history
    }


@router.get("/{proxy_id}/score")
async def get_proxy_score(
    proxy_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    📈 Score y estadísticas de un proxy
    """
    
    from sqlalchemy import select
    from app.models.proxy_health import ProxyScore
    
    result = await db.execute(
        select(ProxyScore).where(ProxyScore.proxy_id == proxy_id)
    )
    score = result.scalar_one_or_none()
    
    if not score:
        return {
            "proxy_id": proxy_id,
            "message": "No score data available yet"
        }
    
    return {
        "proxy_id": proxy_id,
        "overall_score": score.overall_score,
        "speed_score": score.speed_score,
        "availability_score": score.availability_score,
        "geo_accuracy_score": score.geo_accuracy_score,
        "stability_score": score.stability_score,
        "total_checks": score.total_checks,
        "successful_checks": score.successful_checks,
        "failed_checks": score.failed_checks,
        "uptime_percentage": score.uptime_percentage,
        "avg_latency": score.avg_latency,
        "min_latency": score.min_latency,
        "max_latency": score.max_latency,
        "is_blacklisted": score.is_blacklisted,
        "blacklist_reason": score.blacklist_reason,
        "consecutive_failures": score.consecutive_failures,
        "last_check_at": score.last_check_at
    }


@router.get("/top-performers")
async def get_top_performing_proxies(
    limit: int = Query(10, ge=1, le=100),
    min_score: float = Query(80.0, ge=0, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    🏆 Top proxies con mejor rendimiento
    """
    
    service = ProxyHealthService(db)
    
    top_proxies = await service.get_top_performing_proxies(
        limit=limit,
        min_score=min_score
    )
    
    return {
        "count": len(top_proxies),
        "min_score": min_score,
        "proxies": top_proxies
    }


@router.get("/blacklisted")
async def get_blacklisted_proxies(
    db: AsyncSession = Depends(get_db)
):
    """
    🚫 Lista de proxies blacklisted
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
    
    return {
        "count": len(blacklisted),
        "proxies": [
            {
                "proxy_id": proxy.id,
                "proxy_type": proxy.proxy_type,
                "country": proxy.country,
                "blacklist_reason": score.blacklist_reason,
                "blacklisted_at": score.blacklisted_at,
                "consecutive_failures": score.consecutive_failures
            }
            for proxy, score in blacklisted
        ]
    }


@router.post("/{proxy_id}/recover")
async def recover_proxy(
    proxy_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    🔄 Intenta recuperar un proxy manualmente
    
    - Rota sesión
    - Re-verifica salud
    - Quita blacklist si es exitoso
    """
    
    from sqlalchemy import select
    from app.models.proxy import Proxy
    
    result = await db.execute(
        select(Proxy).where(Proxy.id == proxy_id)
    )
    proxy = result.scalar_one_or_none()
    
    if not proxy:
        return {"error": "Proxy not found"}
    
    service = ProxyHealthService(db)
    
    # Intentar recuperación
    await service._attempt_auto_recovery(proxy)
    
    # Re-verificar
    check_result = await service.comprehensive_health_check(
        proxy_id=proxy_id,
        test_multiple_sessions=False
    )
    
    if check_result["overall_status"] == "healthy":
        # Quitar blacklist
        from app.models.proxy_health import ProxyScore
        
        score_result = await db.execute(
            select(ProxyScore).where(ProxyScore.proxy_id == proxy_id)
        )
        score = score_result.scalar_one_or_none()
        
        if score:
            score.is_blacklisted = False
            score.blacklist_reason = None
            score.blacklisted_at = None
            score.consecutive_failures = 0
            await db.commit()
        
        return {
            "success": True,
            "message": "Proxy recovered successfully",
            "health_check": check_result
        }
    
    else:
        return {
            "success": False,
            "message": "Recovery failed",
            "health_check": check_result
        }


@router.get("/stats/summary")
async def get_health_stats_summary(
    db: AsyncSession = Depends(get_db)
):
    """
    📊 Resumen de estadísticas de salud de proxies
    """
    
    from sqlalchemy import select, func, and_
    from app.models.proxy import Proxy
    from app.models.proxy_health import ProxyScore
    
    # Total de proxies
    total_result = await db.execute(select(func.count()).select_from(Proxy))
    total_proxies = total_result.scalar()
    
    # Proxies con score
    scored_result = await db.execute(
        select(func.count()).select_from(ProxyScore)
    )
    scored_proxies = scored_result.scalar()
    
    # Promedios
    avg_result = await db.execute(
        select(
            func.avg(ProxyScore.overall_score),
            func.avg(ProxyScore.avg_latency),
            func.avg(ProxyScore.uptime_percentage)
        )
    )
    averages = avg_result.one()
    
    # Blacklisted
    blacklisted_result = await db.execute(
        select(func.count()).select_from(ProxyScore).where(
            ProxyScore.is_blacklisted == True
        )
    )
    blacklisted_count = blacklisted_result.scalar()
    
    # Por score range
    excellent_result = await db.execute(
        select(func.count()).select_from(ProxyScore).where(
            ProxyScore.overall_score >= 90
        )
    )
    excellent_count = excellent_result.scalar()
    
    good_result = await db.execute(
        select(func.count()).select_from(ProxyScore).where(
            and_(
                ProxyScore.overall_score >= 70,
                ProxyScore.overall_score < 90
            )
        )
    )
    good_count = good_result.scalar()
    
    poor_result = await db.execute(
        select(func.count()).select_from(ProxyScore).where(
            ProxyScore.overall_score < 70
        )
    )
    poor_count = poor_result.scalar()
    
    return {
        "total_proxies": total_proxies,
        "monitored_proxies": scored_proxies,
        "averages": {
            "overall_score": round(averages[0] or 0, 2),
            "avg_latency_ms": round(averages[1] or 0, 2),
            "uptime_percentage": round(averages[2] or 0, 2)
        },
        "distribution": {
            "excellent": excellent_count,  # >= 90
            "good": good_count,  # 70-89
            "poor": poor_count  # < 70
        },
        "blacklisted": blacklisted_count
    }

