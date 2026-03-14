# app/api/v1/admin_control.py
"""
Panel de control del administrador:
- Gestionar agentes y sus tokens
- Crear/ver asignaciones (perfil → agente → URL)
- Ver sesiones activas e historial
- Autorizar/denegar sesiones
- WebSocket para actualizaciones en tiempo real
"""
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime
from loguru import logger

from app.database import get_db
from app.services.agent_service import AgentService
from app.schemas.agent import AgentTokenCreate, AgentTokenResponse, SessionListResponse
from app.schemas.assignment import (
    ProfileAssignmentCreate,
    ProfileAssignmentUpdate,
    ProfileAssignmentResponse,
    ProfileAssignmentListResponse
)
from app.core.connection_manager import connection_manager
from app.models.profile_assignment import ProfileAssignment, AgentToken
from app.models.agent_session import AgentSession

router = APIRouter(prefix="/admin", tags=["👑 Admin Control"])


# ========================================
# WEBSOCKET ADMIN (tiempo real)
# ========================================

@router.websocket("/ws")
async def websocket_admin(websocket: WebSocket):
    """
    El panel del admin se conecta aquí para recibir:
    - Sesiones que se abren/cierran
    - Eventos de navegación en tiempo real
    - Métricas de agentes
    - Sesiones pendientes de autorización
    """
    await connection_manager.connect_admin(websocket)
    try:
        while True:
            # El admin puede enviar comandos también
            data = await websocket.receive_json()

            # Por ahora solo ping/pong
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        connection_manager.disconnect_admin(websocket)


# ========================================
# DASHBOARD
# ========================================

@router.get("/dashboard")
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    """Vista general: sesiones activas, datos consumidos, agentes online"""
    service = AgentService(db)
    return await service.get_dashboard_summary()


# ========================================
# GESTIÓN DE AGENTES (tokens)
# ========================================

@router.post("/agents", response_model=AgentTokenResponse, status_code=201)
async def create_agent(
    data: AgentTokenCreate,
    db: AsyncSession = Depends(get_db)
):
    """Crea un nuevo agente y genera su token de acceso"""
    service = AgentService(db)
    try:
        agent = await service.create_agent_token(data.agent_name, data.notes)
        return agent
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/agents")
async def list_agents(db: AsyncSession = Depends(get_db)):
    """Lista todos los agentes con su estado online"""
    service = AgentService(db)
    agents = await service.list_agent_tokens()

    result = []
    for agent in agents:
        # Ver cuántas sesiones activas tiene
        active_result = await db.execute(
            select(AgentSession).where(
                AgentSession.agent_name == agent.agent_name,
                AgentSession.status == "active"
            )
        )
        active_sessions = len(active_result.scalars().all())

        result.append({
            "id": agent.id,
            "agent_name": agent.agent_name,
            "token": agent.token,
            "is_active": agent.is_active,
            "notes": agent.notes,
            "created_at": agent.created_at,
            "last_used_at": agent.last_used_at,
            "active_sessions": active_sessions
        })

    return {"total": len(result), "items": result}


