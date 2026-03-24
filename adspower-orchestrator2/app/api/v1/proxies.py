# app/api/v1/proxies.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.database import get_db
from app.services.proxy_service import ProxyService
from app.schemas.proxy import (
    ProxyCreate,
    ProxyUpdate,
    ProxyResponse,
    ProxyListResponse,
    ProxyTestResponse
)
from app.models.proxy import ProxyType, ProxyStatus

# Agregar a los imports existentes:
from app.models.proxy_rotation_log import ProxyRotationLog, RotationTrigger
from sqlalchemy import select, desc
from datetime import datetime, timedelta, timezone

router = APIRouter(prefix="/proxies", tags=["Proxies"])

@router.post("/", response_model=ProxyResponse, status_code=201)
async def create_proxy(
    proxy_in: ProxyCreate,
    db: AsyncSession = Depends(get_db)
):
    """Crea un nuevo proxy"""
    service = ProxyService(db)
    try:
        proxy = await service.create_proxy(proxy_in)
        return proxy
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=ProxyListResponse)
async def list_proxies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    proxy_type: Optional[ProxyType] = None,
    country: Optional[str] = None,
    status: Optional[ProxyStatus] = None,
    db: AsyncSession = Depends(get_db)
):
    """Lista proxies con filtros"""
    service = ProxyService(db)
    proxies, total = await service.list_proxies(status=status, proxy_type=proxy_type, skip=skip, limit=limit)

    return ProxyListResponse(total=total, items=proxies)

@router.get("/{proxy_id}", response_model=ProxyResponse)
async def get_proxy(
    proxy_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Obtiene proxy por ID"""
    service = ProxyService(db)
    proxy = await service.get_proxy(proxy_id)
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    return proxy

@router.patch("/{proxy_id}", response_model=ProxyResponse)
async def update_proxy(
    proxy_id: int,
    proxy_in: ProxyUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Actualiza proxy"""
    service = ProxyService(db)
    try:
        proxy = await service.update_proxy(proxy_id, proxy_in)
        if not proxy:
            raise HTTPException(status_code=404, detail="Proxy not found")
        return proxy
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{proxy_id}", status_code=204)
async def delete_proxy(
    proxy_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Elimina proxy"""
    service = ProxyService(db)
    try:
        success = await service.delete_proxy(proxy_id)
        if not success:
            raise HTTPException(status_code=404, detail="Proxy not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{proxy_id}/test", response_model=ProxyTestResponse)
async def test_proxy(
    proxy_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Prueba un proxy"""
    service = ProxyService(db)
    try:
        result = await service.test_proxy(proxy_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/health-check/batch")
async def health_check_batch(
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Health check en batch"""
    service = ProxyService(db)
    result = await service.health_check_batch(limit=limit)
    return result

@router.get("/stats/summary")
async def get_proxies_stats(
    db: AsyncSession = Depends(get_db)
):
    """Obtiene estadísticas de proxies"""
    service = ProxyService(db)
    stats = await service.get_stats()
    return stats

@router.post("/{proxy_id}/health-check")
async def health_check_proxy(
    proxy_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Alias de /test para compatibilidad con el frontend"""
    service = ProxyService(db)
    try:
        result = await service.test_proxy(proxy_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{proxy_id}/rotate")
async def rotate_proxy(
    proxy_id: int,
    profile_id: Optional[int] = None,
    computer_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Rota el proxy usando tu ProxyRotationService existente y guarda el historial"""
    from app.services.proxy_rotation_service import ProxyRotationService

    service = ProxyRotationService(db)
    try:
        result = await service.check_and_rotate_proxy(proxy_id)

        # Guardar en historial
        log = ProxyRotationLog(
            proxy_id=proxy_id,
            profile_id=profile_id,
            computer_id=computer_id,
            old_proxy_display=result.get("old_proxy"),
            new_proxy_display=result.get("new_proxy"),
            trigger=RotationTrigger.MANUAL,
            success=not result.get("error"),
            error_message=result.get("error"),
            latency_ms=result.get("new_latency_ms"),
            ip_address=result.get("new_ip"),
        )
        db.add(log)
        await db.commit()

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rotation-history")
async def get_rotation_history(
    proxy_id: Optional[int] = None,
    profile_id: Optional[int] = None,
    computer_id: Optional[int] = None,
    hours: int = Query(48, ge=1, le=720),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """Historial de rotaciones con filtros"""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    query = (
        select(ProxyRotationLog)
        .where(ProxyRotationLog.created_at >= cutoff)
        .order_by(desc(ProxyRotationLog.created_at))
    )
    if proxy_id:
        query = query.where(ProxyRotationLog.proxy_id == proxy_id)
    if profile_id:
        query = query.where(ProxyRotationLog.profile_id == profile_id)
    if computer_id:
        query = query.where(ProxyRotationLog.computer_id == computer_id)

    result = await db.execute(query.limit(limit))
    logs = result.scalars().all()
    return {"total": len(logs), "items": logs}

# ══════════════════════════════════════════════════════════════════════════════
# SOAX — Países y ciudades disponibles
# ══════════════════════════════════════════════════════════════════════════════


@router.get("/soax/countries")
async def get_soax_countries():
    """
    Retorna los países disponibles en SOAX con sus códigos ISO.
    Lista estática curada — SOAX soporta proxies residenciales en estos países.
    """
    countries = [
        {"code": "ec", "name": "Ecuador"},
        {"code": "es", "name": "España"},
        {"code": "co", "name": "Colombia"},
        {"code": "pe", "name": "Perú"},
        {"code": "mx", "name": "México"},
        {"code": "ar", "name": "Argentina"},
        {"code": "cl", "name": "Chile"},
        {"code": "us", "name": "Estados Unidos"},
        {"code": "gb", "name": "Reino Unido"},
        {"code": "de", "name": "Alemania"},
        {"code": "fr", "name": "Francia"},
        {"code": "it", "name": "Italia"},
        {"code": "br", "name": "Brasil"},
        {"code": "jp", "name": "Japón"},
        {"code": "kr", "name": "Corea del Sur"},
    ]
    return {"countries": countries, "total": len(countries)}


@router.get("/soax/cities")
async def get_soax_cities(
    country: str = Query(
        "ec", description="Código ISO del país (ej: ec, es, co)"),
    conn_type: str = Query(
        "mobile", description="Tipo de conexión: mobile o wifi"),
    force_refresh: bool = Query(
        False, description="Forzar actualización del caché"),
):
    """
    Retorna ciudades disponibles en SOAX para un país dado.
    Consulta la API de SOAX en tiempo real con caché de 5 minutos.
    """
    from app.utils.soax_cities_manager import SOAXCitiesManager

    try:
        cities = await SOAXCitiesManager.get_available_cities(
            country=country,
            conn_type=conn_type,
            force_refresh=force_refresh
        )
        return {
            "country": country,
            "conn_type": conn_type,
            "cities": cities,
            "total": len(cities),
            "cached": not force_refresh,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error consultando SOAX: {str(e)}")
