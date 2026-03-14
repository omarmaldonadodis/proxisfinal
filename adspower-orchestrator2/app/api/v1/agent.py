# app/api/v1/agent.py
#
# LÓGICA CORRECTA:
# - Cualquier computer puede abrir cualquier perfil
# - Incluso abrir solo una URL sin perfil se registra
# - El tracking es: computer_id + profile_id (opcional) + url + timestamps
#
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query, Header
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.database import get_db
from app.models.profile import Profile, ProfileStatus
from app.models.agent_session import AgentSession, SessionStatus
from app.models.computer import Computer, ComputerStatus
from app.core.connection_manager import connection_manager
from app.config import settings

from app.database import AsyncSessionLocal



from pydantic import BaseModel
from app.core.security import verify_token  # o como tengas la validación
import asyncio

router = APIRouter(prefix="/agent", tags=["Agent"])


# ══════════════════════════════════════════════════════════════════════════════
# WebSocket del agente — cada computadora se conecta aquí
# ══════════════════════════════════════════════════════════════════════════════

@router.websocket("/ws/{computer_id}")
async def agent_websocket(websocket: WebSocket, computer_id: int, db: AsyncSession = Depends(get_db)):
    """WebSocket persistente para cada agente. Recibe comandos y envía eventos."""
    await connection_manager.connect_agent(websocket, computer_id)
    # Marcar computadora como ONLINE
    result = await db.execute(select(Computer).where(Computer.id == computer_id))
    computer = result.scalar_one_or_none()
    if computer:
        computer.status       = ComputerStatus.ONLINE
        computer.last_seen_at = datetime.utcnow()
        await db.commit()

        asyncio.create_task(_process_pending_profiles(computer_id))  # ← sin db


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
                metrics_data = data.get("data", {})
                await connection_manager.broadcast_to_admins({
                    "type":        "agent_metrics",
                    "computer_id": computer_id,
                    "data":        metrics_data,
                    "timestamp":   datetime.utcnow().isoformat(),
                })
                # ← AGREGAR: persistir en DB
                await connection_manager._save_metrics_to_db(computer_id, metrics_data)
                
                # ← AGREGAR: actualizar last_seen
                if computer:
                    computer.last_seen_at = datetime.utcnow()
                    await db.commit()

            
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
                session_id = data.get("session_id")
                if session_id:
                    sess = await db.get(AgentSession, session_id)
                    if sess:
                        sess.status        = SessionStatus.CLOSED
                        sess.closed_at     = datetime.utcnow()
                        sess.pages_visited = data.get("pages_visited", 0)
                        sess.total_data_mb = data.get("total_data_mb", 0.0)

                        if sess.opened_at:
                            delta = datetime.utcnow() - sess.opened_at.replace(tzinfo=None)
                            sess.duration_seconds = int(delta.total_seconds())

                        if data.get("crash_reason"):
                            sess.status       = SessionStatus.CRASHED
                            sess.error_detail = data.get("crash_reason")

                        await db.commit()

                        # ← AGREGAR: si el perfil tuvo sesión real, marcar cookies como OK
                        if sess.profile_id and sess.pages_visited and sess.pages_visited > 0:
                            from app.models.profile import Profile
                            profile = await db.get(Profile, sess.profile_id)
                            if profile:
                                profile.cookie_status  = "OK"
                                profile.total_sessions = (profile.total_sessions or 0) + 1
                                profile.total_duration_seconds = (
                                    (profile.total_duration_seconds or 0) + (sess.duration_seconds or 0)
                                )
                                await db.commit()

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

            elif msg_type == "session_metrics":
                session_id = data.get("session_id")
                if session_id:
                    sess = await db.get(AgentSession, session_id)
                    if sess:
                        metrics = data.get("data", {})
                        sess.pages_visited  = metrics.get("pages_visited", sess.pages_visited or 0)
                        sess.total_data_mb  = metrics.get("total_data_mb", sess.total_data_mb or 0.0)
                        sess.browser_health = metrics.get("browser_health", 100.0)
                        sess.memory_mb      = metrics.get("memory_mb", 0.0)
                        if metrics.get("current_url"):
                            sess.last_url = metrics["current_url"]
                        await db.commit()
            elif msg_type == "page_visit":

                session_id = data.get("session_id")
                url        = data.get("url")
                title      = data.get("title", "")
                if session_id and url:
                    sess = await db.get(AgentSession, session_id)
                    if sess:
                        sess.last_url      = url
                        sess.pages_visited = (sess.pages_visited or 0) + 1

                        # ✅ Guardar en BrowserEvent (lo que lee el endpoint)
                        from app.models.agent_session import BrowserEvent
                        db.add(BrowserEvent(
                            session_id = session_id,
                            event_type = "page_visit",
                            url        = url,
                            details    = {"title": title},
                        ))
                        await db.commit()

                        # ✅ Broadcast en tiempo real al admin panel
                        await connection_manager.broadcast_to_admins({
                            "type":       "page_visit",
                            "session_id": session_id,
                            "url":        url,
                            "title":      title,
                            "timestamp":  datetime.utcnow().isoformat(),
                        })

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
            elif msg_type == "log":
                level   = data.get("level", "INFO")
                message = data.get("message", "")
                await connection_manager.add_agent_log(computer_id, level, message)

            elif msg_type == "proxy_check_result":
                request_id = data.get("request_id")
                if request_id:
                    connection_manager.resolve_proxy_check(request_id, {
                        "latency_ms": data.get("latency_ms"),
                        "error":      data.get("error"),
                    })
            elif msg_type == "heartbeat":
                await websocket.send_json({
                    "type":      "pong",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                })
                # Actualizar last_seen del computer
                if computer:
                    computer.last_seen_at = datetime.utcnow()
                    await db.commit()

            elif msg_type == "verify_profile_result":
                request_id = data.get("request_id")
                if request_id:
                    connection_manager.resolve_proxy_check(request_id, {
                        # ANTES solo tenía fingerprint_config y has_cookies
                        # AHORA pasa TODO lo que calcula el agente:
                        "browser_score":     data.get("browser_score", 0),
                        "fingerprint_score": data.get("fingerprint_score", 0),
                        "cookie_status":     data.get("cookie_status", "MISSING"),
                        "breakdown":         data.get("breakdown", {}),
                        "grade":             data.get("grade", "DÉBIL"),
                        "has_cookies":       data.get("has_cookies", False),
                        "error":             data.get("error"),
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


# La función crea su propia sesión:
async def _process_pending_profiles(computer_id: int):
    from app.database import AsyncSessionLocal
    from app.models.profile import Profile, ProfileStatus
    from app.models.proxy import Proxy
    from sqlalchemy.orm import selectinload
    import asyncio

    await asyncio.sleep(2)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Profile)
            .options(selectinload(Profile.proxy))
            .where(Profile.status == ProfileStatus.CREATING)
            .where(Profile.adspower_id.like("pending-%"))
        )
        pending = result.scalars().all()

        if not pending:
            logger.info(f"✅ No hay perfiles pendientes para agente #{computer_id}")
            return

        logger.info(f"📋 {len(pending)} perfiles pendientes — enviando a agente #{computer_id}")

        for profile in pending:

           
            # # # # #REVISAR LENGUAJE 
            fingerprint_config = {
                "ua":                  profile.user_agent or "",
                "os":                  profile.os or "Windows",
                "language":            ["es-ES", "es"] or profile.language,
                "resolution":          profile.screen_resolution or "1920x1080",
                "device_name":         profile.device_name or "",
                "platform":            profile.platform or "Win32",
                "hardware_concurrency": profile.hardware_concurrency or 4,
                "device_memory":       profile.device_memory or 8,
            }

            # Construir proxy config desde la relación
            proxy = profile.proxy
            user_proxy_config = {}
            if proxy:
                user_proxy_config = {
                    "proxy_soft":     "other",
                    "proxy_type":     "http",
                    "proxy_host":     proxy.host,
                    "proxy_port":     str(proxy.port),
                    "proxy_user":     proxy.username or "",
                    "proxy_password": proxy.password or "",
                }

            sent = await connection_manager.send_command_to_agent(
                computer_id=computer_id,
                command="create_adspower_profile",
                payload={
                    "profile_id":         profile.id,
                    "name":               profile.name,
                    "fingerprint_config": fingerprint_config,
                    "user_proxy_config":  user_proxy_config,
                    "remark":             profile.owner or "",
                }
            )
            if sent:
                logger.info(f"  ✅ Perfil {profile.id} ({profile.name}) encolado")
            else:
                logger.warning(f"  ⚠️ No se pudo enviar perfil {profile.id}")

            await asyncio.sleep(2)
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


