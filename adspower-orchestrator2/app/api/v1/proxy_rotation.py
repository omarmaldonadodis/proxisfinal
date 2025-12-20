# app/api/v1/proxy_rotation.py - VERSIÓN SIMPLIFICADA
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.proxy_rotation_service import ProxyRotationService

router = APIRouter(prefix="/proxy-rotation", tags=["🔄 Proxy Rotation"])


@router.post("/{proxy_id}/check-and-rotate")
async def check_and_rotate_proxy(
    proxy_id: int,
    db: AsyncSession = Depends(get_db)
):
    """🎯 Verifica y rota proxy si es necesario"""
    
    service = ProxyRotationService(db)
    result = await service.check_and_rotate_proxy(proxy_id)
    
    return result


@router.post("/check-and-rotate-all")
async def check_and_rotate_all(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """🔄 Verifica y rota TODOS los proxies"""
    
    async def _task():
        from app.database import AsyncSessionLocal
        
        async with AsyncSessionLocal() as bg_db:
            service = ProxyRotationService(bg_db)
            stats = await service.check_and_rotate_all_proxies()
            return stats
    
    background_tasks.add_task(_task)
    
    return {"message": "Verificación iniciada en background"}


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """📊 Estadísticas simples"""
    
    from sqlalchemy import select, func
    from app.models.proxy import Proxy, ProxyStatus
    
    result = await db.execute(
        select(
            func.count(Proxy.id).label('total'),
            func.count(Proxy.id).filter(Proxy.status == ProxyStatus.ACTIVE).label('active'),
            func.count(Proxy.id).filter(Proxy.status == ProxyStatus.FAILED).label('failed'),
            func.avg(Proxy.avg_response_time).label('avg_latency')
        )
    )
    row = result.one()
    
    return {
        "total": row.total,
        "active": row.active,
        "failed": row.failed,
        "avg_latency_ms": round(row.avg_latency or 0, 2)
    }