@router.patch("/agents/{agent_id}/toggle")
async def toggle_agent(agent_id: int, db: AsyncSession = Depends(get_db)):
    """Activa o desactiva un agente"""
    result = await db.execute(
        select(AgentToken).where(AgentToken.id == agent_id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente no encontrado")

    agent.is_active = not agent.is_active
    await db.commit()
    return {"id": agent_id, "is_active": agent.is_active}


@router.post("/agents/{agent_id}/regenerate-token")
async def regenerate_token(agent_id: int, db: AsyncSession = Depends(get_db)):
    """Regenera el token de un agente"""
    result = await db.execute(
        select(AgentToken).where(AgentToken.id == agent_id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agente no encontrado")

    agent.token = AgentToken.generate_token()
    await db.commit()
    return {"id": agent_id, "new_token": agent.token}


# ========================================
# ASIGNACIONES
# ========================================

@router.post("/assignments", response_model=ProfileAssignmentResponse, status_code=201)
async def create_assignment(
    data: ProfileAssignmentCreate,
    db: AsyncSession = Depends(get_db)
):
    """Admin asigna un perfil a un agente con una URL objetivo"""
    assignment = ProfileAssignment(
        profile_id=data.profile_id,
        agent_id=data.agent_id,
        target_url=data.target_url,
        assignment_name=data.assignment_name,
        requires_auth=data.requires_auth,
        notes=data.notes,
        is_active=True
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)

    # Enriquecer respuesta
    from app.models.profile import Profile
    profile_r = await db.execute(
        select(Profile).where(Profile.id == data.profile_id)
    )
    profile = profile_r.scalar_one_or_none()

    agent_r = await db.execute(
        select(AgentToken).where(AgentToken.id == data.agent_id)
    )
    agent = agent_r.scalar_one_or_none()

    return ProfileAssignmentResponse(
        id=assignment.id,
        profile_id=assignment.profile_id,
        agent_id=assignment.agent_id,
        agent_name=agent.agent_name if agent else None,
        profile_name=profile.name if profile else None,
        target_url=assignment.target_url,
        assignment_name=assignment.assignment_name,
        is_active=assignment.is_active,
        requires_auth=assignment.requires_auth,
        notes=assignment.notes,
        created_at=assignment.created_at,
        total_sessions=0,
        has_active_session=False
    )


@router.get("/assignments")
async def list_assignments(
    agent_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """Lista todas las asignaciones con filtros"""
    query = select(ProfileAssignment)
    if agent_id:
        query = query.where(ProfileAssignment.agent_id == agent_id)
    if is_active is not None:
        query = query.where(ProfileAssignment.is_active == is_active)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    assignments = list(result.scalars().all())

    enriched = []
    for a in assignments:
        from app.models.profile import Profile
        profile_r = await db.execute(select(Profile).where(Profile.id == a.profile_id))
        profile = profile_r.scalar_one_or_none()

        agent_r = await db.execute(select(AgentToken).where(AgentToken.id == a.agent_id))
        agent = agent_r.scalar_one_or_none()

        # Sesión activa?
        session_r = await db.execute(
            select(AgentSession).where(
                AgentSession.assignment_id == a.id,
                AgentSession.status == "active"
            )
        )
        active = session_r.scalar_one_or_none()

        enriched.append({
            "id": a.id,
            "profile_id": a.profile_id,
            "profile_name": profile.name if profile else None,
            "agent_id": a.agent_id,
            "agent_name": agent.agent_name if agent else None,
            "target_url": a.target_url,
            "assignment_name": a.assignment_name,
            "is_active": a.is_active,
            "requires_auth": a.requires_auth,
            "has_active_session": active is not None,
            "created_at": a.created_at
        })

    return {"total": len(enriched), "items": enriched}


@router.patch("/assignments/{assignment_id}")
async def update_assignment(
    assignment_id: int,
    data: ProfileAssignmentUpdate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(ProfileAssignment).where(ProfileAssignment.id == assignment_id)
    )
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Asignación no encontrada")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(assignment, field, value)

    await db.commit()
    return {"id": assignment_id, "updated": True}


@router.delete("/assignments/{assignment_id}", status_code=204)
async def delete_assignment(
    assignment_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(ProfileAssignment).where(ProfileAssignment.id == assignment_id)
    )
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Asignación no encontrada")

    await db.delete(assignment)
    await db.commit()


# ========================================
# SESIONES ACTIVAS
# ========================================

@router.get("/sessions/active")
async def get_active_sessions(db: AsyncSession = Depends(get_db)):
    """Ver todos los navegadores abiertos en este momento"""
    service = AgentService(db)
    sessions = await service.get_active_sessions()

    return {
        "total": len(sessions),
        "items": [
            {
                "id": s.id,
                "agent_name": s.agent_name,
                "profile_id": s.profile_id,
                "adspower_profile_id": s.adspower_profile_id,
                "target_url": s.target_url,
                "status": s.status,
                "opened_at": s.opened_at,
                "pages_visited": s.pages_visited,
                "total_data_mb": s.total_data_mb,
                "browser_health": s.browser_health,
                "last_url": s.last_url,
                "computer_id": s.computer_id,
                # Métricas en vivo del ejecutable
                "live_metrics": connection_manager.get_live_metrics(s.computer_id)
            }
            for s in sessions
        ]
    }


@router.get("/sessions/{session_id}/events")
async def get_session_events(
    session_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Ver todos los eventos de una sesión específica"""
    result = await db.execute(
        select(AgentSession).where(AgentSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    events_result = await db.execute(
        select(AgentSession).where(AgentSession.id == session_id)
    )

    # Obtener eventos
    from app.models.agent_session import BrowserEvent
    events_r = await db.execute(
        select(BrowserEvent)
        .where(BrowserEvent.session_id == session_id)
        .order_by(BrowserEvent.timestamp)
    )
    events = events_r.scalars().all()

    return {
        "session_id": session_id,
        "agent_name": session.agent_name,
        "total_events": len(events),
        "events": [
            {
                "id": e.id,
                "type": e.event_type,
                "url": e.url,
                "title": (e.details or {}).get("title") if hasattr(e, "details") else None,
                "timestamp": e.timestamp,
                "extra": e.details or {}
            }
            for e in events
        ]
    }


# ========================================
# AUTORIZACIÓN
# ========================================

@router.post("/sessions/{session_id}/authorize")
async def authorize_session(
    session_id: int,
    admin_name: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Admin autoriza una sesión pendiente"""
    service = AgentService(db)
    try:
        return await service.authorize_session(session_id, admin_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sessions/{session_id}/deny")
async def deny_session(
    session_id: int,
    admin_name: str = Query(...),
    reason: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Admin rechaza una sesión pendiente"""
    service = AgentService(db)
    try:
        return await service.deny_session(session_id, admin_name, reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========================================
# ESTADÍSTICAS
# ========================================

@router.get("/stats/data-usage")
async def get_data_usage(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db)
):
    """Consumo de datos por agente en un período"""
    from sqlalchemy import func as sqlfunc

    query = select(
        AgentSession.agent_name,
        sqlfunc.count(AgentSession.id).label("total_sessions"),
        sqlfunc.sum(AgentSession.total_data_mb).label("total_data_mb"),
        sqlfunc.sum(AgentSession.duration_seconds).label("total_seconds"),
        sqlfunc.sum(AgentSession.pages_visited).label("total_pages")
    ).group_by(AgentSession.agent_name)

    if date_from:
        query = query.where(AgentSession.requested_at >= date_from)
    if date_to:
        query = query.where(AgentSession.requested_at <= date_to)

    result = await db.execute(query)
    rows = result.all()

    return {
        "items": [
            {
                "agent_name": row.agent_name,
                "total_sessions": row.total_sessions,
                "total_data_mb": round(row.total_data_mb or 0, 2),
                "total_minutes": round((row.total_seconds or 0) / 60, 1),
                "total_pages": row.total_pages or 0
            }
            for row in rows
        ]
    }

@router.get("/activity-feed")
async def get_activity_feed(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Feed unificado de: sesiones recientes + alertas recientes.
    Usado por SystemEventsFeed del dashboard.
    """
    from app.models.alert import Alert, AlertStatus

    # Sesiones recientes
    sessions_result = await db.execute(
        select(AgentSession)
        .order_by(AgentSession.requested_at.desc())
        .limit(limit // 2)
    )
    sessions = sessions_result.scalars().all()

    # Alertas recientes
    alerts_result = await db.execute(
        select(Alert)
        .order_by(Alert.created_at.desc())
        .limit(limit // 2)
    )
    alerts = alerts_result.scalars().all()

    events = []

    # Importar Profile arriba del loop
    from app.models.profile import Profile

    for s in sessions:
        # Buscar nombre del perfil
        profile_r = await db.get(Profile, s.profile_id)
        profile_name = profile_r.name if profile_r else f"Perfil #{s.profile_id}"
        profile_owner = profile_r.owner if profile_r else None

        event_type = {
            "active":  "SUCCESS",
            "closed":  "INFO",
            "crashed": "ERROR",
            "opening": "INFO",
            "denied":  "WARNING",
        }.get(s.status, "INFO")

        events.append({
            "id":        f"sess-{s.id}",
            "type":      event_type,
            "message":   _session_message(s, profile_name),
            "source":    profile_owner or s.agent_name,   # ← muestra dueño en vez de "admin-panel"
            "timestamp": s.requested_at.isoformat() if s.requested_at else "",
            "meta": {
                "session_id":  s.id,
                "profile_id":  s.profile_id,
                "computer_id": s.computer_id,
                "target_url":  s.target_url,
                "duration_s":  s.duration_seconds,
                "data_mb":     s.total_data_mb,
            }
        })

    for a in alerts:
        events.append({
            "id":        f"alert-{a.id}",
            "type": {"info":"INFO","warning":"WARNING","error":"ERROR","critical":"ERROR"}.get(
                a.severity.value if hasattr(a.severity, 'value') else a.severity, "INFO"
            ),
            "message":   a.title,
            "source":    a.source or "System",
            "timestamp": a.created_at.isoformat(),
            "meta": {
                "alert_id":  a.id,
                "severity":  a.severity if isinstance(a.severity, str) else a.severity.value,
                "status": a.status if isinstance(a.status, str) else a.status.value,
                "message":   a.message,
            }
        })
        

    # Ordenar por timestamp desc
    events.sort(key=lambda e: e["timestamp"], reverse=True)

    return {"total": len(events), "items": events[:limit]}


def _session_message(s: AgentSession, profile_name: str = None) -> str:
    name = profile_name or f"Perfil #{s.profile_id}"
    msgs = {
        "active":  f"Sesión iniciada — {name}",
        "closed":  f"Sesión cerrada — {name} · {s.duration_seconds or 0}s, {round(s.total_data_mb or 0, 1)}MB",
        "crashed": f"Sesión crasheó — {name}",
        "opening": f"Abriendo navegador — {name}",
        "denied":  f"Sesión denegada — {name}",
    }
    return msgs.get(s.status, f"Evento #{s.id}")

@router.get("/sessions/by-profile/{profile_id}")
async def get_sessions_by_profile(
    profile_id: int,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Historial completo de un perfil específico"""
    result = await db.execute(
        select(AgentSession)
        .where(AgentSession.profile_id == profile_id)
        .order_by(AgentSession.requested_at.desc())
        .limit(limit)
    )
    sessions = result.scalars().all()

    return {
        "profile_id": profile_id,
        "total": len(sessions),
        "items": [
            {
                "id":               s.id,
                "agent_name":       s.agent_name,
                "computer_id":      s.computer_id,
                "target_url":       s.target_url,
                "status":           s.status,
                "requested_at":     s.requested_at,
                "opened_at":        s.opened_at,
                "closed_at":        s.closed_at,
                "duration_seconds": s.duration_seconds,
                "pages_visited":    s.pages_visited,
                "total_data_mb":    s.total_data_mb,
                "browser_health":   s.browser_health,
                "last_url":         s.last_url,
            }
            for s in sessions
        ]
    }