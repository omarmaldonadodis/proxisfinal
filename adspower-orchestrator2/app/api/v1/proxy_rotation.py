# app/api/v1/proxy_rotation.py
"""
API endpoints para rotación inteligente de proxies
"""
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.database import get_db
from app.services.smart_proxy_rotator import SmartProxyRotator
from app.utils.geo_manager import GeoManager

router = APIRouter(prefix="/proxy-rotation", tags=["🔄 Proxy Rotation"])


@router.post("/{proxy_id}/check-and-rotate")
async def check_and_rotate_proxy(
    proxy_id: int,
    test_urls: Optional[List[str]] = Query(None, description="URLs to test functionality"),
    db: AsyncSession = Depends(get_db)
):
    """
    🔍 Verifica proxy y rota si hay problemas
    
    Detecta:
    - Timeouts
    - Carga lenta
    - Bloqueos
    - Detección de bots
    
    Si detecta problemas, rota automáticamente a ubicación alternativa
    """
    
    rotator = SmartProxyRotator(db)
    
    result = await rotator.detect_and_rotate_if_needed(
        proxy_id=proxy_id,
        test_urls=test_urls
    )
    
    return result


@router.post("/scan-all")
async def scan_all_proxies(
    test_urls: Optional[List[str]] = Query(
        None,
        description="URLs to test (default: Google + Ecuabet)"
    ),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db)
):
    """
    🔍 Escanea TODOS los proxies activos y rota los problemáticos
    
    Proceso:
    1. Verifica cada proxy activo
    2. Detecta problemas
    3. Rota automáticamente si es necesario
    4. Actualiza DB + AdsPower
    
    Ejecuta en background (puede tomar varios minutos)
    """
    
    rotator = SmartProxyRotator(db)
    
    if not test_urls:
        test_urls = [
            "https://www.google.com",
            "https://www.ecuabet.com"
        ]
    
    # Ejecutar en background
    async def _scan():
        await rotator.scan_and_rotate_all_proxies(test_urls=test_urls)
    
    background_tasks.add_task(_scan)
    
    return {
        "message": "Proxy scan started in background",
        "test_urls": test_urls
    }


@router.get("/available-locations")
async def get_available_locations(
    country: str = Query("ec", description="Country code")
):
    """
    🗺️ Lista de TODAS las ubicaciones disponibles
    
    Útil para:
    - Ver qué ciudades/regiones están configuradas
    - Planning de distribución geográfica
    """
    
    locations = GeoManager.get_all_locations(country=country)
    
    return {
        "total": len(locations),
        "country": country,
        "locations": [
            {
                "region": loc.region,
                "city": loc.city,
                "soax_string": loc.to_soax_string(),
                "priority": loc.priority
            }
            for loc in locations
        ]
    }


