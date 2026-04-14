# agent/main.py
"""
Entry point del agente AdsPower.
Orquesta todos los módulos y mantiene el ciclo de vida.
"""
import asyncio
import sys
import platform
import signal
from loguru import logger
from pathlib import Path

# Setup logging
from agent.config import AgentConfig, get_config_path

log_dir = get_config_path().parent / "logs"
log_dir.mkdir(exist_ok=True)
logger.add(
    str(log_dir / "agent_{time:YYYY-MM-DD}.log"),
    rotation="1 day",
    retention="7 days",
    level="INFO"
)





class AdsPowerAgent:

    def __init__(self):
        self.config = AgentConfig.load()
        self.is_running = False
        self.is_connected = False

        logger.info(f"DEBUG config.adspower_api_key = '{self.config.adspower_api_key}'")


        # Módulos
        from agent.adspower_monitor import AdsPowerMonitor
        from agent.network_monitor import NetworkMonitor
        from agent.server_client import ServerClient
        from agent.browser_launcher import BrowserLauncher
        from agent.tray_icon import TrayIcon

        from agent.profile_creator import ProfileCreator


        # ✅ FIX: pasar api_key al monitor
        self.adspower = AdsPowerMonitor(
            self.config.adspower_url,
            api_key=self.config.adspower_api_key
        )
        self.network = NetworkMonitor()
        self.server = ServerClient(self.config)
        # BrowserLauncher usa el mismo monitor que ya tiene el api_key
        self.launcher = BrowserLauncher(self.adspower)
        self.tray = TrayIcon(self)

        # Log para confirmar que la key cargó
        if self.config.adspower_api_key:
            logger.info(f"✅ AdsPower API Key cargada: {self.config.adspower_api_key[:8]}...")
        else:
            logger.warning("⚠️  AdsPower API Key NO configurada en config.json")

        # Conectar callbacks del servidor
        self.server.on_open_browser = self._on_open_browser_command
        self.server.on_close_browser = self._on_close_browser_command

        self.profile_creator = ProfileCreator(
            self.config.adspower_url,
            self.config.adspower_api_key
        )
        self.server.on_create_profile = self._on_create_profile_command
        self.server.on_update_proxy = self._on_update_proxy_command
        self.server.on_check_proxy    = self._on_check_proxy_command
        self.server.on_verify_profile = self._on_verify_profile_command
        self.server.on_delete_profile = self._on_delete_profile_command
        self._pending_proxy_rotations: list[dict] = []   # payloads pendientes
        self._rotation_queued = False  # flag para evitar duplicados en el timeline
        self._pending_profile_deletions: list[dict] = []
        self._creating_profiles: set[int] = set()  # ← agregar aquí
        self.server.on_check_adspower_now = self._report_adspower_status_now
        self._verify_queue: asyncio.Queue = asyncio.Queue()
        self._verify_worker_running = False  # ← agregar
    
    async def start(self):
        logger.info("=" * 50)
        logger.info(f"AdsPower Agent iniciando")
        logger.info(f"Servidor: {self.config.server_url}")
        logger.info(f"Agente: {self.config.agent_name}")
        logger.info(f"AdsPower URL: {self.config.adspower_url}")
        logger.info("=" * 50)

        self.is_running = True

        registered = await self.server.register()
        if not registered:
            logger.warning(
                "No se pudo registrar. Esperando para reintentar...")
            await self._wait_for_server()  # ← NUEVO: esperar en vez de abortar
            # logger.error("❌ No se pudo registrar. Abortando.")
            return

        self.is_connected = True
        self._setup_remote_logging()
        self.tray.update_status(True)

        tasks = [
            asyncio.create_task(self.server.connect_websocket()),
            asyncio.create_task(self._metrics_loop()),
            asyncio.create_task(self._heartbeat_loop()),
            asyncio.create_task(self._adspower_health_loop()),
        ]

        #self.tray.start()

        logger.info("✅ Agente iniciado correctamente")

        import threading
        from agent.local_api import start_local_api

        start_local_api(self)


        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            pass

    async def _wait_for_server(self):
        """Espera indefinidamente hasta que el servidor esté disponible"""
        import httpx
        retry_interval = 10
        while self.is_running:
            logger.info(f"⏳ Servidor no disponible, reintentando en {retry_interval}s...")
            await asyncio.sleep(retry_interval)
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    r = await client.get(f"{self.config.server_url}/health")
                    if r.status_code == 200:
                        registered = await self.server.register()
                        if registered:
                            logger.info("✅ Servidor recuperado, continuando...")
                            return
            except Exception:
                pass
            retry_interval = min(retry_interval * 1.5, 60)  # backoff hasta 60s
        
    def stop(self):
        """Detiene el agente limpiamente cerrando todos los navegadores"""
        logger.info("Deteniendo agente — cerrando navegadores activos...")
        self.is_running = False

        # Cerrar todos los navegadores activos sincrónicamente
        active = list(self.launcher.active_sessions.items())
        if active:
            logger.info(f"Cerrando {len(active)} navegador(es)...")
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Crear tarea de limpieza
                asyncio.create_task(self._shutdown_all_browsers())
            else:
                loop.run_until_complete(self._shutdown_all_browsers())

        self.adspower.cleanup()


    async def _shutdown_all_browsers(self):
        """Cierra todos los navegadores y notifica al servidor"""
        tasks = []
        for session_id, session in list(self.launcher.active_sessions.items()):
            tasks.append(self._close_session_on_shutdown(session_id, session))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("✅ Todos los navegadores cerrados")


    async def _close_session_on_shutdown(self, session_id: int, session):
        try:
            # Cerrar navegador en AdsPower
            self.monitor.close_browser(session.profile_id)

            # Notificar al servidor si hay conexión
            await self.server.close_session(
                session_id=session_id,
                data_sent_mb=0,
                data_received_mb=0,
                pages_visited=session.pages_visited,
                crash_reason="Agent shutdown"
            )
            logger.info(f"✅ Sesión {session_id} cerrada correctamente")
        except Exception as e:
            logger.error(f"Error cerrando sesión {session_id}: {e}")

    # ========================================
    # LOOPS DE MONITOREO
    # ========================================

    async def _metrics_loop(self):
        """Cada N segundos envía métricas al servidor"""
        _cleanup_counter = 0

        while self.is_running:
            try:
                metrics = self._collect_metrics()
                await self.server.send_metrics(metrics)

                for session_id, session in list(self.launcher.active_sessions.items()):
                    net_stats = self.network.get_stats()
                    adspower_stats = self.adspower.get_process_stats()

                    await self.server.update_metrics(
                        session_id=session_id,
                        data_sent_mb=net_stats["session_sent_mb"],
                        data_received_mb=net_stats["session_received_mb"],
                        pages_visited=session.pages_visited,
                        current_url=session.current_url,
                        browser_health=self.adspower.get_browser_health(session.profile_id),
                        cpu_percent=adspower_stats["cpu_percent"],
                        ram_mb=adspower_stats["ram_mb"]
                    )

                _cleanup_counter += 1
                if _cleanup_counter >= 12:  # cada ~2 minutos (12 * 10s)
                    _cleanup_counter = 0
                    await self._cleanup_dead_sessions()

            except Exception as e:
                logger.warning(f"⚠️ Error en metrics loop: {e}")

            await asyncio.sleep(self.config.metrics_interval_seconds)

    async def _heartbeat_loop(self):
        """Ping al servidor cada 30 segundos para mantener conexión"""
        while self.is_running:
            await asyncio.sleep(30)
            if self.server.ws and self.server.is_connected:
                try:
                    import json
                    await self.server.ws.send(json.dumps({"type": "heartbeat"}))
                except Exception:
                    pass
                
    async def _adspower_health_loop(self):
        was_running = None  # None = primer chequeo

        while self.is_running:
            await asyncio.sleep(15)
            try:
                is_running = await asyncio.get_event_loop().run_in_executor(
                    None, self.adspower.ping_api
                )

                if was_running != is_running:
                    status = "available" if is_running else "unavailable"
                    if self.server.ws and self.server.is_connected:
                        import json
                        await self.server.ws.send(json.dumps({
                            "type":    "adspower_status",
                            "status":  status,
                            "message": (
                                "✅ AdsPower disponible"
                                if is_running
                                else "⚠️ AdsPower no está disponible — abre la aplicación"
                            ),
                        }))

                        if was_running is not None:
                            await self.server.ws.send(json.dumps({
                                "type":    "log",
                                "level":   "INFO" if is_running else "ERROR",
                                "message": (
                                    "✅ AdsPower disponible nuevamente"
                                    if is_running
                                    else "⚠️ AdsPower no está disponible — abre la aplicación"
                                ),
                            }))

                # ✅ NUEVO: AdsPower volvió online → procesar cola pendiente
                if is_running and not was_running and self._pending_proxy_rotations:
                    logger.info(
                        f"🟢 AdsPower disponible — procesando "
                        f"{len(self._pending_proxy_rotations)} rotaciones encoladas"
                    )
                    await self._process_pending_rotations()

                was_running = is_running

            except Exception as e:
                logger.debug(f"Error en adspower_health_loop: {e}")


    async def _report_adspower_status_now(self):
        """Ping inmediato a AdsPower y reporta resultado al backend."""
        import json
        loop = asyncio.get_event_loop()
        is_available = await loop.run_in_executor(None, self.adspower.ping_api)
        status = "available" if is_available else "unavailable"

        if self.server.ws and self.server.is_connected:
            await self.server.ws.send(json.dumps({
                "type":    "adspower_status",
                "status":  status,
                "message": (
                    "✅ AdsPower disponible"
                    if is_available
                    else "⚠️ AdsPower no disponible — abre la aplicación"
                ),
            }))

        logger.debug(f"📡 AdsPower status report forzado: {status}")

        # ── Si AdsPower está disponible y hay cola pendiente, procesarla ─────
        if is_available:
            tiene_pendientes = (
                self._pending_proxy_rotations or
                self._pending_profile_deletions
            )
            if tiene_pendientes:
                logger.info(
                    f"🟢 AdsPower disponible — procesando cola pendiente "
                    f"({len(self._pending_proxy_rotations)} rotaciones, "
                    f"{len(self._pending_profile_deletions)} eliminaciones)"
                )
                asyncio.create_task(self._process_pending_rotations())
    
    async def _process_pending_rotations(self):
        """Ejecuta rotaciones encoladas cuando AdsPower vuelve online."""
        import json

        # ── Rotaciones de proxy ──────────────────────────────────────────────
        pending_rotations = list(self._pending_proxy_rotations)
        self._pending_proxy_rotations.clear()
        self._rotation_queued = False

        if self.server.ws and self.server.is_connected and pending_rotations:
            await self.server.ws.send(json.dumps({
                "type":    "system_event",
                "event":   "proxy_rotation_queue_processing",
                "message": f"⚡ Procesando {len(pending_rotations)} rotaciones encoladas",
                "source":  "agent",
            }))

        for data in pending_rotations:
            profile_ids = data.get("profile_ids", [])
            proxy_config = {
                "proxy_soft":     "other",
                "proxy_type":     "http",
                "proxy_host":     data["proxy_host"],
                "proxy_port":     str(data["proxy_port"]),
                "proxy_user":     data["proxy_user"],
                "proxy_password": data["proxy_password"],
            }
            logger.info(
                f"⚡ Ejecutando rotación encolada: proxy_id={data.get('proxy_id')}")
            await self._execute_proxy_update(data, proxy_config, profile_ids)
            await asyncio.sleep(2)

        # ── Eliminaciones de perfil pendientes ───────────────────────────────
        pending_deletions = list(self._pending_profile_deletions)
        self._pending_profile_deletions.clear()

        if pending_deletions:
            logger.info(
                f"🗑️ Procesando {len(pending_deletions)} eliminaciones de perfil encoladas"
            )
            if self.server.ws and self.server.is_connected:
                await self.server.ws.send(json.dumps({
                    "type":    "system_event",
                    "event":   "profile_deletion_queue_processing",
                    "message": f"🗑️ Procesando {len(pending_deletions)} eliminaciones encoladas",
                    "source":  "agent",
                }))

            for data in pending_deletions:
                await self._execute_profile_deletion(data)
                await asyncio.sleep(1)

        # ── Notificar fin ─────────────────────────────────────────────────────
        if self.server.ws and self.server.is_connected:
            await self.server.ws.send(json.dumps({
                "type":    "system_event",
                "event":   "proxy_rotation_queue_done",
                "message": "✅ Cola de operaciones procesada",
                "source":  "agent",
            }))

    def _collect_metrics(self) -> dict:
        adspower_stats = self.adspower.get_process_stats()
        net_stats = self.network.get_stats()
        sys_stats = self.network.get_system_stats()

        # Extraer profile_ids de las sesiones activas del launcher
        known_profile_ids = [
            s.profile_id for s in self.launcher.active_sessions.values()
        ]

        # Opción A: verificación rápida solo de perfiles que el agente abrió
        active_browsers = self.adspower.get_active_browsers(known_profile_ids)

        return {
            "computer_id": self.config.computer_id,
            "adspower_running": adspower_stats["is_running"],
            "adspower_cpu_percent": adspower_stats["cpu_percent"],
            "adspower_ram_mb": adspower_stats["ram_mb"],
            "active_browsers_count": len(active_browsers),
            "active_sessions": list(self.launcher.active_sessions.keys()),
            "network": net_stats,
            "system": sys_stats
        }
    # ========================================
    # COMANDOS DEL SERVIDOR
    # ========================================
    
    async def _check_adspower_available(self, action: str = "", name: str = "") -> bool:
        """
        Verificación ON-DEMAND con ping real a AdsPower.
        Solo notifica al backend si el estado CAMBIÓ — evita el bucle
        adspower_status → _process_pending_profiles → check_adspower → adspower_status.
        """
        loop = asyncio.get_event_loop()
        is_available = await loop.run_in_executor(None, self.adspower.ping_api)

        # Notificar al servidor SOLO si el estado cambió respecto al último conocido
        prev = getattr(self, '_last_adspower_available', None)
        if is_available != prev:
            self._last_adspower_available = is_available
            if self.server.ws and self.server.is_connected:
                import json
                await self.server.ws.send(json.dumps({
                    "type":    "adspower_status",
                    "status":  "available" if is_available else "unavailable",
                    "message": (
                        "✅ AdsPower disponible"
                        if is_available
                        else "⚠️ AdsPower no está disponible — abre la aplicación"
                    ),
                }))

        if not is_available:
            logger.warning(
                f"⚠️ Acción '{action}' bloqueada — AdsPower no responde")
            if self.server.ws and self.server.is_connected:
                import json
                await self.server.ws.send(json.dumps({
                    "type":    "adspower_unavailable_for_action",
                    "action":  action,
                    "name":    name,
                    "message": f"AdsPower no está disponible — abre la aplicación antes de '{action}'",
                }))

        return is_available


    async def _on_open_browser_command(self, session_id, profile_id, target_url):
         # ✅ Validar AdsPower ANTES de abrir navegador
        if not await self._check_adspower_available(action="open_browser"):
            await self.server.close_session(
                session_id=session_id,
                data_sent_mb=0, data_received_mb=0, pages_visited=0,
                crash_reason="AdsPower no está disponible — abre la aplicación"
            )
            return
    
        result = await self.launcher.launch(
            session_id=session_id,
            profile_id=profile_id,
            target_url=target_url,
            on_navigation=self._on_navigation,
            on_close=self._on_browser_close,
            on_error=self._on_browser_error
        )

        if result.get("success"):
            self.network.reset_session()   # ← resetear SOLO si el browser abrió
            await self.server.mark_session_active(session_id)
            logger.info(f"✅ Navegador activo confirmado: sesión={session_id}")
        else:
            logger.error(f"❌ Error abriendo navegador: {result.get('error')}")

    async def _on_close_browser_command(self, session_id: int):
        """El servidor ordena cerrar un navegador"""
        logger.info(f"📥 Comando close_browser: sesión={session_id}")
        await self.launcher.close_browser(session_id)

    async def _on_navigation(self, session_id: int, url: str, title: str):
        """El navegador navegó a una nueva URL"""
        logger.debug(f"🌐 Navegación: sesión={session_id} → {url}")
        await self.server.report_navigation(session_id, url, title)

    async def _on_browser_close(self, session_id: int, final_metrics: dict):
        """El navegador fue cerrado"""
        logger.info(f"🔴 Sesión cerrada: {session_id}")
        net_stats = self.network.get_stats()

        await self.server.close_session(
            session_id=session_id,
            data_sent_mb=net_stats["session_sent_mb"],
            data_received_mb=net_stats["session_received_mb"],
            pages_visited=final_metrics.get("pages_visited", 0)
        )

    async def _on_browser_error(self, session_id: int, error: str):
        """Error abriendo el navegador — cierra sesión en backend y limpia local"""
        # Clasificar el error para mejor visibilidad
        if "ADSPOWER_OFFLINE" in error or "AdsPower no disponible" in error:
            logger.error(f"❌ Sesión {session_id} — AdsPower no está abierto")
        elif "PROXY_INVALID" in error or "Proxy inválido" in error:
            logger.error(
                f"❌ Sesión {session_id} — Proxy caído o inválido, necesita rotación")
        elif "TIMEOUT" in error or "Timeout" in error:
            logger.error(
                f"❌ Sesión {session_id} — Timeout: navegador tardó demasiado")
        elif "not exist" in error.lower():
            logger.error(
                f"❌ Sesión {session_id} — Perfil no existe en AdsPower")
        else:
            logger.error(f"❌ Error en sesión {session_id}: {error}")

        # Limpiar sesión local si quedó registrada
        if session_id in self.launcher.active_sessions:
            session = self.launcher.active_sessions.pop(session_id)
            session.is_running = False
            logger.info(f"🧹 Sesión zombie limpiada: {session_id}")

        # Verificar conexión antes de reportar
        if not self.server.is_connected or not self.server.ws:
            logger.warning(
                f"⚠️ Sin conexión al backend — error de sesión {session_id} no reportado")
            return

        try:
            await self.server.close_session(
                session_id=session_id,
                data_sent_mb=0,
                data_received_mb=0,
                pages_visited=0,
                crash_reason=error
            )
            logger.info(f"✅ Error de sesión {session_id} reportado al backend")
        except Exception as e:
            logger.error(f"❌ No se pudo reportar error al backend: {e}")

    async def _on_update_proxy_command(self, data: dict):
        """
        Actualiza proxy en AdsPower.
        Si AdsPower no está disponible → encola el comando y lo ejecuta
        cuando AdsPower vuelva a estar online.
        """
        import httpx
        import json

        profile_ids = data.get("profile_ids", [])
        proxy_config = {
            "proxy_soft":     "other",
            "proxy_type":     "http",
            "proxy_host":     data["proxy_host"],
            "proxy_port":     str(data["proxy_port"]),
            "proxy_user":     data["proxy_user"],
            "proxy_password": data["proxy_password"],
        }

        logger.info(
            f"🔄 update_proxy: {len(profile_ids)} perfiles → "
            f"{data['proxy_host']}:{data['proxy_port']} — verificando AdsPower..."
        )

        # ✅ Verificar AdsPower con ping real ANTES de actuar
        if not await self._check_adspower_available(action="update_proxy"):
            # Encolar para cuando AdsPower esté disponible
            if data not in self._pending_proxy_rotations:
                self._pending_proxy_rotations.append(data)
                logger.warning(
                    f"⏸️ update_proxy encolado ({len(self._pending_proxy_rotations)} pendientes) "
                    f"— esperando AdsPower"
                )

                if self.server.ws and self.server.is_connected:
                    await self.server.ws.send(json.dumps({
                        "type":      "proxy_rotation_queued",
                        "proxy_id":  data.get("proxy_id"),
                        "reason":    "AdsPower no está disponible — se ejecutará cuando abra",
                        "queued":    len(self._pending_proxy_rotations),
                    }))
            return

        # AdsPower disponible → ejecutar
        await self._execute_proxy_update(data, proxy_config, profile_ids)

    async def _execute_proxy_update(self, data: dict, proxy_config: dict, profile_ids: list):
        """Ejecuta el update_proxy real contra AdsPower."""
        import httpx
        import json

        success_count = 0
        failed_count = 0

        async with httpx.AsyncClient(timeout=30.0) as client:
            for ads_id in profile_ids:
                try:
                    r = await client.post(
                        f"{self.config.adspower_url}/api/v1/user/update",
                        json={"user_id": ads_id,
                              "user_proxy_config": proxy_config},
                        headers={
                            "Authorization": f"Bearer {self.config.adspower_api_key}"},
                    )
                    if r.status_code == 200 and r.json().get("code") == 0:
                        success_count += 1
                        logger.info(f"  ✅ Perfil {ads_id} proxy actualizado")
                    else:
                        failed_count += 1
                        logger.warning(f"  ⚠️ Perfil {ads_id} falló: {r.text}")
                except Exception as e:
                    failed_count += 1
                    logger.error(f"  ❌ Perfil {ads_id}: {e}")

                await asyncio.sleep(1)

        if self.server.ws and self.server.is_connected:
            try:
                await self.server.ws.send(json.dumps({
                    "type":          "proxy_update_result",
                    "proxy_id":      data.get("proxy_id"),
                    "success_count": success_count,
                    "failed_count":  failed_count,
                }))
            except Exception as e:
                logger.error(f"❌ No se pudo reportar resultado proxy: {e}")

        logger.info(
            f"✅ update_proxy: {success_count} ok, {failed_count} fallidos")

        if success_count > 0:
            logger.info("⏳ Esperando 4s para que AdsPower recargue proxy...")
            await asyncio.sleep(4)
        
    # Agregar método:
    async def _on_create_profile_command(self, data: dict):
        profile_id = data.get("profile_id")
        name = data.get("name")

        # ── Guard: evitar crear el mismo perfil dos veces ────────────────────
        if profile_id in self._creating_profiles:
            logger.warning(
                f"⏭️ Perfil {profile_id} ya está siendo creado, ignorando duplicado")
            return
        self._creating_profiles.add(profile_id)
        # ─────────────────────────────────────────────────────────────────────

        try:
            if not await self._check_adspower_available(action="create_profile", name=name):
                return

            logger.info(f"📥 Creando perfil AdsPower para profile_id={profile_id}")

            try:
                adspower_id = await self.profile_creator.create_profile(data)
            except ValueError as e:
                friendly_msg = str(e)
                logger.error(f"❌ Perfil {name} no creado: {friendly_msg}")
                if self.server.ws and self.server.is_connected:
                    import json
                    await self.server.ws.send(json.dumps({
                        "type":       "profile_create_error",
                        "profile_id": profile_id,
                        "name":       name,
                        "error":      friendly_msg,
                    }))
                return
            except Exception as e:
                friendly_msg = f"Error inesperado creando perfil: {e}"
                logger.error(f"❌ {friendly_msg}")
                if self.server.ws and self.server.is_connected:
                    import json
                    await self.server.ws.send(json.dumps({
                        "type":       "profile_create_error",
                        "profile_id": profile_id,
                        "name":       name,
                        "error":      friendly_msg,
                    }))
                return

            if self.server.ws and self.server.is_connected:
                import json
                await self.server.ws.send(json.dumps({
                    "type":        "profile_created",
                    "name":        name,
                    "profile_id":  profile_id,
                    "adspower_id": adspower_id,
                    "success":     True,
                }))

        finally:
            # Siempre liberar el guard, incluso si hubo excepción
            self._creating_profiles.discard(profile_id)

    async def _on_delete_profile_command(self, data: dict):
        """
        Elimina un perfil de AdsPower local.
        Si AdsPower no está disponible → encola y procesa cuando vuelva.
        """
        import json

        adspower_id = data.get("adspower_id")
        profile_id = data.get("profile_id")

        if not adspower_id or adspower_id.startswith("pending-"):
            logger.info(f"🗑️ Perfil {profile_id} sin adspower_id válido, skip")
            return

        logger.info(f"🗑️ Solicitud de eliminación AdsPower: {adspower_id}")

        # ── Verificar AdsPower disponible ────────────────────────────────────
        if not await self._check_adspower_available(action="delete_profile"):
            # Encolar para cuando AdsPower vuelva a estar disponible
            if not any(d.get("adspower_id") == adspower_id
                    for d in self._pending_profile_deletions):
                self._pending_profile_deletions.append(data)
                logger.warning(
                    f"⏸️ delete_profile encolado ({len(self._pending_profile_deletions)} "
                    f"pendientes) — esperando AdsPower: {adspower_id}"
                )
                if self.server.ws and self.server.is_connected:
                    await self.server.ws.send(json.dumps({
                        "type":        "profile_delete_queued",
                        "adspower_id": adspower_id,
                        "profile_id":  profile_id,
                        "reason":      "AdsPower no está disponible",
                        "queued":      len(self._pending_profile_deletions),
                    }))
            return

        # AdsPower disponible → ejecutar eliminación
        await self._execute_profile_deletion(data)


    async def _execute_profile_deletion(self, data: dict):
        """Ejecuta la eliminación real del perfil en AdsPower."""
        import httpx
        import json

        adspower_id = data.get("adspower_id")
        profile_id = data.get("profile_id")

        try:
            headers = {}
            if self.config.adspower_api_key:
                headers["Authorization"] = f"Bearer {self.config.adspower_api_key}"

            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.post(
                    f"{self.config.adspower_url}/api/v1/user/delete",
                    json={"user_ids": [adspower_id]},
                    headers=headers,
                )
                data_resp = r.json()

                if data_resp.get("code") == 0:
                    logger.info(f"✅ Perfil {adspower_id} eliminado de AdsPower")
                    # Limpiar de la cola backend
                    if self.server.ws and self.server.is_connected:
                        await self.server.ws.send(json.dumps({
                            "type":        "profile_delete_result",
                            "profile_id":  profile_id,
                            "adspower_id": adspower_id,
                            "status":      "deleted",
                        }))
                else:
                    msg = data_resp.get("msg", "")
                    already_gone = any(k in msg.lower() for k in [
                        "not exist", "being used by other", "does not exist"
                    ])
                    if already_gone:
                        logger.info(
                            f"ℹ️ Perfil {adspower_id} ya no estaba en AdsPower: {msg}"
                        )
                        if self.server.ws and self.server.is_connected:
                            await self.server.ws.send(json.dumps({
                                "type":        "profile_delete_result",
                                "profile_id":  profile_id,
                                "adspower_id": adspower_id,
                                "status":      "already_gone",
                            }))
                    else:
                        logger.warning(
                            f"⚠️ AdsPower no eliminó {adspower_id}: {msg}")

        except Exception as e:
            logger.error(
                f"❌ Error eliminando perfil {adspower_id} de AdsPower: {e}")
            # Re-encolar si fue un error de conexión
            if "connection" in str(e).lower() or "All connection" in str(e):
                if not any(d.get("adspower_id") == adspower_id
                        for d in self._pending_profile_deletions):
                    self._pending_profile_deletions.append(data)
                    logger.warning(
                        f"⏸️ Re-encolado tras error de conexión: {adspower_id}")
                
    def _setup_remote_logging(self):
        server_ref = self.server

        async def remote_sink(message):
            record = message.record
            if not server_ref.is_connected or not server_ref.ws:
                return
            try:
                await server_ref.send_log(
                    level=record["level"].name,
                    message=(
                        f"[{record['name']}:{record['function']}:{record['line']}] "
                        f"{record['message']}"
                    ),
                )
            except Exception:
                pass  # No loguear errores del logger — evita loop infinito

        logger.add(remote_sink, level="WARNING")


    async def _on_check_proxy_command(self, data: dict):
        """Hace ping al proxy DESDE esta máquina y reporta latencia al backend."""
        import httpx, time, json

        request_id = data.get("request_id")
        proxy_id   = data.get("proxy_id")
        host       = data.get("proxy_host")
        port       = data.get("proxy_port")
        user       = data.get("proxy_user")
        password   = data.get("proxy_password")

        proxy_url = f"http://{user}:{password}@{host}:{port}"
        latency_ms = None
        error = None

        try:
            start = time.time()
            async with httpx.AsyncClient(
                proxy=proxy_url,
                timeout=10.0
            ) as client:
                r = await client.get("https://api.ipify.org?format=json")
                if r.status_code == 200:
                    latency_ms = int((time.time() - start) * 1000)
        except Exception as e:
            error = str(e)
            logger.warning(f"Proxy {proxy_id} unreachable: {e}")

        if self.server.ws and self.server.is_connected:
            await self.server.ws.send(json.dumps({
                "type":       "proxy_check_result",
                "request_id": request_id,
                "proxy_id":   proxy_id,
                "latency_ms": latency_ms,   # None = offline
                "error":      error,
            }))

    def _calculate_profile_score(self, profile_info: dict, db_profile_data: dict) -> dict:
        scores = {}

        # ── 1. PROXY (25pts) ──────────────────────────
        proxy = profile_info.get("user_proxy_config", {})
        proxy_score = 0
        if proxy.get("proxy_host"):                                    proxy_score += 10
        if proxy.get("proxy_user") and proxy.get("proxy_password"):    proxy_score += 10
        if "sessionid" in proxy.get("proxy_user", ""):                 proxy_score += 5
        scores["proxy"] = proxy_score

        # ── 2. COOKIES (35pts) ───────────────────────  ← ESTE FALTABA
        cookie_count = db_profile_data.get("cookie_count", 0)
        cookie_score = 0
        if   cookie_count >= 50: cookie_score = 35
        elif cookie_count >= 20: cookie_score = 28
        elif cookie_count >= 10: cookie_score = 20
        elif cookie_count >= 3:  cookie_score = 12
        elif cookie_count >= 1:  cookie_score = 6
        scores["cookies"] = cookie_score

        # ── 3. MADUREZ (25pts) ───────────────────────
        session_score = 0
        if db_profile_data.get("total_sessions", 0) >= 5:            session_score += 10
        elif db_profile_data.get("total_sessions", 0) >= 1:          session_score += 6
        if db_profile_data.get("total_duration_seconds", 0) >= 3600: session_score += 8
        if profile_info.get("last_open_time", "0") != "0":           session_score += 2
        scores["maturity"] = session_score

        # ── 4. ANTI-DETECCIÓN (20pts) ─────────────────
        anti_score = 0
        if profile_info.get("ipchecker"):                              anti_score += 8
        if proxy.get("proxy_type") in ("http", "socks5"):              anti_score += 8
        if profile_info.get("remark"):                                 anti_score += 4
        scores["anti_detection"] = anti_score

        total = min(sum(scores.values()), 100)

        return {
            "browser_score":     total,
            "fingerprint_score": scores["proxy"] + scores["anti_detection"],
            "breakdown":         scores,
            "cookie_status":     db_profile_data.get("cookie_status", "MISSING"),
            "grade": (
                "EXCELENTE" if total >= 80 else
                "BUENO"     if total >= 60 else
                "REGULAR"   if total >= 40 else
                "DÉBIL"
            )
        }   

    async def _on_verify_profile_command(self, data: dict):
        if not hasattr(self, '_verify_queue'):
            self._verify_queue = asyncio.Queue()
            self._verify_worker_running = False
        await self._verify_queue.put(data)
        if not self._verify_worker_running:
            asyncio.create_task(self._verify_worker())


    async def _verify_worker(self):
        """Procesa verificaciones de a una por vez."""
        self._verify_worker_running = True
        try:
            while not self._verify_queue.empty():
                data = await self._verify_queue.get()
                await self._run_verify_profile(data)
                await asyncio.sleep(3)  # pausa entre verificaciones
        finally:
            self._verify_worker_running = False


    async def _run_verify_profile(self, data: dict):
        """Lógica original de verificación — sin cambios."""
        import json
        from agent.profile_verifier import ProfileVerifier

        request_id = data.get("request_id")
        adspower_id = data.get("adspower_id")
        name = data.get("name", adspower_id)

        logger.info(
            f"📥 verify_profile recibido: {adspower_id} — verificando AdsPower...")

        if not await self._check_adspower_available(action="verify_profile", name=name):
            if self.server.ws and self.server.is_connected and request_id:
                await self.server.ws.send(json.dumps({
                    "type":              "verify_profile_result",
                    "request_id":        request_id,
                    "browser_score":     0,
                    "fingerprint_score": 0,
                    "cookie_status":     data.get("cookie_status", "MISSING"),
                    "has_cookies":       False,
                    "breakdown":         {},
                    "grade":             "DÉBIL",
                    "error":             "AdsPower no está disponible",
                }))
            return

        logger.info(
            f"✅ AdsPower disponible — iniciando verificación de {adspower_id}")

        verifier = ProfileVerifier(
            self.config.adspower_url, self.config.adspower_api_key)
        db_data = {
            "total_sessions":         data.get("total_sessions", 0),
            "is_warmed":              data.get("is_warmed", False),
            "total_duration_seconds": data.get("total_duration_seconds", 0),
            "cookie_status":          data.get("cookie_status", "MISSING"),
            "timezone":               data.get("timezone", ""),
            "hardware_concurrency":   data.get("hardware_concurrency"),
        }

        result = await verifier.verify(adspower_id, db_data)

        if result.get("error"):
            logger.error(
                f"Verificar perfil falló para {adspower_id}: {result['error']}")
        else:
            logger.info(
                f"Verificar perfil exitoso para {adspower_id}: score={result.get('browser_score')} grade={result.get('grade')}")

        if self.server.ws and self.server.is_connected:
            await self.server.ws.send(json.dumps({
                "type":              "verify_profile_result",
                "request_id":        request_id,
                "browser_score":     result.get("browser_score", 0),
                "fingerprint_score": result.get("fingerprint_score", 0),
                "cookie_status":     result.get("cookie_status", "MISSING"),
                "has_cookies":       result.get("has_cookies", False),
                "breakdown":         result.get("breakdown", {}),
                "issues":            result.get("issues", []),
                "warnings":          result.get("warnings", []),
                "raw_fingerprint":   result.get("raw_fingerprint", {}),
                "grade":             result.get("grade", "DÉBIL"),
                "error":             result.get("error"),
            }))


    async def _cleanup_dead_sessions(self):
        """
        Verifica qué sesiones activas tienen el navegador realmente cerrado.
        Limpia las sesiones fantasma sin esperar al monitor de CDP.
        """
        import httpx
        import time

        GRACE_PERIOD_SECONDS = 90  # No verificar sesiones recientes
        CDP_TIMEOUT = 5.0          # Aumentado de 2.0 → 5.0s para páginas pesadas
        MAX_CONSECUTIVE_FAILURES = 3  # Confirmar con múltiples intentos

        for session_id, session in list(self.launcher.active_sessions.items()):
            try:
                debug_address = getattr(session, '_debug_address', None)
                if not debug_address:
                    continue

                # ── Período de gracia ──────────────────────────────────────────
                session_age = time.time() - (session.opened_at or time.time())
                if session_age < GRACE_PERIOD_SECONDS:
                    logger.debug(
                        f"Sesión {session_id} en período de gracia "
                        f"({session_age:.0f}s < {GRACE_PERIOD_SECONDS}s), ignorando"
                    )
                    continue

                # ── Verificar con timeout generoso ────────────────────────────
                alive = False
                try:
                    async with httpx.AsyncClient(timeout=CDP_TIMEOUT) as client:
                        r = await client.get(f"http://{debug_address}/json/version")
                        alive = r.status_code == 200
                except Exception:
                    alive = False

                if alive:
                    continue  # Navegador vivo, ok

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Error verificando sesión {session_id}: {e}")
                continue

            # ── Solo aquí: navegador cerrado + fuera del período de gracia ──
            logger.warning(
                f"⚠️ Sesión fantasma detectada: {session_id} — cerrando..."
            )
            session.is_running = False
            self.launcher.active_sessions.pop(session_id, None)

            await self.server.close_session(
                session_id=session_id,
                data_sent_mb=0,
                data_received_mb=0,
                pages_visited=session.pages_visited,
                crash_reason="Browser cerrado externamente",
            )

# ========================================
# ENTRY POINT
# ========================================


def main():
    config = AgentConfig.load()

    if not config.is_configured():
        from agent.first_run import FirstRunSetup
        setup = FirstRunSetup()
        if not setup.run():
            sys.exit(1)
        config = AgentConfig.load()

    agent = AdsPowerAgent()

    async def _run():
        loop = asyncio.get_running_loop()

        # Manejador de señales que espera cierre limpio
        def _signal_handler():
            logger.info("🛑 Señal de cierre recibida")
            asyncio.create_task(_graceful_shutdown())

        async def _graceful_shutdown():
            await agent._shutdown_all_browsers()
            agent.stop()

        if platform.system() != "Windows":
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, _signal_handler)

        await agent.start()

    asyncio.run(_run())

if __name__ == "__main__":
    main()