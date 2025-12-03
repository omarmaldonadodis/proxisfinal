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
    proxies, total = await service.list_proxies(
        skip=skip,
        limit=limit,
        proxy_type=proxy_type,
        country=country,
        status=status
    )
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