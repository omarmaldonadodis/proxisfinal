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

import httpx



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
        computer.status = ComputerStatus.ONLINE
        computer.last_seen_at = datetime.utcnow()
        await db.commit()
        asyncio.create_task(_process_pending_profiles(computer_id))

        # ── Enviar eliminaciones de AdsPower pendientes ──────────────────
        pending_deletes = connection_manager.get_pending_adspower_deletes()
        if pending_deletes:
            logger.info(
                f"📋 {len(pending_deletes)} eliminaciones AdsPower pendientes "
                f"→ agente #{computer_id}"
            )
            for item in pending_deletes:
                sent = await connection_manager.send_command_to_agent(
                    computer_id=computer_id,
                    command="delete_adspower_profile",
                    payload={
                        "adspower_id": item["adspower_id"],
                        "profile_id":  item["profile_id"],
                    },
                )
                if sent:
                    logger.info(
                        f"  ✅ Comando delete enviado: {item['adspower_id']}")

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
                        
                        # Enriquecer con nombre del perfil
                        profile_name = None
                        agent_name_val = sess.agent_name or "agent"
                        if sess.profile_id:
                            from app.models.profile import Profile
                            prof = await db.get(Profile, sess.profile_id)
                            if prof:
                                profile_name = prof.name

                        await connection_manager.broadcast_to_admins({
                            "type":        "session_active",
                            "session_id":  session_id,
                            "computer_id": computer_id,
                            "profile_id":  sess.profile_id,
                            "profile":     profile_name,          # ← nombre del perfil
                            "agent_name":  agent_name_val,        # ← nombre del agente
                            "target_url":  sess.target_url,
                            "timestamp":   datetime.utcnow().isoformat(),
                        })

            elif msg_type == "session_closed":
                session_id = data.get("session_id")
                if session_id:
                    from app.models.profile import Profile
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
                        
                        profile_name = None
                        if sess.profile_id:
                            prof = await db.get(Profile, sess.profile_id)
                            profile_name = prof.name if prof else f"Perfil #{sess.profile_id}"

                        await connection_manager.broadcast_to_admins({
                            "type":             "session_closed",
                            "session_id":       session_id,
                            "computer_id":      computer_id,
                            "profile_id":       sess.profile_id,
                            "profile_name":     profile_name,
                            "duration_seconds": sess.duration_seconds,
                            "total_data_mb":    sess.total_data_mb,
                            "agent_name":       "agent",
                            "timestamp":        datetime.utcnow().isoformat(),
                        })
                        
                        # ← AGREGAR: si el perfil tuvo sesión real, marcar cookies como OK
                        if sess.profile_id and sess.pages_visited and sess.pages_visited > 0:
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
                name = data.get("name")
                logger.info(f"[profile_created] {data}")
                if profile_id and adspower_id:
                    from app.services.profile_service import ProfileService
                    svc = ProfileService(db)
                    await svc.set_adspower_id(profile_id, adspower_id)

                    await connection_manager.broadcast_to_admins({
                        "type":        "profile_ready",
                        "name": name,
                        "profile_id":  profile_id,
                        "adspower_id": adspower_id,
                        "computer_id": computer_id,
                        "timestamp":   datetime.utcnow().isoformat(),
                    })

            elif msg_type == "profile_create_error":
                profile_id = data.get("profile_id")
                name = data.get("name")
                error_msg = data.get("error", "Error desconocido al crear perfil")

                if profile_id:
                    # Marcar perfil como ERROR en BD (no quedarse en CREATING)
                    from app.models.profile import Profile, ProfileStatus
                    profile = await db.get(Profile, profile_id)
                    if profile:
                        profile.status = ProfileStatus.ERROR
                        profile.last_action = "CREATE_FAILED"
                        await db.commit()

                    # Crear alerta visible en el timeline
                    from app.models.alert import Alert, AlertSeverity, AlertStatus
                    alert = Alert(
                        title=f"Error al crear perfil {name}",
                        message=error_msg,
                        severity=AlertSeverity.ERROR.value,
                        status=AlertStatus.ACTIVE.value,
                        source="profile_creator",
                        source_id=profile_id,
                    )
                    db.add(alert)
                    await db.commit()

                    # Broadcast al panel admin
                    await connection_manager.broadcast_to_admins({
                        "type":       "profile_create_error",
                        "profile_id": profile_id,
                        "name":       name,
                        "error":      error_msg,
                        "timestamp":  datetime.utcnow().isoformat(),
                    })
                    logger.error(f"❌ Perfil {profile_id} falló: {error_msg}")
        
            elif msg_type == "profile_delete_result":
                adspower_id = data.get("adspower_id")
                status = data.get("status")  # "deleted" o "already_gone"

                if adspower_id:
                    # Limpiar de la cola en ambos casos — ya no hace falta reintentarlo
                    connection_manager.clear_adspower_delete(adspower_id)
                    logger.info(
                        f"✅ Delete de AdsPower resuelto ({status}): {adspower_id} — "
                        f"eliminado de la cola pendiente"
                    )

                await connection_manager.broadcast_to_admins({
                    "type":        "profile_delete_result",
                    "adspower_id": adspower_id,
                    "status":      status,
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
                error_msg = data.get("error", "")
                if session_id:
                    sess = await db.get(AgentSession, session_id)
                    if sess:
                        sess.status = SessionStatus.CRASHED
                        sess.error_detail = error_msg
                        sess.closed_at = datetime.utcnow()
                        await db.commit()

                        profile_name = None
                        if sess.profile_id:
                            prof = await db.get(Profile, sess.profile_id)
                            profile_name = prof.name if prof else f"Perfil #{sess.profile_id}"

                        # Clasificar el error (limpio, sin traza Python)
                        is_proxy_error = any(kw in error_msg for kw in [
                            "Proxy inválido", "Check Proxy", "PROXY_INVALID",
                            "proxy", "Check", "Proxy caído",
                        ])

                        # Mensaje amigable (sin [_main_:xxx:yyy])
                        if is_proxy_error:
                            friendly_msg = f"Proxy caído o inválido — ejecuta rotación de proxies"
                        elif "AdsPower no disponible" in error_msg or "ADSPOWER_OFFLINE" in error_msg:
                            friendly_msg = "AdsPower no disponible — verifica que la app esté abierta"
                        elif "Timeout" in error_msg or "TIMEOUT" in error_msg:
                            friendly_msg = "Timeout al abrir navegador — AdsPower tardó demasiado"
                        elif "not exist" in error_msg.lower():
                            friendly_msg = "Perfil no encontrado en AdsPower — puede haber sido eliminado"
                        else:
                            friendly_msg = error_msg

                        # Crear alerta en BD ANTES del broadcast
                        crash_alert_id = None
                        if is_proxy_error and sess.profile_id:
                            from app.models.alert import Alert, AlertSeverity, AlertStatus
                            crash_alert = Alert(
                                title=f"Proxy inválido o caído — {profile_name or f'Perfil #{sess.profile_id}'}",
                                message=f"Sesión #{session_id} crasheó: {friendly_msg}. Auto-rotación iniciando...",
                                severity=AlertSeverity.ERROR.value,
                                status=AlertStatus.ACTIVE.value,
                                source="proxy_crash",
                                source_id=sess.profile_id,
                            )
                            db.add(crash_alert)
                            await db.commit()
                            await db.refresh(crash_alert)
                            crash_alert_id = crash_alert.id

                        await connection_manager.broadcast_to_admins({
                            "type":           "session_crashed",
                            "session_id":     session_id,
                            "computer_id":    computer_id,
                            "profile_id":     sess.profile_id,
                            "profile_name":   profile_name,
                            "error":          friendly_msg,      # ← limpio
                            "crash_reason":   friendly_msg,
                            "is_proxy_error": is_proxy_error,
                            "crash_alert_id": crash_alert_id,
                            "timestamp":      datetime.utcnow().isoformat(),
                        })

                        if is_proxy_error and sess.profile_id:
                            asyncio.create_task(_rotate_proxy_runtime(sess.profile_id))
        
            elif msg_type == "log":
                level   = data.get("level", "INFO")
                message = data.get("message", "")
                await connection_manager.add_agent_log(computer_id, level, message)
                
            elif msg_type == "proxy_rotation_queued":
                # El agente encoló una rotación porque AdsPower estaba cerrado
                proxy_id = data.get("proxy_id")
                queued = data.get("queued", 0)
                reason = data.get("reason", "AdsPower no disponible")

                connection_manager.set_pending_rotation(computer_id, True)

                await connection_manager.broadcast_to_admins({
                    "type":        "system_event",
                    "event":       "proxy_rotation_queued",
                    "message":     f"⏸️ Rotación encolada — {reason} ({queued} pendiente/s)",
                    "source":      f"Computer #{computer_id}",
                    "computer_id": computer_id,
                    "timestamp":   datetime.utcnow().isoformat(),
                })
                logger.info(
                    f"📋 Rotación encolada en Computer #{computer_id}: {queued} pendientes")

            elif msg_type == "proxy_update_result":
                # Resultado de un update_proxy (éxito o fallo)
                proxy_id = data.get("proxy_id")
                success_count = data.get("success_count", 0)
                failed_count = data.get("failed_count", 0)

                await connection_manager.broadcast_to_admins({
                    "type":          "proxy_update_result",
                    "computer_id":   computer_id,
                    "proxy_id":      proxy_id,
                    "success_count": success_count,
                    "failed_count":  failed_count,
                    "timestamp":     datetime.utcnow().isoformat(),
                })
    
            elif msg_type == "adspower_status":
                status = data.get("status")
                is_available = status in ("available", "online", True)

                # Guardar estado ANTERIOR antes de actualizar
                was_available = connection_manager.is_adspower_ready(computer_id)
                connection_manager.set_adspower_status(computer_id, is_available)

                # ── Solo disparar cola si es una TRANSICIÓN offline → online ─────────
                # Cubre dos casos:
                # 1. Agente conecta y AdsPower ya está abierto (was_available=False por defecto)
                # 2. AdsPower estaba cerrado y el usuario lo abrió
                if is_available and not was_available:
                    asyncio.create_task(_process_pending_profiles(computer_id))
                    logger.info(
                        f"🟢 AdsPower de Computer #{computer_id} disponible — "
                        f"el agente procesará la cola de perfiles pendientes"
                    )
                # ─────────────────────────────────────────────────────────────────────

                if is_available and connection_manager.has_pending_rotation(computer_id):
                    connection_manager.clear_pending_rotation(computer_id)
                    logger.info(
                        f"🟢 AdsPower de Computer #{computer_id} disponible — "
                        f"el agente procesará la cola de rotaciones pendientes"
                    )

                await connection_manager.broadcast_to_admins({
                    "type":        "adspower_status",
                    "status":      status,
                    "computer_id": computer_id,
                    "message":     data.get("message"),
                    "timestamp":   datetime.utcnow().isoformat(),
                })
            
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
            elif msg_type == "agent_connected":
                """
                El agente envía su lista de sesiones realmente activas al reconectarse.
                Cerramos en la BD todas las sesiones de esta computadora que NO estén
                en esa lista (quedaron abiertas del crash/restart anterior).
                """
                from app.models.agent_session import AgentSession, SessionStatus

                reported_active_ids: list[int] = data.get("active_session_ids", [])

                # Buscar sesiones que el backend cree que siguen abiertas
                result = await db.execute(
                    select(AgentSession).where(
                        AgentSession.computer_id == computer_id,
                        AgentSession.status.in_([
                            SessionStatus.ACTIVE.value,
                            SessionStatus.OPENING.value,
                        ])
                    )
                )
                open_sessions = result.scalars().all()

                zombie_count = 0
                for sess in open_sessions:
                    if sess.id not in reported_active_ids:
                        sess.status = SessionStatus.CLOSED.value
                        sess.closed_at = datetime.utcnow()
                        sess.error_detail = "Cerrada por reconexión del agente (sesión zombie)"
                        zombie_count += 1

                if zombie_count > 0:
                    await db.commit()
                    logger.info(
                        f"🧹 Agente #{computer_id} reconectó — "
                        f"{zombie_count} sesión(es) zombie cerradas, "
                        f"{len(reported_active_ids)} sesión(es) activas conservadas"
                    )
                    await connection_manager.broadcast_to_admins({
                        "type":        "system_event",
                        "event":       "zombie_sessions_cleaned",
                        "computer_id": computer_id,
                        "message":     (
                            f"🧹 {zombie_count} sesión(es) zombie cerradas en "
                            f"{computer.name if computer else f'Computer #{computer_id}'}"
                        ),
                        "timestamp":   datetime.utcnow().isoformat(),
                    })
                else:
                    logger.info(
                        f"✅ Agente #{computer_id} reconectó — sin sesiones zombie"
                    )

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
            "name":        computer.name,
            "computer_id": computer_id,
            "timestamp":   datetime.utcnow().isoformat(),
        })