@router.get("/fallback-locations/{proxy_id}")
async def get_fallback_locations(
    proxy_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    🔄 Ubicaciones alternativas para un proxy
    
    Muestra qué ciudades se usarían si el proxy actual falla
    """
    
    from sqlalchemy import select
    from app.models.proxy import Proxy
    
    result = await db.execute(
        select(Proxy).where(Proxy.id == proxy_id)
    )
    proxy = result.scalar_one_or_none()
    
    if not proxy:
        return {"error": "Proxy not found"}
    
    current_location = GeoManager.create_location(
        country=proxy.country,
        region=proxy.region,
        city=proxy.city
    )
    
    fallbacks = GeoManager.get_fallback_locations(current_location)
    
    return {
        "current_location": {
            "city": current_location.city,
            "region": current_location.region,
            "soax_string": current_location.to_soax_string()
        },
        "fallback_count": len(fallbacks),
        "fallbacks": [
            {
                "priority": i + 1,
                "region": loc.region,
                "city": loc.city,
                "soax_string": loc.to_soax_string(),
                "proximity": "same_region" if loc.region == current_location.region else "nearby_region"
            }
            for i, loc in enumerate(fallbacks[:10])  # Top 10
        ]
    }


@router.get("/rotation-stats")
async def get_rotation_stats(
    db: AsyncSession = Depends(get_db)
):
    """
    📊 Estadísticas de rotación
    
    Muestra:
    - Proxies activos por ciudad
    - Proxies fallidos
    - Rotaciones recientes
    """
    
    from sqlalchemy import select, func
    from app.models.proxy import Proxy, ProxyStatus
    
    # Proxies activos por ciudad
    result = await db.execute(
        select(
            Proxy.city,
            Proxy.region,
            func.count(Proxy.id).label('count')
        )
        .where(Proxy.status == ProxyStatus.ACTIVE)
        .group_by(Proxy.city, Proxy.region)
        .order_by(func.count(Proxy.id).desc())
    )
    
    active_by_city = [
        {
            "city": row.city,
            "region": row.region,
            "count": row.count
        }
        for row in result.all()
    ]
    
    # Proxies fallidos
    result = await db.execute(
        select(func.count(Proxy.id))
        .where(Proxy.status == ProxyStatus.FAILED)
    )
    failed_count = result.scalar()
    
    # Total activos
    result = await db.execute(
        select(func.count(Proxy.id))
        .where(Proxy.status == ProxyStatus.ACTIVE)
    )
    active_count = result.scalar()
    
    return {
        "active_proxies": active_count,
        "failed_proxies": failed_count,
        "distribution_by_city": active_by_city,
        "total_cities": len(active_by_city)
    }


@router.post("/{proxy_id}/force-rotate")
async def force_rotate_proxy(
    proxy_id: int,
    target_city: Optional[str] = Query(None, description="Specific city to rotate to"),
    target_region: Optional[str] = Query(None, description="Specific region"),
    db: AsyncSession = Depends(get_db)
):
    """
    🔄 Forzar rotación manual a ubicación específica
    
    Útil para:
    - Testing
    - Redistribución geográfica manual
    - Cambio de estrategia de localización
    """
    
    from sqlalchemy import select
    from app.models.proxy import Proxy
    
    result = await db.execute(
        select(Proxy).where(Proxy.id == proxy_id)
    )
    proxy = result.scalar_one_or_none()
    
    if not proxy:
        return {"error": "Proxy not found"}
    
    rotator = SmartProxyRotator(db)
    
    # Si se especifica ciudad/región, validar
    if target_city or target_region:
        target_location = GeoManager.create_location(
            country=proxy.country,
            region=target_region,
            city=target_city
        )
        
        # Marcar proxy actual como failed para forzar rotación
        proxy.status = "failed"
        await db.commit()
        
        # Rotar (usará target_location como hint)
        new_proxy = await rotator._rotate_to_alternative_location(
            current_proxy=proxy,
            issues=["manual_rotation"]
        )
        
        if not new_proxy:
            return {"error": "Target location not available"}
        
        await rotator._update_profiles_proxy(
            old_proxy_id=proxy.id,
            new_proxy_id=new_proxy.id
        )
        
        return {
            "success": True,
            "old_location": f"{proxy.city}, {proxy.region}",
            "new_location": f"{new_proxy.city}, {new_proxy.region}",
            "new_proxy_id": new_proxy.id
        }
    
    else:
        # Rotación automática (sin target específico)
        result = await rotator.detect_and_rotate_if_needed(
            proxy_id=proxy_id,
            test_urls=["https://www.google.com"]
        )
        
        return result


@router.get("/health-monitor")
async def get_health_monitor_data(
    db: AsyncSession = Depends(get_db)
):
    """
    📊 Datos para dashboard de monitoreo en tiempo real
    
    Retorna:
    - Estado de cada proxy
    - Problemas detectados
    - Rotaciones recientes
    """
    
    from sqlalchemy import select, and_
    from app.models.proxy import Proxy, ProxyStatus
    from app.models.proxy_health import ProxyScore
    from datetime import datetime, timedelta
    
    # Proxies con sus scores
    result = await db.execute(
        select(Proxy, ProxyScore)
        .outerjoin(ProxyScore)
        .where(Proxy.status == ProxyStatus.ACTIVE)
    )
    
    proxies_data = []
    
    for proxy, score in result.all():
        issues = []
        
        if score:
            if score.avg_latency and score.avg_latency > 3000:
                issues.append("slow")
            if score.uptime_percentage < 80:
                issues.append("unstable")
            if score.geo_mismatch_count > 2:
                issues.append("geo_mismatch")
            if score.is_blacklisted:
                issues.append("blacklisted")
        
        proxies_data.append({
            "id": proxy.id,
            "location": f"{proxy.city}, {proxy.region}",
            "status": proxy.status.value,
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