class RegisterAgentRequest(BaseModel):
    name:             str
    hostname:         str
    ip_address:       Optional[str] = ""
    adspower_api_url: Optional[str] = ""
    adspower_api_key: Optional[str] = ""
    os_info:          Optional[str] = ""
    cpu_cores:        Optional[int] = None
    ram_gb:           Optional[int] = None

@router.post("/register")
async def register_agent(
    request: RegisterAgentRequest,
    token: str = Header(None, alias="X-Agent-Token"),
    db: AsyncSession = Depends(get_db),
):
    # Validar token
    if not token or token != settings.AGENT_SECRET_TOKEN:
        raise HTTPException(status_code=401, detail="Token inválido")

    # Verificar si ya existe por hostname
    result = await db.execute(
        select(Computer).where(Computer.hostname == request.hostname)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        existing.status           = ComputerStatus.ONLINE
        existing.last_seen_at     = datetime.utcnow()
        existing.adspower_api_url = request.adspower_api_url or existing.adspower_api_url
        existing.ip_address       = request.ip_address or existing.ip_address
        await db.commit()
        return {"computer_id": existing.id, "name": existing.name, "registered": False}

    computer = Computer(
        name=             request.name,
        hostname=         request.hostname,
        ip_address=       request.ip_address,
        adspower_api_url= request.adspower_api_url or "",
        adspower_api_key= request.adspower_api_key or "",
        os_info=          request.os_info,
        cpu_cores=        request.cpu_cores,
        ram_gb=           request.ram_gb,
        status=           ComputerStatus.ONLINE,
        last_seen_at=     datetime.utcnow(),
        is_active=        True,
    )
    db.add(computer)
    await db.commit()
    await db.refresh(computer)

    return {"computer_id": computer.id, "name": computer.name, "registered": True}

@router.get("/computers/{computer_id}/logs")
async def get_computer_logs(computer_id: int):
    return {"logs": connection_manager.get_agent_logs(computer_id)}

