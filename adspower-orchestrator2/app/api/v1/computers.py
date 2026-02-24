# app/api/v1/computers.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.database import get_db
from app.services.computer_service import ComputerService
from app.schemas.computer import (
    ComputerCreate,
    ComputerUpdate,
    ComputerResponse,
    ComputerListResponse
)
from app.models.computer import ComputerStatus

# Agregar a los imports existentes:
from sqlalchemy import select, desc
from datetime import datetime, timedelta, timezone
from app.models.health_check import HealthCheck
from app.core.connection_manager import connection_manager


router = APIRouter(prefix="/computers", tags=["Computers"])

@router.post("/", response_model=ComputerResponse, status_code=201)
async def create_computer(
    computer_in: ComputerCreate,
    db: AsyncSession = Depends(get_db)
):
    """Crea un nuevo computer"""
    service = ComputerService(db)
    try:
        computer = await service.create_computer(computer_in)
        return computer
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=ComputerListResponse)
async def list_computers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[ComputerStatus] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """Lista computers con filtros"""
    service = ComputerService(db)
    computers, total = await service.list_computers(
        skip=skip,
        limit=limit,
        status=status,
        is_active=is_active
    )
    return ComputerListResponse(total=total, items=computers)

@router.get("/{computer_id}", response_model=ComputerResponse)
async def get_computer(
    computer_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Obtiene computer por ID"""
    service = ComputerService(db)
    computer = await service.get_computer(computer_id)
    if not computer:
        raise HTTPException(status_code=404, detail="Computer not found")
    return computer

@router.patch("/{computer_id}", response_model=ComputerResponse)
async def update_computer(
    computer_id: int,
    computer_in: ComputerUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Actualiza computer"""
    service = ComputerService(db)
    try:
        computer = await service.update_computer(computer_id, computer_in)
        if not computer:
            raise HTTPException(status_code=404, detail="Computer not found")
        return computer
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{computer_id}", status_code=204)
async def delete_computer(
    computer_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Elimina computer"""
    service = ComputerService(db)
    try:
        success = await service.delete_computer(computer_id)
        if not success:
            raise HTTPException(status_code=404, detail="Computer not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{computer_id}/health-check")
async def health_check_computer(
    computer_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Verifica salud del computer"""
    service = ComputerService(db)
    try:
        result = await service.health_check(computer_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/stats/summary")
async def get_computers_stats(
    db: AsyncSession = Depends(get_db)
):
    """Obtiene estadísticas de computers"""
    service = ComputerService(db)
    stats = await service.get_stats()
    return stats

@router.get("/{computer_id}/metrics")
async def get_computer_metrics(
    computer_id: int,
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db)
):
    """Serie de tiempo de métricas — usa tu tabla health_checks existente"""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    result = await db.execute(
        select(HealthCheck)
        .where(
            HealthCheck.computer_id == computer_id,
            HealthCheck.checked_at >= cutoff
        )
        .order_by(HealthCheck.checked_at)
    )
    checks = result.scalars().all()
    return [
        {
            "computer_id": h.computer_id,
            "cpu_percent": h.cpu_usage,
            "memory_percent": h.memory_usage,
            "disk_percent": h.disk_usage,
            "adspower_running": h.active_profiles,
            "status": "online" if h.is_healthy else "degraded",
            "recorded_at": h.checked_at,
        }
        for h in checks
    ]


@router.get("/{computer_id}/metrics/latest")
async def get_computer_metrics_latest(
    computer_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Métrica más reciente del nodo"""
    result = await db.execute(
        select(HealthCheck)
        .where(HealthCheck.computer_id == computer_id)
        .order_by(desc(HealthCheck.checked_at))
        .limit(1)
    )
    h = result.scalar_one_or_none()
    if not h:
        raise HTTPException(status_code=404, detail="No metrics found")
    return {
        "computer_id": h.computer_id,
        "cpu_percent": h.cpu_usage,
        "memory_percent": h.memory_usage,
        "disk_percent": h.disk_usage,
        "adspower_running": h.active_profiles,
        "is_healthy": h.is_healthy,
        "response_time_ms": h.response_time_ms,
        "status": "online" if h.is_healthy else "degraded",
        "recorded_at": h.checked_at,
    }


@router.post("/{computer_id}/diagnostics")
async def run_diagnostics(
    computer_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Diagnóstico completo — corre health_check y lo enriquece"""
    service = ComputerService(db)
    computer = await service.get_computer(computer_id)
    if not computer:
        raise HTTPException(status_code=404, detail="Computer not found")

    # Reutiliza tu health_check existente
    health = await service.health_check(computer_id)

    # Última métrica
    result = await db.execute(
        select(HealthCheck)
        .where(HealthCheck.computer_id == computer_id)
        .order_by(desc(HealthCheck.checked_at))
        .limit(1)
    )
    latest = result.scalar_one_or_none()

    return {
        "computer_id": computer_id,
        "name": computer.name,
        "ip_address": computer.ip_address,
        "status": computer.status,
        "overall_healthy": health.get("is_healthy", False),
        "checks": {
            "adspower": health.get("adspower_status") == "online",
            "cpu_ok": (latest.cpu_usage or 0) < 85 if latest else None,
            "memory_ok": (latest.memory_usage or 0) < 90 if latest else None,
            "disk_ok": (latest.disk_usage or 0) < 95 if latest else None,
        },
        "latest_metrics": {
            "cpu_percent": latest.cpu_usage if latest else None,
            "memory_percent": latest.memory_usage if latest else None,
            "disk_percent": latest.disk_usage if latest else None,
            "adspower_running": latest.active_profiles if latest else None,
            "recorded_at": latest.checked_at if latest else None,
        },
        "health_detail": health,
    }


@router.post("/{computer_id}/restart-adspower")
async def restart_adspower(
    computer_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Envía comando de reinicio al agente via WebSocket"""
    service = ComputerService(db)
    computer = await service.get_computer(computer_id)
    if not computer:
        raise HTTPException(status_code=404, detail="Computer not found")
    if computer.status != ComputerStatus.ONLINE:
        raise HTTPException(status_code=409, detail="Computer is offline")

    # Usa tu connection_manager existente
    sent = await connection_manager.send_to_agent(
        computer_id,
        {"type": "restart_adspower", "payload": {}}
    )
    return {"success": sent, "computer_id": computer_id}


@router.get("/{computer_id}/logs")
async def get_computer_logs(
    computer_id: int,
    lines: int = Query(100, ge=10, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """Últimos registros de health_checks como log entries"""
    service = ComputerService(db)
    computer = await service.get_computer(computer_id)
    if not computer:
        raise HTTPException(status_code=404, detail="Computer not found")

    result = await db.execute(
        select(HealthCheck)
        .where(HealthCheck.computer_id == computer_id)
        .order_by(desc(HealthCheck.checked_at))
        .limit(lines)
    )
    checks = result.scalars().all()

    return {
        "computer_id": computer_id,
        "name": computer.name,
        "logs": [
            {
                "timestamp": h.checked_at.isoformat(),
                "level": "INFO" if h.is_healthy else "WARNING",
                "message": (
                    f"cpu={h.cpu_usage}% mem={h.memory_usage}% "
                    f"disk={h.disk_usage}% profiles={h.active_profiles} "
                    f"adspower={h.adspower_status}"
                ),
            }
            for h in reversed(checks)
        ],
    }