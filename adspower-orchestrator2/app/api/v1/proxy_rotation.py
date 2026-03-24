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
    """Espera hasta que haya un agente online y luego ejecuta la rotación"""
    from app.core.connection_manager import connection_manager
    max_wait_seconds = 300  # máximo 5 minutos esperando
    waited = 0

    while waited < max_wait_seconds:
        online_agents = connection_manager.get_online_agents()
        if online_agents:
            logger.info(f"✅ Agente disponible — iniciando rotación de proxies")
            await _background_check_all()
            return
        logger.info(
            f"⏳ Esperando agente online... ({waited}s / {max_wait_seconds}s)")
        await asyncio.sleep(10)
        waited += 10

    logger.warning(
        "⚠️ Timeout esperando agente — rotación cancelada después de 5 minutos")
    await connection_manager.broadcast_to_admins({
        "type":    "system_event",
        "event":   "proxy_rotation_timeout",
        "message": "Rotación cancelada — no hubo agente disponible en 5 minutos",
        "source":  "proxy_rotation",
    })


async def _background_check_all():
    from app.database import AsyncSessionLocal
    from app.models.proxy import Proxy, ProxyStatus
    from app.models.alert import Alert, AlertSeverity, AlertStatus
    from app.core.connection_manager import connection_manager
    from app.config import settings
    import secrets
    import json
    from sqlalchemy import select, or_

    async with AsyncSessionLocal() as db:
        # Obtener agentes online
        online_agents = connection_manager.get_online_agents()
        if not online_agents:
            logger.warning("No hay agentes online para verificar proxies")
            return

        computer_id = next(iter(online_agents))  # usar el primero disponible

        # Obtener proxies ACTIVE + FAILED
        result = await db.execute(
            select(Proxy).where(
                or_(Proxy.status == ProxyStatus.ACTIVE, Proxy.status == ProxyStatus.FAILED)
            )
        )
        proxies = result.scalars().all()
        logger.info(f"Verificando {len(proxies)} proxies via agente #{computer_id}")

        stats = {"total": len(proxies), "optimal": 0, "rotated": 0, "failed": 0}

        for proxy in proxies:
            city = None  # ← DEFINIR AL INICIO del loop para evitar el scoping error
            latency = None

            try:
                check = await connection_manager.request_proxy_check(
                    computer_id=computer_id,
                    proxy_id=proxy.id,
                    proxy_host=proxy.host,
                    proxy_port=int(proxy.port),          # ← forzar int
                    proxy_user=proxy.username or "",     # ← evitar None
                    proxy_password=proxy.password or "",  # ← evitar None
                    timeout=15.0,
                )

                if check is None:
                    logger.warning(f"Proxy {proxy.id}: timeout esperando respuesta del agente")
                    stats["failed"] += 1
                    from app.models.proxy_rotation_log import ProxyRotationLog, RotationTrigger
                    db.add(ProxyRotationLog(
                        proxy_id=          proxy.id,
                        computer_id=       computer_id,
                        old_proxy_display= f"{proxy.host}:{proxy.port} ({proxy.city or 'unknown'})",
                        trigger=           RotationTrigger.SCHEDULED,
                        success=           False,
                        error_message=     "Timeout — agente sin respuesta",
                    ))
                    await db.commit()
                    continue

                latency = check.get("latency_ms")

                if latency is not None and latency < 2000:
                    # ── PROXY ÓPTIMO ──────────────────────────────────────
                    proxy.avg_response_time = latency
                    proxy.status = ProxyStatus.ACTIVE
                    await db.commit()
                    stats["optimal"] += 1
                    logger.info(f"Proxy {proxy.id} OK ({latency}ms)")
                    await connection_manager.broadcast_to_admins({
                        "type":       "rotation_progress",
                        "proxy_id":   proxy.id,
                        "result":     "ok",
                        "latency_ms": latency,
                        "stats":      dict(stats),
                        "detail":     f"#{proxy.id} {proxy.host} — {latency}ms ✓ estable",
                    })
                    continue

                # ── PROXY LENTO U OFFLINE → ROTAR ─────────────────────────
                reason = "offline" if latency is None else f"latencia {latency}ms"
                logger.warning(f"Proxy {proxy.id} necesita rotación: {reason}")

                old_session = proxy.session_id or "—"

                # ← Usar ciudades dinámicas de SOAX con fallback automático
                from app.utils.soax_cities_manager import get_soax_username_with_dynamic_city
                soax_result = await get_soax_username_with_dynamic_city(
                    base_username=settings.SOAX_USERNAME,
                    country=(proxy.country or "ec").lower(),
                    preferred_city=None,  # ← no preferir la ciudad actual, buscar una diferente
                    exclude_cities=[proxy.city.lower()] if proxy.city else [],
                    session_lifetime=3600
                )
                new_user = soax_result.get("username")
                if not new_user:
                    raise ValueError(
                        f"SOAX no devolvió username válido para proxy {proxy.id}")
                # No usar proxy.city como fallback — si SOAX falló, la ciudad es desconocida
                
                city = soax_result.get(
                    "selected_city") or proxy.city or "unknown"
                
                # ← AGREGAR ESTO
                logger.info(
                    f"🔑 Proxy {proxy.id} — nuevo username SOAX: {new_user}"
                )
                logger.info(
                    f"   Ciudad seleccionada: {city} | Fallback usado: {soax_result.get('fallback_used', False)}"
                )

                if not new_user:
                    raise ValueError(f"SOAX no devolvió username válido para proxy {proxy.id}")

                raw = soax_result.get("username", "")
                # Extraer todo entre "sessionid-" y "-sessionlength" o fin de string
                match = re.search(r'sessionid-(.+?)(?:-sessionlength|$)', raw)
                session_id = match.group(1) if match else secrets.token_urlsafe(8)

                logger.info(
                    f"🔄 Proxy {proxy.id} rotando a ciudad: {city} "
                    f"(fallback: {soax_result.get('fallback_used', False)})"
                )

                from app.models.profile import Profile
                profiles_r = await db.execute(
                    select(Profile).where(Profile.proxy_id == proxy.id)
                )
                profiles_list = profiles_r.scalars().all()
                adspower_ids  = [
                    p.adspower_id for p in profiles_list
                    if p.adspower_id and not p.adspower_id.startswith("pending")
                ]

                sent = await connection_manager.send_command_to_agent(
                    computer_id=computer_id,
                    command="update_proxy",
                    payload={
                        "proxy_id":       proxy.id,
                        "profile_ids":    adspower_ids,
                        "proxy_host":     proxy.host,
                        "proxy_port":     proxy.port,
                        "proxy_user":     new_user,
                        "proxy_password": proxy.password or "",
                    }
                )

                if sent:
                    proxy.username   = new_user
                    proxy.session_id = session_id
                    proxy.status     = ProxyStatus.ACTIVE

                    from app.models.proxy_rotation_log import ProxyRotationLog, RotationTrigger
                    db.add(ProxyRotationLog(
                        proxy_id=          proxy.id,
                        computer_id=       computer_id,
                        old_proxy_display= f"{proxy.host}:{proxy.port} ({proxy.city or 'unknown'}) sesión:{old_session[:8]}",
                        new_proxy_display= f"{proxy.host}:{proxy.port} ({city}) sesión:{session_id[:8]}",
                        trigger=           RotationTrigger.SCHEDULED,
                        success=           True,
                        latency_ms=        latency,
                    ))

                    await db.commit()
                    stats["rotated"] += 1
                    logger.info(
                        f"Proxy {proxy.id} rotado → ciudad: {city} (session: {session_id[:6]}...)")
                    await connection_manager.broadcast_to_admins({
                        "type":     "rotation_progress",
                        "proxy_id": proxy.id,
                        "result":   "rotated",
                        "stats":    dict(stats),
                        "detail":   f"#{proxy.id} {proxy.host} → nueva sesión {city} ({len(adspower_ids)} perfiles)",
                    })
                else:
                    stats["failed"] += 1
                    from app.models.proxy_rotation_log import ProxyRotationLog, RotationTrigger
                    db.add(ProxyRotationLog(
                        proxy_id=          proxy.id,
                        computer_id=       computer_id,
                        old_proxy_display= f"{proxy.host}:{proxy.port} ({proxy.city or 'unknown'})",
                        trigger=           RotationTrigger.SCHEDULED,
                        success=           False,
                        error_message=     "update_proxy falló — AdsPower no alcanzable",
                        latency_ms=        latency,
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
                try:
                    from app.models.proxy_rotation_log import ProxyRotationLog, RotationTrigger
                    db.add(ProxyRotationLog(
                        proxy_id=          proxy.id,
                        computer_id=       computer_id,
                        old_proxy_display= f"{proxy.host}:{proxy.port} ({proxy.city or 'unknown'})",
                        trigger=           RotationTrigger.SCHEDULED,
                        success=           False,
                        error_message=     str(e),
                        latency_ms=        latency,
                    ))
                    await db.commit()
                except Exception:
                    pass

# ─── ALERTA RESUMEN ───────────────────────────────────────
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

        # ─── BROADCAST FINAL ──────────────────────────────────────
        try:
            await connection_manager.broadcast_to_admins({
                "type":    "system_event",
                "event":   "proxy_rotation_complete",
                "message": f"Rotación completada — {stats['rotated']} rotados, {stats['optimal']} óptimos",
                "source":  "proxy_rotation",
                "stats":   stats,
            })
            logger.info(f"Broadcast rotation_complete enviado a admins")
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
    """📊 Estadísticas simples"""
    
    from sqlalchemy import select, func
    from app.models.proxy import Proxy, ProxyStatus
    
    try:
        result = await db.execute(
            select(
                func.count(Proxy.id).label('total'),
                func.count(Proxy.id).filter(Proxy.status == ProxyStatus.ACTIVE).label('active'),
                func.count(Proxy.id).filter(Proxy.status == ProxyStatus.FAILED).label('failed'),
                func.avg(Proxy.avg_response_time).label('avg_latency')
            )
        )
        row = result.one()
        
        return {
            "total": row.total,
            "active": row.active,
            "failed": row.failed,
            "avg_latency_ms": round(row.avg_latency or 0, 2)
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