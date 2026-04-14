# app/api/v1/proxy_rotation.py - ✅ VERSIÓN CORREGIDA SIN BACKGROUNDTASKS

import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.proxy_rotation_service import ProxyRotationService
from loguru import logger
from sqlalchemy import select
import asyncio


router = APIRouter(prefix="/proxy-rotation", tags=["Proxy Rotation"])


@router.post("/{proxy_id}/check-and-rotate")
async def check_and_rotate_proxy(
    proxy_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Verifica y rota proxy si es necesario
    """
    
    try:
        service = ProxyRotationService(db)
        result = await service.check_and_rotate_proxy(proxy_id)
        
        if result.get("error"):
            logger.error(f"Error rotando proxy {proxy_id}: {result['error']}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": result["error"],
                    "proxy_id": proxy_id,
                    "old_latency_ms": result.get("old_latency_ms")
                }
            )
        
        return result
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Unexpected error checking proxy {proxy_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error inesperado: {str(e)}"
        )


@router.post("/check-and-rotate-all")
async def check_and_rotate_all():
    asyncio.create_task(_queued_check_all())
    return {"message": "Verificación encolada — se ejecutará cuando haya un agente disponible", "status": "queued"}


async def _queued_check_all():
    """
    Espera hasta que haya un agente online con AdsPower disponible.
    Si el agente está online pero AdsPower cerrado → notifica y espera.
    """
    from app.core.connection_manager import connection_manager
    max_wait_seconds = 600  # 10 minutos
    waited = 0
    notified_no_agent = False
    notified_no_adspower = False

    while waited < max_wait_seconds:
        online_agents = connection_manager.get_online_agents()

        if not online_agents:
            if not notified_no_agent:
                logger.warning("⏳ Esperando agente online para rotación...")
                await connection_manager.broadcast_to_admins({
                    "type":    "system_event",
                    "event":   "proxy_rotation_waiting",
                    "message": "⏸️ Rotación en espera — no hay agentes conectados",
                    "source":  "proxy_rotation",
                })
                notified_no_agent = True
            await asyncio.sleep(15)
            waited += 15
            continue

        notified_no_agent = False

        # Verificar que al menos un agente tenga AdsPower disponible
        ready_agents = [
            cid for cid in online_agents
            if connection_manager.is_adspower_ready(cid)
        ]

        if not ready_agents:
            if not notified_no_adspower:
                agent_names = list(online_agents)
                logger.warning(
                    f"⏳ Agente(s) {agent_names} conectados pero AdsPower no disponible"
                )
                await connection_manager.broadcast_to_admins({
                    "type":    "system_event",
                    "event":   "proxy_rotation_waiting_adspower",
                    "message": (
                        f"⏸️ Rotación encolada — agente conectado pero AdsPower no está abierto. "
                        f"Abre AdsPower para continuar."
                    ),
                    "source":  "proxy_rotation",
                })
                # Marcar en connection_manager que hay rotación pendiente
                for cid in online_agents:
                    connection_manager.set_pending_rotation(cid, True)
                notified_no_adspower = True
            await asyncio.sleep(10)
            waited += 10
            continue

        # ✅ Hay agente online con AdsPower disponible
        notified_no_adspower = False
        for cid in ready_agents:
            connection_manager.clear_pending_rotation(cid)

        logger.info(
            f"✅ Agente {list(ready_agents)[0]} disponible con AdsPower — "
            f"iniciando rotación de proxies"
        )
        await _background_check_all()
        return

    logger.warning(
        "⚠️ Timeout esperando agente + AdsPower — rotación cancelada")
    await connection_manager.broadcast_to_admins({
        "type":    "system_event",
        "event":   "proxy_rotation_timeout",
        "message": "❌ Rotación cancelada — timeout sin agente+AdsPower disponible (10 min)",
        "source":  "proxy_rotation",
    })


async def _background_check_all():
    from app.database import AsyncSessionLocal
    from app.models.proxy import Proxy, ProxyStatus
    from app.models.alert import Alert, AlertSeverity, AlertStatus
    from app.core.connection_manager import connection_manager
    from app.config import settings
    from datetime import datetime
    import secrets
    import json
    from sqlalchemy import select, or_

    async with AsyncSessionLocal() as db:
        online_agents = connection_manager.get_online_agents()
        if not online_agents:
            logger.warning("No hay agentes online para verificar proxies")
            return

        computer_id = next(iter(online_agents))

        result = await db.execute(
            select(Proxy).where(
                or_(Proxy.status == ProxyStatus.ACTIVE,
                    Proxy.status == ProxyStatus.FAILED)
            )
        )
        proxies = result.scalars().all()
        logger.info(
            f"Verificando {len(proxies)} proxies via agente #{computer_id}")

        stats = {"total": len(proxies), "optimal": 0,
                 "rotated": 0, "failed": 0}

        for proxy in proxies:
            city = None
            latency = None

            # Sincronizar password desde .env
            if proxy.password != settings.SOAX_PASSWORD:
                proxy.password = settings.SOAX_PASSWORD
                await db.commit()

            try:
                check = await connection_manager.request_proxy_check(
                    computer_id=computer_id,
                    proxy_id=proxy.id,
                    proxy_host=proxy.host,
                    proxy_port=int(proxy.port),
                    proxy_user=proxy.username or "",
                    proxy_password=settings.SOAX_PASSWORD,
                    timeout=15.0,
                )

                # ── Actualizar contadores en BD (siempre) ──────────────────────
                proxy.total_checks = (proxy.total_checks or 0) + 1
                proxy.last_check_at = datetime.utcnow()

                if check is None:
                    # TIMEOUT
                    proxy.failed_checks = (proxy.failed_checks or 0) + 1
                    proxy.success_rate = round(
                        (proxy.total_checks - proxy.failed_checks) /
                        proxy.total_checks * 100, 2
                    )
                    logger.warning(
                        f"Proxy {proxy.id}: timeout esperando respuesta del agente")
                    stats["failed"] += 1
                    from app.models.proxy_rotation_log import ProxyRotationLog, RotationTrigger
                    db.add(ProxyRotationLog(
                        proxy_id=proxy.id,
                        computer_id=computer_id,
                        old_proxy_display=f"{proxy.host}:{proxy.port} ({proxy.city or 'unknown'})",
                        trigger=RotationTrigger.SCHEDULED,
                        success=False,
                        error_message="Timeout — agente sin respuesta",
                    ))
                    await db.commit()
                    continue

                latency = check.get("latency_ms")

                if latency is not None and latency < 2000:
                    # ── PROXY ÓPTIMO ───────────────────────────────────────────
                    proxy.avg_response_time = latency
                    proxy.status = ProxyStatus.ACTIVE
                    proxy.last_success_at = datetime.utcnow()
                    # success_rate real
                    successful = proxy.total_checks - \
                        (proxy.failed_checks or 0)
                    proxy.success_rate = round(
                        successful / proxy.total_checks * 100, 2)
                    await db.commit()
                    stats["optimal"] += 1
                    logger.info(
                        f"Proxy {proxy.id} OK ({latency}ms) — éxito: {proxy.success_rate:.0f}%")
                    await connection_manager.broadcast_to_admins({
                        "type":         "rotation_progress",
                        "proxy_id":     proxy.id,
                        "result":       "ok",
                        "latency_ms":   latency,
                        "success_rate": proxy.success_rate,
                        "stats":        dict(stats),
                        "detail":       f"#{proxy.id} {proxy.host} — {latency}ms ✓ estable ({proxy.success_rate:.0f}%)",
                    })
                    continue

                # ── PROXY LENTO U OFFLINE → ROTAR ─────────────────────────────
                proxy.failed_checks = (proxy.failed_checks or 0) + 1
                proxy.success_rate = round(
                    (proxy.total_checks - proxy.failed_checks) /
                    proxy.total_checks * 100, 2
                )
                reason = "offline" if latency is None else f"latencia {latency}ms"
                logger.warning(
                    f"Proxy {proxy.id} necesita rotación: {reason} — éxito: {proxy.success_rate:.0f}%")

                old_session = proxy.session_id or "—"

                from app.utils.soax_cities_manager import get_soax_username_with_dynamic_city
                soax_result = await get_soax_username_with_dynamic_city(
                    base_username=settings.SOAX_USERNAME,
                    country=(proxy.country or "ec").lower(),
                    preferred_city=None,
                    exclude_cities=[proxy.city.lower()] if proxy.city else [],
                    session_lifetime="3600" +"-opt-lookalike" 
                )
                new_user = soax_result.get("username")
                if not new_user:
                    raise ValueError(
                        f"SOAX no devolvió username válido para proxy {proxy.id}")

                city = soax_result.get(
                    "selected_city") or proxy.city or "unknown"

                import re
                raw = soax_result.get("username", "")
                # match = re.search(r'sessionid-(.+?)(?:-sessionlength|$)', raw)
                match = re.search(r'sessionid-([a-zA-Z0-9]+)(?:-sessionlength|$)', raw)
                import secrets as _secrets
                session_id = match.group(1) if match else _secrets.token_hex(8)  # ← era token_urlsafe(8)

                from app.models.profile import Profile
                profiles_r = await db.execute(
                    select(Profile).where(Profile.proxy_id == proxy.id)
                )
                profiles_list = profiles_r.scalars().all()
                adspower_ids = [
                    p.adspower_id for p in profiles_list
                    if p.adspower_id and not p.adspower_id.startswith("pending")
                ]

                sent = await connection_manager.send_command_to_agent(
                    computer_id=computer_id,
                    command="update_proxy",
                    payload={
                        "proxy_id":       proxy.id,
                        "profile_ids":    adspower_ids,
                        "proxy_host":     settings.SOAX_HOST,
                        "proxy_port":     settings.SOAX_PORT,
                        "proxy_user":     new_user,
                        "proxy_password": settings.SOAX_PASSWORD,
                    }
                )

                if sent:
                    proxy.username = new_user
                    proxy.session_id = session_id
                    proxy.password = settings.SOAX_PASSWORD
                    proxy.host = settings.SOAX_HOST
                    proxy.port = settings.SOAX_PORT
                    proxy.status = ProxyStatus.ACTIVE
                    proxy.last_success_at = datetime.utcnow()

                    from app.models.proxy_rotation_log import ProxyRotationLog, RotationTrigger
                    db.add(ProxyRotationLog(
                        proxy_id=proxy.id,
                        computer_id=computer_id,
                        old_proxy_display=f"{proxy.host}:{proxy.port} ({proxy.city or 'unknown'}) sesión:{old_session[:8]}",
                        new_proxy_display=f"{proxy.host}:{proxy.port} ({city}) sesión:{session_id[:8]}",
                        trigger=RotationTrigger.SCHEDULED,
                        success=True,
                        latency_ms=latency,
                    ))

                    await db.commit()
                    stats["rotated"] += 1
                    logger.info(f"Proxy {proxy.id} rotado → {city}")
                    await connection_manager.broadcast_to_admins({
                        "type":         "rotation_progress",
                        "proxy_id":     proxy.id,
                        "result":       "rotated",
                        "success_rate": proxy.success_rate,
                        "stats":        dict(stats),
                        "detail":       f"#{proxy.id} {proxy.host} → nueva sesión {city} ({len(adspower_ids)} perfiles)",
                    })
                else:
                    stats["failed"] += 1
                    from app.models.proxy_rotation_log import ProxyRotationLog, RotationTrigger
                    db.add(ProxyRotationLog(
                        proxy_id=proxy.id,
                        computer_id=computer_id,
                        old_proxy_display=f"{proxy.host}:{proxy.port} ({proxy.city or 'unknown'})",
                        trigger=RotationTrigger.SCHEDULED,
                        success=False,
                        error_message="update_proxy falló — AdsPower no alcanzable",
                        latency_ms=latency,
                    ))
                    await db.commit()
                    await connection_manager.broadcast_to_admins({
                        "type":     "rotation_progress",
                        "proxy_id": proxy.id,
                        "result":   "failed",
                        "stats":    dict(stats),
                        "detail":   f"#{proxy.id} {proxy.host} ✗ AdsPower sin respuesta",
                    })

            except Exception as e:
                logger.error(f"Error procesando proxy {proxy.id}: {e}")
                stats["failed"] += 1
                # Registrar fallo en contadores
                try:
                    proxy.total_checks = (proxy.total_checks or 0) + 1
                    proxy.failed_checks = (proxy.failed_checks or 0) + 1
                    proxy.last_check_at = datetime.utcnow()
                    if proxy.total_checks > 0:
                        proxy.success_rate = round(
                            (proxy.total_checks - proxy.failed_checks) /
                            proxy.total_checks * 100, 2
                        )
                    from app.models.proxy_rotation_log import ProxyRotationLog, RotationTrigger
                    db.add(ProxyRotationLog(
                        proxy_id=proxy.id,
                        computer_id=computer_id,
                        old_proxy_display=f"{proxy.host}:{proxy.port} ({proxy.city or 'unknown'})",
                        trigger=RotationTrigger.SCHEDULED,
                        success=False,
                        error_message=str(e),
                        latency_ms=latency,
                    ))
                    await db.commit()
                except Exception:
                    pass

        # ── Resumen final ──────────────────────────────────────────────────────
        from sqlalchemy import update as sql_update
        await db.execute(
            sql_update(Alert)
            .where(Alert.source == "proxy_rotation")
            .where(Alert.status == AlertStatus.ACTIVE.value)
            .values(status=AlertStatus.RESOLVED.value)
        )
        await db.commit()

        is_failure = stats["failed"] > 0
        new_alert = Alert(
            title="Rotación automática de proxies",
            message=(
                f"Total: {stats['total']} | "
                f"Óptimos: {stats['optimal']} | "
                f"Rotados: {stats['rotated']} | "
                f"Fallidos: {stats['failed']}"
            ),
            severity=AlertSeverity.ERROR.value if is_failure else AlertSeverity.INFO.value,
            status=AlertStatus.ACTIVE.value if is_failure else AlertStatus.RESOLVED.value,
            source="proxy_rotation",
        )
        db.add(new_alert)
        await db.commit()

        try:
            await connection_manager.broadcast_to_admins({
                "type":    "system_event",
                "event":   "proxy_rotation_complete",
                "message": f"Rotación completada — {stats['rotated']} rotados, {stats['optimal']} óptimos",
                "source":  "proxy_rotation",
                "stats":   stats,
            })
        except Exception as e:
            logger.warning(f"No se pudo broadcast proxy rotation: {e}")

        logger.info(f"Rotación completa: {stats}")



@router.get("/{proxy_id}/history")
async def get_proxy_rotation_history(
    proxy_id: int,
    db: AsyncSession = Depends(get_db)
):
    from app.models.proxy_rotation_log import ProxyRotationLog

    result = await db.execute(
        select(ProxyRotationLog)
        .where(ProxyRotationLog.proxy_id == proxy_id)
        .order_by(ProxyRotationLog.created_at.desc())
        .limit(50)
    )
    logs = result.scalars().all()
    return {
        "items": [
            {
                "id":               l.id,
                "old_proxy":        l.old_proxy_display,
                "new_proxy":        l.new_proxy_display,
                "success":          l.success,
                "error_message":    l.error_message,
                "latency_ms":       l.latency_ms,
                "trigger":          l.trigger,
                "rotated_at":       l.created_at.isoformat(),
            }
            for l in logs
        ]
    }  # ← esta línea ya existe, no duplicar


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select, func
    from app.models.proxy import Proxy, ProxyStatus
    from app.models.proxy_rotation_log import ProxyRotationLog
    from datetime import datetime, timedelta

    try:
        result = await db.execute(
            select(
                func.count(Proxy.id).label("total"),
                func.count(Proxy.id).filter(Proxy.status ==
                                            ProxyStatus.ACTIVE).label("active"),
                func.count(Proxy.id).filter(Proxy.status ==
                                            ProxyStatus.FAILED).label("failed"),
                func.avg(Proxy.avg_response_time).label("avg_latency"),
            )
        )
        row = result.one()

        # ── Success rate: solo checks de los últimos 7 días ──────────────
        # Evita que checks históricos fallidos arrastren el % hacia abajo
        since = datetime.utcnow() - timedelta(days=7)
        recent = await db.execute(
            select(
                func.count(ProxyRotationLog.id).label("total"),
                func.count(ProxyRotationLog.id).filter(
                    ProxyRotationLog.success == True
                ).label("success"),
            ).where(ProxyRotationLog.created_at >= since)
        )
        rrow = recent.one()

        if rrow.total and rrow.total > 0:
            avg_success_rate = round(rrow.success / rrow.total * 100, 2)
        elif row.active and row.total and row.total > 0:
            # Fallback: ratio activos/total si no hay logs recientes
            avg_success_rate = round(row.active / row.total * 100, 2)
        else:
            avg_success_rate = 100.0

        return {
            "total":            row.total or 0,
            "active":           row.active or 0,
            "failed":           row.failed or 0,
            "avg_latency_ms":   round(float(row.avg_latency or 0), 2),
            "avg_success_rate": avg_success_rate,
            "total_checks":     rrow.total or 0,
        }

    except Exception as e:
        logger.error(f"Error obteniendo stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync-all")
async def sync_all_to_adspower():
    """
    🔄 FORZAR sincronización de TODOS los proxies a AdsPower, sirve para pasar de la BD al adspower 
    
    """
    
    # ✅ Crear tarea en background
    asyncio.create_task(_background_sync_all())
    
    return {
        "message": "Sincronización iniciada en background",
        "status": "processing"
    }


async def _background_sync_all():
    """
    ✅ Sincroniza todos los proxies con AdsPower en background
    """
    from app.database import AsyncSessionLocal
    from app.models.proxy import Proxy, ProxyStatus
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Proxy).where(Proxy.status == ProxyStatus.ACTIVE)
        )
        proxies = list(result.scalars().all())
        
        logger.info(f"🔄 Sincronizando {len(proxies)} proxies a AdsPower...")
        
        service = ProxyRotationService(db)
        
        synced = 0
        failed = 0
        
        for proxy in proxies:
            try:
                success = await service._update_adspower_profiles_centralized(proxy)
                
                if success:
                    synced += 1
                    logger.info(f"✅ Proxy {proxy.id} sincronizado")
                else:
                    failed += 1
                    logger.error(f"❌ Proxy {proxy.id} falló")
            
            except Exception as e:
                logger.error(f"❌ Error sincronizando proxy {proxy.id}: {e}")
                failed += 1
            
            await asyncio.sleep(1)
        
        logger.info(
            f"✅ Sincronización completa: {synced} OK, {failed} fallidos"
        )
        
        return {"synced": synced, "failed": failed}
    

@router.post(
    "/profile/{profile_id}/rotate",
    summary="🔄 Rotar proxy de un perfil (manual)",
    description="""
Rota el proxy asignado a un perfil específico usando SOAX.
 
- Genera una nueva sesión con la misma ciudad (o la próxima disponible).
- Actualiza la contraseña y credenciales en AdsPower via el agente online.
- Crea una alerta activa visible en el panel hasta resolverse.
- Funciona igual que la rotación automática por crash, pero la dispara el operador.
 
Requiere que haya al menos un agente online para enviar el comando `update_proxy` a AdsPower.
""",
    tags=["Proxy Rotation"],
)
async def rotate_proxy_for_profile(
    profile_id:  int,
    db:          AsyncSession = Depends(get_db),
):
    """
    Endpoint manual para rotar el proxy de un perfil.
    Accesible desde Swagger en /docs y desde el panel de administración.
    """
    from app.models.profile import Profile
    from app.models.proxy import Proxy
    from app.core.connection_manager import connection_manager

    profile = await db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(
            status_code=404, detail=f"Perfil {profile_id} no encontrado"
        )
    if not profile.proxy_id:
        raise HTTPException(
            status_code=400, detail="El perfil no tiene proxy asignado"
        )

    proxy = await db.get(Proxy, profile.proxy_id)
    if not proxy:
        raise HTTPException(
            status_code=404, detail="Proxy del perfil no encontrado"
        )

    online_agents = connection_manager.get_online_agents()
    if not online_agents:
        raise HTTPException(
            status_code=503,
            detail="No hay agentes online. Conecta al menos un agente antes de rotar.",
        )

    computer_id = next(iter(online_agents))

    # _auto_rotate_proxy_for_profile está definida en este mismo módulo
    result = await _auto_rotate_proxy_for_profile(
        profile_id=profile_id,
        computer_id=computer_id,
        crash_alert_id=None,
    )

    if result.get("success"):
        return {
            "success":  True,
            "message":  f"Proxy rotado correctamente — {profile.name}",
            "new_city": result.get("new_city"),
            "alert_id": result.get("alert_id"),
            "proxy_id": profile.proxy_id,
        }
    else:
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Rotación fallida"),
        )


async def _auto_rotate_proxy_for_profile(
    profile_id:     int,
    computer_id:    int,
    crash_alert_id: int | None = None,
):
    """
    Rota automáticamente el proxy de un perfil tras un crash por proxy.
    También se puede llamar desde el endpoint manual /proxy-rotation/profile/{id}/rotate.
    """
    from app.database import AsyncSessionLocal
    from app.models.proxy import Proxy, ProxyStatus
    from app.models.alert import Alert, AlertSeverity, AlertStatus
    from app.config import settings
    from app.models.profile import Profile
    import uuid

    await asyncio.sleep(1)

    async with AsyncSessionLocal() as db:
        profile = await db.get(Profile, profile_id)
        if not profile or not profile.proxy_id:
            logger.warning(
                f"⚠️ Perfil {profile_id} sin proxy asignado — rotación cancelada")
            return {"success": False, "error": "Perfil sin proxy asignado"}

        proxy = await db.get(Proxy, profile.proxy_id)
        if not proxy:
            logger.warning(f"⚠️ Proxy del perfil {profile_id} no encontrado")
            return {"success": False, "error": "Proxy no encontrado"}

        profile_name = profile.name or f"Perfil #{profile_id}"

        # ── Reusar o crear la alerta ───────────────────────────────────────
        if crash_alert_id:
            alert = await db.get(Alert, crash_alert_id)
            if alert:
                alert.message = f"Proxy #{proxy.id} falló. Iniciando rotación automática..."
                await db.commit()
            else:
                crash_alert_id = None

        if not crash_alert_id:
            alert = Alert(
                title=f"Proxy inválido o caído — {profile_name}",
                message=f"Proxy #{proxy.id} falló. Iniciando rotación automática...",
                severity=AlertSeverity.ERROR.value,
                status=AlertStatus.ACTIVE.value,
                source="proxy_rotation",
                source_id=proxy.id,
            )
            db.add(alert)
            await db.commit()
            await db.refresh(alert)

        # Broadcast: rotación iniciando
        await connection_manager.broadcast_to_admins({
            "type":           "proxy_rotation_started",
            "alert_id":       alert.id,
            "profile_id":     profile_id,
            "profile_name":   profile_name,
            "proxy_id":       proxy.id,
            "message":        f"Rotando proxy — {profile_name}",
            "timestamp":      datetime.utcnow().isoformat(),
        })

        try:
            country = (proxy.country or "ec").lower()
            session_id = uuid.uuid4().hex[:16]
            lifetime = proxy.session_lifetime or 3600

            from app.utils.soax_cities_manager import get_soax_username_with_dynamic_city
            soax_result = await get_soax_username_with_dynamic_city(
                base_username=settings.SOAX_USERNAME,
                country=country,
                preferred_city=(proxy.city or "").lower() or None,
                exclude_cities=[],
                session_id=session_id,
                session_lifetime=lifetime,
            )
            new_username = soax_result.get("username")
            selected_city = soax_result.get(
                "selected_city") or proxy.city or country

            if not new_username:
                raise ValueError("SOAX no devolvió username válido")

            # Actualizar proxy en BD
            proxy.username = new_username
            proxy.password = settings.SOAX_PASSWORD
            proxy.host = settings.SOAX_HOST
            proxy.port = settings.SOAX_PORT
            proxy.session_id = session_id
            proxy.city = selected_city
            proxy.status = ProxyStatus.ACTIVE
            proxy.last_success_at = datetime.utcnow()
            await db.commit()

            # Obtener adspower_ids válidos
            adspower_ids = []
            if profile.adspower_id and not profile.adspower_id.startswith("pending"):
                adspower_ids = [profile.adspower_id]

            sent = await connection_manager.send_command_to_agent(
                computer_id=computer_id,
                command="update_proxy",
                payload={
                    "proxy_id":       proxy.id,
                    "profile_ids":    adspower_ids,
                    "proxy_host":     proxy.host,
                    "proxy_port":     proxy.port,
                    "proxy_user":     new_username,
                    "proxy_password": settings.SOAX_PASSWORD,
                }
            )

            if sent:
                alert.status = AlertStatus.RESOLVED.value
                alert.resolved_at = datetime.utcnow()
                await db.commit()

                logger.info(
                    f"✅ Proxy rotado: perfil {profile_id} → {selected_city}")
                await connection_manager.broadcast_to_admins({
                    "type":         "proxy_rotation_resolved",
                    "alert_id":     alert.id,
                    "profile_id":   profile_id,
                    "profile_name": profile_name,
                    "proxy_id":     proxy.id,
                    "new_city":     selected_city,
                    "message":      f"Proxy rotado — {profile_name} → {selected_city}",
                    "timestamp":    datetime.utcnow().isoformat(),
                })
                return {"success": True, "new_city": selected_city, "alert_id": alert.id}
            else:
                raise ValueError(
                    "Agente desconectado — no se pudo enviar update_proxy")

        except Exception as e:
            logger.error(f"❌ Error rotando proxy del perfil {profile_id}: {e}")
            await connection_manager.broadcast_to_admins({
                "type":         "proxy_rotation_failed",
                "alert_id":     alert.id,
                "profile_id":   profile_id,
                "profile_name": profile_name,
                "message":      f"Rotación falló — {profile_name}: {str(e)[:100]}",
                "timestamp":    datetime.utcnow().isoformat(),
            })
            return {"success": False, "error": str(e), "alert_id": alert.id}
