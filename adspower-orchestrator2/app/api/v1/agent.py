# app/api/v1/agent.py
#
# LÓGICA CORRECTA:
# - Cualquier computer puede abrir cualquier perfil
# - Incluso abrir solo una URL sin perfil se registra
# - El tracking es: computer_id + profile_id (opcional) + url + timestamps
#
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.database import get_db
from app.models.profile import Profile, ProfileStatus
from app.models.agent_session import AgentSession, SessionStatus
from app.models.computer import Computer, ComputerStatus
from app.core.connection_manager import connection_manager

router = APIRouter()


# ══════════════════════════════════════════════════════════════════════════════
# WebSocket del agente — cada computadora se conecta aquí
# ══════════════════════════════════════════════════════════════════════════════

@router.websocket("/ws/{computer_id}")
async def agent_websocket(websocket: WebSocket, computer_id: int, db: AsyncSession = Depends(get_db)):
    """WebSocket persistente para cada agente. Recibe comandos y envía eventos."""
    await connection_manager.connect_agent(computer_id, websocket)

    # Marcar computadora como ONLINE
    result = await db.execute(select(Computer).where(Computer.id == computer_id))
    computer = result.scalar_one_or_none()
    if computer:
        computer.status       = ComputerStatus.ONLINE
        computer.last_seen_at = datetime.utcnow()
        await db.commit()

        await connection_manager.broadcast_to_admins({
            "type":        "agent_online",
            "computer_id": computer_id,
            "name":        computer.name,
            "timestamp":   datetime.utcnow().isoformat(),
        })

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "metrics":
                # El agente reporta CPU/RAM en tiempo real
                await connection_manager.broadcast_to_admins({
                    "type":        "agent_metrics",
                    "computer_id": computer_id,
                    "data":        data.get("data", {}),
                    "timestamp":   datetime.utcnow().isoformat(),
                })

            elif msg_type == "session_opened":
                # Confirma que el navegador se abrió
                session_id = data.get("session_id")
                if session_id:
                    sess = await db.get(AgentSession, session_id)
                    if sess:
                        sess.status    = SessionStatus.ACTIVE
                        sess.opened_at = datetime.utcnow()
                        await db.commit()

                        await connection_manager.broadcast_to_admins({
                            "type":        "session_active",
                            "session_id":  session_id,
                            "computer_id": computer_id,
                            "profile_id":  sess.profile_id,
                            "target_url":  sess.target_url,
                            "timestamp":   datetime.utcnow().isoformat(),
                        })

            elif msg_type == "session_closed":
                # Navegador cerrado
                session_id = data.get("session_id")
                if session_id:
                    sess = await db.get(AgentSession, session_id)
                    if sess:
                        sess.status           = SessionStatus.CLOSED
                        sess.closed_at        = datetime.utcnow()
                        sess.duration_seconds = data.get("duration_seconds")
                        sess.pages_visited    = data.get("pages_visited", 0)
                        sess.total_data_mb    = data.get("total_data_mb", 0.0)
                        sess.last_url         = data.get("last_url")
                        await db.commit()

                        await connection_manager.broadcast_to_admins({
                            "type":             "session_closed",
                            "session_id":       session_id,
                            "computer_id":      computer_id,
                            "duration_seconds": sess.duration_seconds,
                            "timestamp":        datetime.utcnow().isoformat(),
                        })

            elif msg_type == "profile_created":
                # El agente creó el perfil en AdsPower y reporta el adspower_id real
                profile_id   = data.get("profile_id")
                adspower_id  = data.get("adspower_id")
                if profile_id and adspower_id:
                    from app.services.profile_service import ProfileService
                    svc = ProfileService(db)
                    await svc.set_adspower_id(profile_id, adspower_id)

                    await connection_manager.broadcast_to_admins({
                        "type":        "profile_ready",
                        "profile_id":  profile_id,
                        "adspower_id": adspower_id,
                        "computer_id": computer_id,
                        "timestamp":   datetime.utcnow().isoformat(),
                    })

            elif msg_type == "page_visit":
                # Registrar visita a URL (incluso sin perfil)
                session_id = data.get("session_id")
                url        = data.get("url")
                if session_id:
                    sess = await db.get(AgentSession, session_id)
                    if sess:
                        sess.last_url      = url
                        sess.pages_visited = (sess.pages_visited or 0) + 1
                        events = sess.events or []
                        events.append({
                            "type":      "page_visit",
                            "url":       url,
                            "timestamp": datetime.utcnow().isoformat(),
                        })
                        sess.events = events
                        await db.commit()

            elif msg_type == "error":
                session_id = data.get("session_id")
                if session_id:
                    sess = await db.get(AgentSession, session_id)
                    if sess:
                        sess.status       = SessionStatus.CRASHED
                        sess.error_detail = data.get("error")
                        sess.closed_at    = datetime.utcnow()
                        await db.commit()

                        await connection_manager.broadcast_to_admins({
                            "type":        "session_crashed",
                            "session_id":  session_id,
                            "computer_id": computer_id,
                            "error":       data.get("error"),
                            "timestamp":   datetime.utcnow().isoformat(),
                        })

    except WebSocketDisconnect:
        pass
    finally:
        connection_manager.disconnect_agent(computer_id)

        # Marcar computadora como OFFLINE
        result = await db.execute(select(Computer).where(Computer.id == computer_id))
        computer = result.scalar_one_or_none()
        if computer:
            computer.status = ComputerStatus.OFFLINE
            await db.commit()

        await connection_manager.broadcast_to_admins({
            "type":        "agent_offline",
            "computer_id": computer_id,
            "timestamp":   datetime.utcnow().isoformat(),
        })


