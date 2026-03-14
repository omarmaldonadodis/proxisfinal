# app/api/v1/computers.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from app.database import get_db
from app.services.computer_service import ComputerService
from app.schemas.computer import (
    ComputerCreate, ComputerUpdate, ComputerResponse, ComputerListResponse
)
from app.models.computer import Computer, ComputerStatus
from app.models.health_check import HealthCheck
from app.models.agent_session import AgentSession, SessionStatus
from app.models.profile_assignment import AgentToken
from app.core.connection_manager import connection_manager

router = APIRouter(prefix="/computers", tags=["Computers"])


# ============================================================
# RUTAS ESTÁTICAS (antes de /{computer_id})
# ============================================================

@router.get("/with-metrics", summary="Computers con última métrica de CPU/RAM")
async def list_computers_with_metrics(db: AsyncSession = Depends(get_db)):
    """
    JOIN Computer + última HealthCheck.
    Incluye connected_since para que el frontend calcule el uptime real.
    """
    latest_hc_subq = (
        select(func.max(HealthCheck.id))
        .where(HealthCheck.computer_id == Computer.id)
        .correlate(Computer)
        .scalar_subquery()
    )

    result = await db.execute(
        select(Computer, HealthCheck)
        .outerjoin(HealthCheck, HealthCheck.id == latest_hc_subq)
        .where(Computer.is_active == True)
        .order_by(Computer.name)
    )
    rows = result.all()

    items = []
    for computer, hc in rows:
        sessions_result = await db.execute(
            select(func.count(AgentSession.id))
            .where(
                AgentSession.computer_id == computer.id,
                AgentSession.status == SessionStatus.ACTIVE.value
            )
        )
        active_sessions = sessions_result.scalar() or 0

        # Filtrar entradas fantasma (health-check de AdsPower sin datos del SO)
        cpu_value = round(hc.cpu_usage    or 0, 1) if hc else 0
        ram_value = round(hc.memory_usage or 0, 1) if hc else 0

        if ram_value == 0:
            real_hc_result = await db.execute(
                select(HealthCheck)
                .where(HealthCheck.computer_id == computer.id, HealthCheck.memory_usage > 0)
                .order_by(desc(HealthCheck.checked_at))
                .limit(1)
            )
            real_hc = real_hc_result.scalar_one_or_none()
            if real_hc:
                cpu_value = round(real_hc.cpu_usage    or 0, 1)
                ram_value = round(real_hc.memory_usage,     1)

        # ← NUEVO: connected_since desde connection_manager (en memoria, preciso)
        # Si el agente está online devolverá el timestamp real de conexión.
        # Si está offline devolverá None y el frontend mostrará "—".
        connected_since = connection_manager.get_connected_since(computer.id)

        items.append({
            "id":               computer.id,
            "name":             computer.name,
            "hostname":         computer.hostname,
            "ip_address":       computer.ip_address,
            "group":            _get_group_tag(computer.tags),
            "status":           computer.status.value.upper(),
            "openBrowsers":     active_sessions,
            "cpu":              cpu_value,
            "ram":              ram_value,
            "uptime":           _compute_uptime(connected_since),   # ← usa connected_since
            "connected_since":  connected_since.isoformat() if connected_since else None,  # ← NUEVO
            "lastUpdate":       _time_ago(computer.last_seen_at),
            "max_profiles":     computer.max_profiles,
            "adspower_api_url": computer.adspower_api_url,
        })

    return {"total": len(items), "items": items}


@router.get("/stats/summary")
async def get_computers_stats(db: AsyncSession = Depends(get_db)):
    service = ComputerService(db)
    return await service.get_stats()


# ============================================================
# CRUD GENERAL
# ============================================================

@router.post("/", response_model=ComputerResponse, status_code=201)
async def create_computer(computer_in: ComputerCreate, db: AsyncSession = Depends(get_db)):
    service = ComputerService(db)
    try:
        return await service.create_computer(computer_in)
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
    service = ComputerService(db)
    computers, total = await service.list_computers(skip=skip, limit=limit, status=status, is_active=is_active)
    return ComputerListResponse(total=total, items=computers)


# ============================================================
# RUTAS DINÁMICAS (/{computer_id} al final)
# ============================================================

