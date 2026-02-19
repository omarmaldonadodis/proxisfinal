# app/api/v1/metrics.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.metrics_service import MetricsService

router = APIRouter(prefix="/metrics", tags=["📊 Metrics & Analytics"])


@router.get("/dashboard")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db)
):
    """📊 Estadísticas generales del dashboard"""
    service = MetricsService(db)
    return await service.get_dashboard_stats()


@router.get("/proxies/performance")
async def get_proxy_performance(
    days: int = Query(30, ge=1, le=365, description="Días a analizar"),
    db: AsyncSession = Depends(get_db)
):
    """🚀 Reporte de rendimiento de proxies"""
    service = MetricsService(db)
    return await service.get_proxy_performance_report(days=days)


@router.get("/profiles/timeline")
async def get_creation_timeline(
    days: int = Query(30, ge=1, le=365, description="Días a analizar"),
    db: AsyncSession = Depends(get_db)
):
    """📈 Timeline de creación de profiles"""
    service = MetricsService(db)
    return await service.get_creation_timeline(days=days)


@router.get("/proxies/{proxy_id}/stats")
async def get_proxy_detailed_stats(
    proxy_id: int,
    db: AsyncSession = Depends(get_db)
):
    """📍 Estadísticas detalladas de un proxy específico"""
    from sqlalchemy import select
    from app.models.proxy_health import ProxyUsageStats
    
    result = await db.execute(
        select(ProxyUsageStats).where(ProxyUsageStats.proxy_id == proxy_id)
    )
    stats = result.scalar_one_or_none()
    
    if not stats:
        return {
            "proxy_id": proxy_id,
            "message": "No usage stats available"
        }
    
    return {
        "proxy_id": proxy_id,
        "total_profiles_created": stats.total_profiles_created,
        "avg_latency_ms": stats.avg_latency_ms,
        "success_rate": stats.success_rate,
        "total_rotations": stats.total_rotations,
        "first_used_at": stats.first_used_at,
        "last_used_at": stats.last_used_at
    }