async def _rotate_proxy_runtime(profile_id: int):
    from app.database import AsyncSessionLocal
    from app.models.profile import Profile
    from app.config import settings

    async with AsyncSessionLocal() as db:
        profile = await db.get(Profile, profile_id)

        if not profile or not profile.proxy_id:
            logger.warning(f"⚠️ No proxy_id para profile {profile_id}")
            return

        proxy_id = profile.proxy_id

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"{settings.API_INTERNAL_URL}/api/v1/proxy-rotation/{proxy_id}/check-and-rotate"
            )

            if r.status_code == 200:
                logger.info(f"🔄 Proxy rotado correctamente: {proxy_id}")
            else:
                logger.error(f"❌ Error rotando proxy {proxy_id}: {r.text}")

    except Exception as e:
        logger.error(f"❌ Error llamando rotación proxy: {e}")

# La función crea su propia sesión:


async def _process_pending_profiles(computer_id: int):
    from app.database import AsyncSessionLocal
    from app.models.profile import Profile, ProfileStatus
    from app.models.proxy import Proxy
    from sqlalchemy.orm import selectinload
    import asyncio

    # ── Guard: solo una ejecución por computadora a la vez ───────────────────
    if computer_id in connection_manager._processing_profiles:
        logger.info(
            f"⏭️ _process_pending_profiles ya corriendo para #{computer_id}, skip")
        return
    connection_manager._processing_profiles.add(computer_id)
    # ─────────────────────────────────────────────────────────────────────────

    try:
        """Espera 2s y verifica AdsPower antes de enviar perfiles pendientes."""
        await asyncio.sleep(2)

        # Verificar si el agente reportó AdsPower como disponible
        adspower_ok = connection_manager.is_adspower_ready(computer_id)
        if not adspower_ok:
            logger.warning(
                f"⏸️ Computer #{computer_id} conectado pero AdsPower NO está disponible. "
                f"Perfiles pendientes quedarán en cola hasta que AdsPower se abra."
            )
            await connection_manager.broadcast_to_admins({
                "type":        "adspower_not_ready_on_connect",
                "computer_id": computer_id,
                "message":     f"Computer #{computer_id} conectado — esperando que AdsPower se abra para procesar cola",
                "timestamp":   datetime.utcnow().isoformat(),
            })
            return  # No procesar cola todavía

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Profile)
                .options(selectinload(Profile.proxy))
                .where(Profile.status == ProfileStatus.CREATING)
                .where(Profile.adspower_id.like("pending-%"))
            )
            pending = result.scalars().all()

            if not pending:
                logger.info(
                    f"✅ No hay perfiles pendientes para agente #{computer_id}")
                return

            logger.info(
                f"📋 {len(pending)} perfiles pendientes — enviando a agente #{computer_id}")

            def _clamp_val(value, valid_list):
                return min(valid_list, key=lambda x: abs(x - (value or valid_list[0])))

            for profile in pending:
                fingerprint_config = {
                    "ua":                   profile.user_agent or "",
                    "os":                   profile.os or "Windows",
                    "language":             ["es-ES", "es"] or profile.language,
                    "resolution":           profile.screen_resolution or "1920x1080",
                    "device_name":          profile.device_name or "",
                    "platform":             profile.platform or "Win32",
                    "hardware_concurrency": _clamp_val(profile.hardware_concurrency, [2, 3, 4, 6, 8, 10, 12, 16, 20, 24, 32, 64]),
                    "device_memory":        _clamp_val(profile.device_memory, [2, 4, 6, 8, 16, 32, 64, 128]),
                }

                proxy = profile.proxy
                user_proxy_config = {}
                if proxy:
                    user_proxy_config = {
                        "proxy_soft":     "other",
                        "proxy_type":     "http",
                        "proxy_host":     settings.SOAX_HOST,
                        "proxy_port":     str(settings.SOAX_PORT),
                        "proxy_user":     proxy.username or "",
                        "proxy_password": settings.SOAX_PASSWORD,
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
                    logger.info(
                        f"  ✅ Perfil {profile.id} ({profile.name}) encolado")
                else:
                    logger.warning(
                        f"  ⚠️ No se pudo enviar perfil {profile.id}")

                await asyncio.sleep(2)

    finally:
        # Siempre liberar el guard, incluso si hubo excepción
        connection_manager._processing_profiles.discard(computer_id)
        
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

    # ── Enviar eliminaciones pendientes al agente que acaba de hacer checkin ──
    pending_deletes = connection_manager.get_pending_adspower_deletes()
    if pending_deletes:
        logger.info(
            f"📋 Enviando {len(pending_deletes)} eliminaciones pendientes "
            f"al agente #{computer_id}"
        )
        for item in pending_deletes:
            await connection_manager.send_command_to_agent(
                computer_id=computer_id,
                command="delete_adspower_profile",
                payload={
                    "adspower_id": item["adspower_id"],
                    "profile_id":  item["profile_id"],
                },
            )
            await asyncio.sleep(0.5)

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


@router.post("/broadcast-check-adspower")
async def broadcast_check_adspower():
    """
    Pide a todos los agentes online que reporten
    el estado de AdsPower de forma inmediata.
    """
    online = connection_manager.get_online_agents()
    results = {}
    for cid in online:
        sent = await connection_manager.send_command_to_agent(
            computer_id=cid,
            command="check_adspower_now",
            payload={"computer_id": cid},
        )
        results[str(cid)] = sent
    return {"agents_notified": results, "total": len(online)}

# ══════════════════════════════════════════════════════════════════════════════
# ABRIR NAVEGADOR CON PERFIL (desde el panel admin)
# Cualquier computadora puede abrir cualquier perfil
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/open-browser/direct")
async def open_browser_direct(
    profile_adspower_id: str = Query(..., description="adspower_id del perfil"),
    computer_id:         int = Query(..., description="ID de la computadora que abrirá el navegador"),
    target_url:          str = Query("https://www.facebook.com"),
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

    # Verificar si hay sesión activa
    existing = await db.execute(
        select(AgentSession).where(
            AgentSession.profile_id == profile.id,
            AgentSession.status.in_([SessionStatus.ACTIVE, SessionStatus.OPENING]),
        )
    )
    active_session = existing.scalar_one_or_none()
    
    # Si ya hay una sesión activa, pero en OTRA computadora, denegar (AdsPower no permite concurrencia entre máquinas)
    if active_session and active_session.computer_id != computer_id:
        raise HTTPException(
            status_code=409,
            detail=f"El perfil ya está activo en la computadora #{active_session.computer_id}. Ciérralo allí primero.",
        )
    
    # Si ya hay una sesión activa en la MISMA computadora, el agente lo manejará como una nueva pestaña
    is_new_tab = active_session is not None

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
            "proxy_id":    profile.proxy_id,
            "is_new_tab":  is_new_tab,
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

