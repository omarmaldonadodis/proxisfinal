# app/api/v1/proxy_rotation.py - ✅ VERSIÓN CORREGIDA SIN BACKGROUNDTASKS

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.proxy_rotation_service import ProxyRotationService
from loguru import logger
from sqlalchemy import select
import asyncio


router = APIRouter(prefix="/proxy-rotation", tags=["Proxy Rotation"])


@router.post("/{proxy_id}/check-and-rotate")
async def check_and_rotate_proxy(
    proxy_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Verifica y rota proxy si es necesario
    """
    
    try:
        service = ProxyRotationService(db)
        result = await service.check_and_rotate_proxy(proxy_id)
        
        if result.get("error"):
            logger.error(f"Error rotando proxy {proxy_id}: {result['error']}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": result["error"],
                    "proxy_id": proxy_id,
                    "old_latency_ms": result.get("old_latency_ms")
                }
            )
        
        return result
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Unexpected error checking proxy {proxy_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error inesperado: {str(e)}"
        )


@router.post("/check-and-rotate-all")
async def check_and_rotate_all():
    """
    🔄 Verifica y rota TODOS los proxies
    
    """
    
    # ✅ Crear tarea en background usando asyncio
    asyncio.create_task(_background_check_all())
    
    return {
        "message": "Verificación iniciada en background",
        "status": "processing"
    }


async def _background_check_all():
    """
    ✅ Tarea en background que se ejecuta con su propia sesión de DB
    """
    from app.database import AsyncSessionLocal
    
    try:
        async with AsyncSessionLocal() as db:
            service = ProxyRotationService(db)
            stats = await service.check_and_rotate_all_proxies()
            
            logger.info(
                f"✅ Rotación completa: "
                f"{stats['rotated']} rotados, "
                f"{stats['recovered']} recuperados, "
                f"{stats['optimal']} óptimos, "
                f"{stats['failed']} fallidos"
            )
            
            return stats
    
    except Exception as e:
        logger.error(f"Error en tarea de rotación: {e}")
        raise


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """📊 Estadísticas simples"""
    
    from sqlalchemy import select, func
    from app.models.proxy import Proxy, ProxyStatus
    
    try:
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
    
    except Exception as e:
        logger.error(f"Error obteniendo stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-all")
async def sync_all_to_adspower():
    """
    🔄 FORZAR sincronización de TODOS los proxies a AdsPower, sirve para pasar de la BD al adspower 
    
    """
    
    # ✅ Crear tarea en background
    asyncio.create_task(_background_sync_all())
    
    return {
        "message": "Sincronización iniciada en background",
        "status": "processing"
    }


async def _background_sync_all():
    """
    ✅ Sincroniza todos los proxies con AdsPower en background
    """
    from app.database import AsyncSessionLocal
    from app.models.proxy import Proxy, ProxyStatus
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Proxy).where(Proxy.status == ProxyStatus.ACTIVE)
        )
        proxies = list(result.scalars().all())
        
        logger.info(f"🔄 Sincronizando {len(proxies)} proxies a AdsPower...")
        
        service = ProxyRotationService(db)
        
        synced = 0
        failed = 0
        
        for proxy in proxies:
            try:
                success = await service._update_adspower_profiles_centralized(proxy)
                
                if success:
                    synced += 1
                    logger.info(f"✅ Proxy {proxy.id} sincronizado")
                else:
                    failed += 1
                    logger.error(f"❌ Proxy {proxy.id} falló")
            
            except Exception as e:
                logger.error(f"❌ Error sincronizando proxy {proxy.id}: {e}")
                failed += 1
            
            await asyncio.sleep(1)
        
        logger.info(
            f"✅ Sincronización completa: {synced} OK, {failed} fallidos"
        )
        
        return {"synced": synced, "failed": failed}