@router.get("/{computer_id}", response_model=ComputerResponse)
async def get_computer(computer_id: int, db: AsyncSession = Depends(get_db)):
    service = ComputerService(db)
    computer = await service.get_computer(computer_id)
    if not computer:
        raise HTTPException(status_code=404, detail="Computer not found")
    return computer


@router.patch("/{computer_id}", response_model=ComputerResponse)
async def update_computer(computer_id: int, computer_in: ComputerUpdate, db: AsyncSession = Depends(get_db)):
    service = ComputerService(db)
    try:
        computer = await service.update_computer(computer_id, computer_in)
        if not computer:
            raise HTTPException(status_code=404, detail="Computer not found")
        return computer
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{computer_id}", status_code=204)
async def delete_computer(computer_id: int, db: AsyncSession = Depends(get_db)):
    service = ComputerService(db)
    try:
        if not await service.delete_computer(computer_id):
            raise HTTPException(status_code=404, detail="Computer not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{computer_id}/health-check")
async def health_check_computer(computer_id: int, db: AsyncSession = Depends(get_db)):
    service = ComputerService(db)
    try:
        return await service.health_check(computer_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{computer_id}/metrics")
async def get_computer_metrics(
    computer_id: int,
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db)
):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    result = await db.execute(
        select(HealthCheck)
        .where(
            HealthCheck.computer_id == computer_id,
            HealthCheck.checked_at  >= cutoff,
            HealthCheck.memory_usage > 0,
        )
        .order_by(HealthCheck.checked_at)
    )
    return [
        {
            "time":           h.checked_at.strftime("%H:%M:%S"),  # ← formato que espera el chart
            "cpu":            round(h.cpu_usage    or 0, 1),
            "ram":            round(h.memory_usage or 0, 1),
            "disk":           round(h.disk_usage   or 0, 1),
            "cpu_percent":    h.cpu_usage,
            "memory_percent": h.memory_usage,
            "disk_percent":   h.disk_usage,
            "recorded_at":    h.checked_at,
        }
        for h in result.scalars().all()
    ]


@router.get("/{computer_id}/metrics/latest")
async def get_computer_metrics_latest(computer_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(HealthCheck)
        .where(HealthCheck.computer_id == computer_id, HealthCheck.memory_usage > 0)
        .order_by(desc(HealthCheck.checked_at))
        .limit(1)
    )
    h = result.scalar_one_or_none()
    if not h:
        raise HTTPException(status_code=404, detail="No metrics found")
    return {
        "computer_id":      h.computer_id,
        "cpu_percent":      h.cpu_usage,
        "memory_percent":   h.memory_usage,
        "disk_percent":     h.disk_usage,
        "adspower_running": h.active_profiles,
        "is_healthy":       h.is_healthy,
        "status":           "online" if h.is_healthy else "degraded",
        "recorded_at":      h.checked_at,
    }


@router.post("/{computer_id}/diagnostics")
async def run_diagnostics(computer_id: int, db: AsyncSession = Depends(get_db)):
    service = ComputerService(db)
    computer = await service.get_computer(computer_id)
    if not computer:
        raise HTTPException(status_code=404, detail="Computer not found")

    health = await service.health_check(computer_id)

    result = await db.execute(
        select(HealthCheck)
        .where(HealthCheck.computer_id == computer_id, HealthCheck.memory_usage > 0)
        .order_by(desc(HealthCheck.checked_at))
        .limit(1)
    )
    latest = result.scalar_one_or_none()

    return {
        "computer_id":     computer_id,
        "name":            computer.name,
        "ip_address":      computer.ip_address,
        "status":          computer.status,
        "overall_healthy": health.get("is_healthy", False),
        "checks": {
            "adspower":  health.get("adspower_status") == "online",
            "cpu_ok":    (latest.cpu_usage    or 0) < 85 if latest else None,
            "memory_ok": (latest.memory_usage or 0) < 90 if latest else None,
            "disk_ok":   (latest.disk_usage   or 0) < 95 if latest else None,
        },
        "latest_metrics": {
            "cpu_percent":      latest.cpu_usage      if latest else None,
            "memory_percent":   latest.memory_usage   if latest else None,
            "disk_percent":     latest.disk_usage     if latest else None,
            "adspower_running": latest.active_profiles if latest else None,
            "recorded_at":      latest.checked_at     if latest else None,
        },
    }


