# app/api/v1/proxy_rotation.py - VERSIÓN CORREGIDA COMPLETA
"""
API endpoints para rotación inteligente de proxies
✅ FIXES:
- Muestra TODAS las proxies (ACTIVE, FAILED, INACTIVE)
- Conteos correctos con manejo de NULL scores
- Busca alternativas eficientes sin importar status actual
- Recuperación automática de proxies FAILED
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
    📊 Estadísticas de rotación CORREGIDAS
    
    ✅ FIXES:
    - Muestra TODAS las proxies (no solo ACTIVE)
    - Maneja correctamente proxies sin ProxyScore
    - Conteos precisos por estado
    """
    
    from sqlalchemy import select, func, case
    from app.models.proxy import Proxy, ProxyStatus
    from app.models.proxy_health import ProxyScore
    
    # ========================================
    # 1. TODAS LAS PROXIES (sin filtro de status)
    # ========================================
    result = await db.execute(
        select(func.count(Proxy.id))
    )
    total_proxies = result.scalar()
    
    # ========================================
    # 2. CONTEO POR STATUS
    # ========================================
    result = await db.execute(
        select(
            Proxy.status,
            func.count(Proxy.id).label('count')
        )
        .group_by(Proxy.status)
    )
    
    status_distribution = {row.status.value: row.count for row in result.all()}
    
    # ========================================
    # 3. PROXIES CON SCORE (LEFT JOIN CORRECTO)
    # ========================================
    result = await db.execute(
        select(
            Proxy.id,
            Proxy.city,
            Proxy.region,
            Proxy.status,
            Proxy.is_available,
            ProxyScore.overall_score,
            ProxyScore.avg_latency,
            ProxyScore.uptime_percentage
        )
        .outerjoin(ProxyScore, Proxy.id == ProxyScore.proxy_id)
    )
    
    proxies_data = result.all()
    
    # Clasificar por health status
    healthy = 0
    degraded = 0
    unhealthy = 0
    no_score = 0
    offline = 0
    
    distribution = []
    
    for proxy_id, city, region, status, is_available, score, latency, uptime in proxies_data:
        proxy_info = {
            "id": proxy_id,
            "location": f"{city or 'N/A'}, {region or 'N/A'}",
            "status": status.value,
            "is_available": is_available,
            "score": score,
            "latency_ms": latency,
            "uptime": uptime
        }
        
        # ✅ Clasificación correcta
        if status == ProxyStatus.FAILED:
            offline += 1
            proxy_info["health_status"] = "offline"
        elif score is None:
            no_score += 1
            proxy_info["health_status"] = "no_score"
        elif score >= 80:
            healthy += 1
            proxy_info["health_status"] = "healthy"
        elif score >= 60:
            degraded += 1
            proxy_info["health_status"] = "degraded"
        else:
            unhealthy += 1
            proxy_info["health_status"] = "unhealthy"
        
        distribution.append(proxy_info)
    
    # ========================================
    # 4. PROMEDIOS (solo proxies con score válido)
    # ========================================
    result = await db.execute(
        select(
            func.avg(ProxyScore.overall_score),
            func.avg(ProxyScore.avg_latency),
            func.avg(ProxyScore.uptime_percentage)
        )
    )
    averages = result.one()
    
    # ========================================
    # 5. DISTRIBUCIÓN POR CIUDAD (TODAS las proxies)
    # ========================================
    result = await db.execute(
        select(
            Proxy.city,
            Proxy.region,
            Proxy.status,
            func.count(Proxy.id).label('count')
        )
        .group_by(Proxy.city, Proxy.region, Proxy.status)
        .order_by(func.count(Proxy.id).desc())
    )
    
    city_distribution = {}
    for row in result.all():
        key = f"{row.city}, {row.region}"
        if key not in city_distribution:
            city_distribution[key] = {
                "city": row.city,
                "region": row.region,
                "active": 0,
                "failed": 0,
                "inactive": 0,
                "total": 0
            }
        
        city_distribution[key][row.status.value] = row.count
        city_distribution[key]["total"] += row.count
    
    return {
        "summary": {
            "total_proxies": total_proxies,
            "by_status": status_distribution,
            "health_distribution": {
                "healthy": healthy,        # Score >= 80
                "degraded": degraded,      # Score 60-79
                "unhealthy": unhealthy,    # Score < 60
                "no_score": no_score,      # Sin health check
                "offline": offline         # Status FAILED
            }
        },
        "averages": {
            "overall_score": round(averages[0] or 0, 2),
            "avg_latency_ms": round(averages[1] or 0, 2),
            "uptime_percentage": round(averages[2] or 0, 2)
        },
        "distribution_by_city": list(city_distribution.values()),
        "proxies_detail": distribution
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
        new_proxy = await rotator._rotate_to_optimal_location(
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