# ══════════════════════════════════════════════════════════════════════════════
# CHECK-IN del agente al conectarse
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/checkin")
async def agent_checkin(
    computer_id: int = Query(..., description="ID de la computadora"),
    agent_name:  str = Query("agent", description="Nombre del agente"),
    db: AsyncSession = Depends(get_db),
):
    """El ejecutable llama esto al arrancar. Registra hora de ingreso y marca ONLINE."""
    result = await db.execute(select(Computer).where(Computer.id == computer_id))
    computer = result.scalar_one_or_none()
    if not computer:
        raise HTTPException(status_code=404, detail="Computer not found")

    computer.status       = ComputerStatus.ONLINE
    computer.last_seen_at = datetime.utcnow()
    await db.commit()

    await connection_manager.broadcast_to_admins({
        "type":        "agent_checkin",
        "computer_id": computer_id,
        "agent_name":  agent_name,
        "name":        computer.name,
        "timestamp":   datetime.utcnow().isoformat(),
    })

    return {
        "computer_id": computer_id,
        "checked_in":  True,
        "timestamp":   datetime.utcnow().isoformat(),
    }


# ══════════════════════════════════════════════════════════════════════════════
# ABRIR NAVEGADOR CON PERFIL (desde el panel admin)
# Cualquier computadora puede abrir cualquier perfil
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/open-browser/direct")
async def open_browser_direct(
    profile_adspower_id: str = Query(..., description="adspower_id del perfil"),
    computer_id:         int = Query(..., description="ID de la computadora que abrirá el navegador"),
    target_url:          str = Query("https://www.google.com"),
    agent_name:          str = Query("admin"),
    db: AsyncSession = Depends(get_db),
):
    """
    Abre un perfil AdsPower en una computadora específica.
    - computer_id: SOLO dice DESDE Qué computadora se abre, NO es el "dueño" del perfil.
    - El perfil es global y puede abrirse desde cualquier computadora.
    - Verifica que el perfil no esté ya activo en otra computadora.
    """
    # Buscar el perfil por adspower_id
    result = await db.execute(
        select(Profile).where(Profile.adspower_id == profile_adspower_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail=f"Perfil '{profile_adspower_id}' no encontrado")

    # Verificar que no haya sesión activa en NINGUNA computadora
    existing = await db.execute(
        select(AgentSession).where(
            AgentSession.profile_id == profile.id,
            AgentSession.status.in_([SessionStatus.ACTIVE, SessionStatus.OPENING]),
        )
    )
    active_session = existing.scalar_one_or_none()
    if active_session:
        raise HTTPException(
            status_code=409,
            detail=f"El perfil ya está activo en la computadora #{active_session.computer_id}",
        )

    # Crear registro de sesión
    session = AgentSession(
        computer_id=         computer_id,
        profile_id=          profile.id,
        adspower_profile_id= profile_adspower_id,
        agent_name=          agent_name,
        target_url=          target_url,
        status=              SessionStatus.OPENING,
        requested_at=        datetime.utcnow(),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Enviar comando al agente
    sent = await connection_manager.send_command_to_agent(
        computer_id=computer_id,
        command="open_browser",
        payload={
            "session_id":  session.id,
            "profile_id":  profile_adspower_id,
            "target_url":  target_url,
        }
    )

    # Actualizar last_action del perfil
    profile.last_action    = "OPEN"
    profile.last_opened_at = datetime.utcnow()
    await db.commit()

    # Notificar admins
    await connection_manager.broadcast_to_admins({
        "type":        "session_created",
        "session_id":  session.id,
        "agent_name":  agent_name,
        "profile":     profile.name,
        "profile_id":  profile.id,
        "computer_id": computer_id,
        "target_url":  target_url,
        "timestamp":   datetime.utcnow().isoformat(),
    })

    return {
        "session_id":  session.id,
        "status":      "opening",
        "profile":     profile.name,
        "computer_id": computer_id,
        "command_sent": sent,
        "message":     f"Abriendo '{profile.name}' en computadora #{computer_id}",
    }


# ══════════════════════════════════════════════════════════════════════════════
# ABRIR URL SIN PERFIL (el agente abre solo una URL, se registra igualmente)
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/open-browser")
async def open_browser_url(
    url:         str = Query(..., description="URL a abrir"),
    computer_id: int = Query(..., description="ID de la computadora"),
    agent_name:  str = Query("agent", description="Nombre del agente"),
    db: AsyncSession = Depends(get_db),
):
    """
    Abre el navegador en una URL específica SIN perfil de AdsPower.
    Se registra la sesión igualmente con profile_id=NULL.
    Útil para verificaciones manuales, testeos, etc.
    """
    # Crear registro de sesión sin perfil
    session = AgentSession(
        computer_id=  computer_id,
        profile_id=   None,           # Sin perfil
        agent_name=   agent_name,
        target_url=   url,
        status=       SessionStatus.OPENING,
        requested_at= datetime.utcnow(),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Enviar comando al agente
    sent = await connection_manager.send_command_to_agent(
        computer_id=computer_id,
        command="open_url",
        payload={
            "session_id": session.id,
            "url":        url,
        }
    )

    # Notificar admins
    await connection_manager.broadcast_to_admins({
        "type":        "session_created",
        "session_id":  session.id,
        "agent_name":  agent_name,
        "profile":     None,
        "computer_id": computer_id,
        "target_url":  url,
        "timestamp":   datetime.utcnow().isoformat(),
    })

    return {
        "session_id":  session.id,
        "status":      "opening",
        "url":         url,
        "computer_id": computer_id,
        "command_sent": sent,
    }


# ══════════════════════════════════════════════════════════════════════════════
# REGISTRAR AGENTE (al arrancar el ejecutable por primera vez)
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/register")
async def register_agent(
    name:        str = Query(...),
    hostname:    str = Query(...),
    ip_address:  str = Query(""),
    db: AsyncSession = Depends(get_db),
):
    """Registra una nueva computadora en el sistema."""
    # Verificar si ya existe
    result = await db.execute(
        select(Computer).where(Computer.hostname == hostname)
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.status       = ComputerStatus.ONLINE
        existing.last_seen_at = datetime.utcnow()
        await db.commit()
        return {"computer_id": existing.id, "name": existing.name, "registered": False}

    computer = Computer(
        name=         name,
        hostname=     hostname,
        ip_address=   ip_address,
        status=       ComputerStatus.ONLINE,
        last_seen_at= datetime.utcnow(),
        max_profiles= 10,
        is_active=    True,
    )
    db.add(computer)
    await db.commit()
    await db.refresh(computer)

    await connection_manager.broadcast_to_admins({
        "type":        "agent_registered",
        "computer_id": computer.id,
        "name":        computer.name,
        "timestamp":   datetime.utcnow().isoformat(),
    })

    return {"computer_id": computer.id, "name": computer.name, "registered": True}