@router.post("/{computer_id}/restart-adspower")
async def restart_adspower(computer_id: int, db: AsyncSession = Depends(get_db)):
    service = ComputerService(db)
    computer = await service.get_computer(computer_id)
    if not computer:
        raise HTTPException(status_code=404, detail="Computer not found")
    if computer.status != ComputerStatus.ONLINE:
        raise HTTPException(status_code=409, detail="Computer is offline")

    sent = await connection_manager.send_to_agent(computer_id, {"type": "restart_adspower", "payload": {}})
    return {"success": sent, "computer_id": computer_id}


@router.get("/{computer_id}/logs")
async def get_computer_logs(
    computer_id: int,
    lines: int = Query(100, ge=10, le=1000),
    db: AsyncSession = Depends(get_db)
):
    computer = await db.get(Computer, computer_id)
    if not computer:
        raise HTTPException(status_code=404, detail="Computer not found")

    result = await db.execute(
        select(HealthCheck)
        .where(HealthCheck.computer_id == computer_id)
        .order_by(desc(HealthCheck.checked_at))
        .limit(lines)
    )
    checks = result.scalars().all()

    sessions_result = await db.execute(
        select(AgentSession)
        .where(AgentSession.computer_id == computer_id)
        .order_by(desc(AgentSession.requested_at))
        .limit(20)
    )
    sessions = sessions_result.scalars().all()

    logs = []

    for s in sessions:
        if s.status == SessionStatus.ACTIVE:
            logs.append({
                "timestamp": s.opened_at.isoformat() if s.opened_at else s.requested_at.isoformat(),
                "level":   "SUCCESS",
                "message": f"Sesión ACTIVA — perfil #{s.profile_id} en {s.target_url or 'N/A'} [{s.agent_name}]"
            })
        elif s.status == SessionStatus.CLOSED:
            logs.append({
                "timestamp": s.closed_at.isoformat() if s.closed_at else s.requested_at.isoformat(),
                "level":   "INFO",
                "message": f"Sesión cerrada — {s.duration_seconds or 0}s, {s.pages_visited or 0} páginas [{s.agent_name}]"
            })
        elif s.status == SessionStatus.CRASHED:
            logs.append({
                "timestamp": s.closed_at.isoformat() if s.closed_at else s.requested_at.isoformat(),
                "level":   "ERROR",
                "message": f"Sesión CRASHEADA — {s.error_detail or 'unknown'} [{s.agent_name}]"
            })

    for h in reversed(checks):
        if not h.memory_usage or h.memory_usage == 0:
            continue
        logs.append({
            "timestamp": h.checked_at.isoformat(),
            "level":   "INFO" if h.is_healthy else "WARNING",
            "message": f"cpu={h.cpu_usage}% mem={h.memory_usage}% disk={h.disk_usage}% adspower={h.adspower_status}"
        })

    live_logs = connection_manager.get_agent_logs(computer_id)
    all_logs  = sorted(logs + live_logs, key=lambda x: x["timestamp"])
    return {"computer_id": computer_id, "name": computer.name, "logs": all_logs[-lines:]}


# ============================================================
# HELPERS
# ============================================================

def _get_group_tag(tags: list) -> str:
    if not tags:             return "STANDARD"
    if "elite"     in tags:  return "ELITE"
    if "incubator" in tags:  return "INCUBATOR"
    return "STANDARD"


def _compute_uptime(connected_since: Optional[datetime]) -> str:
    """
    Calcula uptime desde el momento real de conexión del agente (en memoria).
    Muestra minutos si es < 1 hora.
    Devuelve "—" si el agente está offline o no registrado.
    """
    if not connected_since:
        return "—"

    now   = datetime.utcnow()
    since = connected_since.replace(tzinfo=None)

    if since > now:
        return "0m"

    total_s = int((now - since).total_seconds())
    days    = total_s // 86400
    hours   = (total_s % 86400) // 3600
    mins    = (total_s % 3600)  // 60

    if days  > 0: return f"{days}d {hours}h"
    if hours > 0: return f"{hours}h {mins}m"
    return f"{mins}m"


def _time_ago(dt: datetime) -> str:
    if not dt: return "never"
    delta = datetime.utcnow() - dt.replace(tzinfo=None)
    s = int(delta.total_seconds())
    if s < 0:    return "just now"
    if s < 60:   return f"{s}s ago"
    if s < 3600: return f"{s // 60}m ago"
    return f"{s // 3600}h ago"