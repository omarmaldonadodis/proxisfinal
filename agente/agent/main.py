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
                if _cleanup_counter >= 3:
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
        """Verifica cada 15s si AdsPower está corriendo y reporta al backend"""
        was_running = True  # asumimos que arranca corriendo
        while self.is_running:
            await asyncio.sleep(15)
            try:
                is_running = await asyncio.get_event_loop().run_in_executor(
                    None, self.adspower.ping_api
                )

                if was_running and not is_running:
                    # AdsPower acaba de caerse
                    # logger.warning("⚠️ AdsPower dejó de responder")
                    if self.server.ws and self.server.is_connected:
                        import json
                        await self.server.ws.send(json.dumps({
                            "type":    "log",
                            "level":   "ERROR",
                            "message": "⚠️ AdsPower no está disponible — aplicación cerrada o bloqueada",
                        }))
                    # Cerrar sesiones activas
                    for session_id in list(self.launcher.active_sessions.keys()):
                        await self._on_browser_error(
                            session_id,
                            "AdsPower dejó de responder"
                        )

                elif not was_running and is_running:
                    # AdsPower volvió
                    logger.info("✅ AdsPower volvió a estar disponible")
                    if self.server.ws and self.server.is_connected:
                        import json
                        await self.server.ws.send(json.dumps({
                            "type":    "log",
                            "level":   "INFO",
                            "message": "✅ AdsPower disponible nuevamente",
                        }))

                was_running = is_running

            except Exception as e:
                logger.debug(f"Error en adspower_health_loop: {e}")

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

    async def _on_open_browser_command(self, session_id, profile_id, target_url):
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
        """Backend pide rotar proxy en AdsPower local."""
        import httpx
        import json

        profile_ids  = data.get("profile_ids", [])
        proxy_config = {
            "proxy_soft":     "other",
            "proxy_type":     "http",
            "proxy_host":     data["proxy_host"],
            "proxy_port":     str(data["proxy_port"]),
            "proxy_user":     data["proxy_user"],
            "proxy_password": data["proxy_password"],
        }

        logger.info(f"🔄 update_proxy: {len(profile_ids)} perfiles → {data['proxy_host']}:{data['proxy_port']}")

        success_count = 0
        failed_count  = 0

        async with httpx.AsyncClient(timeout=30.0) as client:
            for ads_id in profile_ids:
                try:
                    r = await client.post(
                        f"{self.config.adspower_url}/api/v1/user/update",
                        json={"user_id": ads_id, "user_proxy_config": proxy_config},
                        headers={"Authorization": f"Bearer {self.config.adspower_api_key}"},
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
                
                await asyncio.sleep(1)  # ← ADD: respetar rate limit de AdsPower

        # Reportar resultado al backend
        if self.server.ws and self.server.is_connected:
            try:
                await self.server.ws.send(json.dumps({
                    "type":          "proxy_update_result",
                    "proxy_id":      data.get("proxy_id"),
                    "success_count": success_count,
                    "failed_count":  failed_count,
                }))
                logger.info(f"✅ Resultado proxy_update enviado al backend")
            except Exception as e:
                logger.error(
                    f"❌ No se pudo reportar resultado de proxy al backend: {e}")
        else:
            logger.warning(
                f"⚠️ Sin conexión — resultado proxy_update no enviado")

        logger.info(f"✅ update_proxy completado: {success_count} ok, {failed_count} fallidos")
        
        # ← AGREGAR ESTO: dar tiempo a AdsPower para recargar el proxy
        if success_count > 0:
            logger.info(
                "⏳ Esperando 4s para que AdsPower recargue el proxy...")
            await asyncio.sleep(4)
        
    # Agregar método:
    async def _on_create_profile_command(self, data: dict):
        profile_id = data.get("profile_id")
        name = data.get("name")
        
        logger.info(f"📥 Creando perfil AdsPower para profile_id={profile_id}")

        try:
            adspower_id = await self.profile_creator.create_profile(data)
        except ValueError as e:
            # Error conocido (límite, proxy, etc.) — NO crear en BD
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

        # Solo llega aquí si AdsPower creó el perfil exitosamente
        if self.server.ws and self.server.is_connected:
            import json
            await self.server.ws.send(json.dumps({
                "type":        "profile_created",
                "name":        name,
                "profile_id":  profile_id,
                "adspower_id": adspower_id,
                "success":     True,
            }))

    async def _on_delete_profile_command(self, data: dict):
        """Elimina un perfil de AdsPower local."""
        import httpx
        import json

        adspower_id = data.get("adspower_id")
        profile_id = data.get("profile_id")

        if not adspower_id or adspower_id.startswith("pending-"):
            logger.info(
                f"🗑️ Perfil {profile_id} sin adspower_id válido, skip AdsPower")
            return

        logger.info(f"🗑️ Eliminando perfil AdsPower: {adspower_id}")

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
                else:
                    msg = data_resp.get("msg", "")
                    # Casos donde el perfil ya no está disponible — no es error crítico
                    already_gone = (
                        "not exist" in msg.lower() or
                        "being used by other" in msg.lower() or  # ← perfil en Trash
                        "does not exist" in msg.lower()
                    )
                    if already_gone:
                        logger.info(
                            f"ℹ️ Perfil {adspower_id} ya no estaba disponible en AdsPower "
                            f"(en Trash o eliminado previamente): {msg}"
                        )
                    else:
                        logger.warning(
                            f"⚠️ AdsPower no eliminó {adspower_id}: {msg}")

            await self.server.ws.send(json.dumps({
                "type":       "profile_delete_result",
                "profile_id": profile_id,
                "adspower_id": adspower_id,
                "status":     "deleted",   # o "skipped" si already_gone
            }))

        except Exception as e:
            logger.error(
                f"❌ Error eliminando perfil {adspower_id} de AdsPower: {e}")
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
    # agent/main.py — _on_verify_profile_command COMPLETO
    

    async def _on_verify_profile_command(self, data: dict):
        import json
        from agent.profile_verifier import ProfileVerifier

        request_id  = data.get("request_id")
        adspower_id = data.get("adspower_id")
        name        = data.get("name")
        logger.info(f"📥 verify_profile: adspower_id={adspower_id}")

        verifier = ProfileVerifier(
            self.config.adspower_url,
            self.config.adspower_api_key
        )

        db_data = {
            "total_sessions":         data.get("total_sessions", 0),
            "is_warmed":              data.get("is_warmed", False),
            "total_duration_seconds": data.get("total_duration_seconds", 0),
            "cookie_status":          data.get("cookie_status", "MISSING"),
            "timezone":               data.get("timezone", ""),
            "hardware_concurrency":   data.get("hardware_concurrency"),
        }

        result = await verifier.verify(adspower_id, db_data)

        # ← AGREGAR: loguear si hubo error
        if result.get("error"):
            logger.error(
                f"Verificar perfil falló para {name}: {result['error']}"
            )
        else:
            logger.info(
                f"Verificar perfil exitoso para {name}: score={result.get('browser_score')} "
                f"grade={result.get('grade')} "
                f"cookies={result.get('cookie_count')} "
                f"issues={result.get('issues', [])}"
            )

        payload = {
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
        }

        if self.server.ws and self.server.is_connected:
            await self.server.ws.send(json.dumps(payload))    

    # Agregar en la clase AdsPowerAgent:

    async def _cleanup_dead_sessions(self):
        """
        Verifica qué sesiones activas tienen el navegador realmente cerrado.
        Limpia las sesiones fantasma sin esperar al monitor de CDP.
        """
        for session_id, session in list(self.launcher.active_sessions.items()):
            try:
                debug_address = getattr(session, '_debug_address', None)
                if not debug_address:
                    continue

                # Ping rápido al Chrome — si no responde, la sesión está muerta
                async with httpx.AsyncClient(timeout=2.0) as client:
                    r = await client.get(f"http://{debug_address}/json/version")
                    if r.status_code == 200:
                        continue  # navegador vivo, ok

            except Exception:
                pass  # No respondió = navegador cerrado

            # Navegador cerrado pero sesión activa → limpiar
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