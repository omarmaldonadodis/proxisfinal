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
            logger.error("❌ No se pudo registrar. Abortando.")
            return

        self.is_connected = True
        self._setup_remote_logging()
        self.tray.update_status(True)

        tasks = [
            asyncio.create_task(self.server.connect_websocket()),
            asyncio.create_task(self._metrics_loop()),
            asyncio.create_task(self._heartbeat_loop()),
        ]

        #self.tray.start()

        logger.info("✅ Agente iniciado correctamente")

        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            pass

    def stop(self):
        """Detiene el agente limpiamente"""
        logger.info("Deteniendo agente...")
        self.is_running = False
        self.adspower.cleanup()

    # ========================================
    # LOOPS DE MONITOREO
    # ========================================

    async def _metrics_loop(self):
        """Cada N segundos envía métricas al servidor"""
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

            except Exception as e:
                logger.debug(f"Error en metrics loop: {e}")

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
        """Error abriendo el navegador"""
        logger.error(f"❌ Error en sesión {session_id}: {error}")
        await self.server.close_session(
            session_id=session_id,
            data_sent_mb=0,
            data_received_mb=0,
            pages_visited=0,
            crash_reason=error
        )

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
                
                await asyncio.sleep(0.5)  # ← ADD: respetar rate limit de AdsPower

        # Reportar resultado al backend
        if self.server.ws and self.server.is_connected:
            await self.server.ws.send(json.dumps({
                "type":          "proxy_update_result",
                "proxy_id":      data.get("proxy_id"),
                "success_count": success_count,
                "failed_count":  failed_count,
            }))

        logger.info(f"✅ update_proxy completado: {success_count} ok, {failed_count} fallidos")
        
    # Agregar método:
    async def _on_create_profile_command(self, data: dict):
        """Crea el perfil en AdsPower y notifica al servidor"""
        profile_id = data.get("profile_id")
        logger.info(f"📥 Creando perfil AdsPower para profile_id={profile_id}")

        adspower_id = await self.profile_creator.create_profile(data)

        # Notificar al servidor con el resultado
        if self.server.ws and self.server.is_connected:
            import json
            await self.server.ws.send(json.dumps({
                "type":        "profile_created",
                "profile_id":  profile_id,
                "adspower_id": adspower_id,  # None si falló
                "success":     adspower_id is not None,
            }))


    def _setup_remote_logging(self):
        server_ref = self.server

        async def remote_sink(message):
            record = message.record
            if server_ref.is_connected:
                await server_ref.send_log(
                    level=record["level"].name,
                    message=record["message"],
                )

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
        import httpx, json

        request_id  = data.get("request_id")
        adspower_id = data.get("adspower_id")
        logger.info(f"📥 verify_profile: adspower_id={adspower_id}")

        try:
            headers = {"Authorization": f"Bearer {self.config.adspower_api_key}"}

            async with httpx.AsyncClient(timeout=10.0) as client:
                # 1. Obtener info del perfil via API v1 real
                r = await client.get(
                    f"{self.config.adspower_url}/api/v1/user/list",
                    params={"user_id": adspower_id, "page": 1, "page_size": 1},
                    headers=headers,
                )
                resp = r.json()
                profiles_list = resp.get("data", {}).get("list", [])
                profile_info  = profiles_list[0] if profiles_list else {}
                logger.info(f"[VERIFY] profile_info keys: {list(profile_info.keys())}")

                # 2. Inferir cookies desde last_open_time y cookie field del perfil
                #    AdsPower almacena cookies en el campo "cookie" del profile
                #    pero solo cuando el browser está abierto las expone via /browser/cookies
                has_cookies  = False
                cookie_count = 0

                last_open_time = profile_info.get("last_open_time", "0")
                cookie_field   = profile_info.get("cookie", "")

                if cookie_field and cookie_field not in ("", "[]", None):
                    try:
                        import json as json_mod
                        parsed = json_mod.loads(cookie_field) if isinstance(cookie_field, str) else cookie_field
                        cookie_count = len(parsed) if isinstance(parsed, list) else 0
                        has_cookies  = cookie_count > 0
                    except Exception:
                        # Cookie field existe pero no es JSON válido — asumir que hay cookies
                        has_cookies  = True
                        cookie_count = 1

                # Si el browser está abierto ahora, leer cookies reales
                if not has_cookies and last_open_time and last_open_time != "0":
                    browser_check = await client.get(
                        f"{self.config.adspower_url}/api/v1/browser/active",
                        params={"user_id": adspower_id},
                        headers=headers,
                    )
                    if browser_check.status_code == 200:
                        bdata = browser_check.json()
                        if bdata.get("code") == 0 and bdata.get("data", {}).get("status") == "Active":
                            # Browser abierto — leer cookies reales
                            ck_r = await client.get(
                                f"{self.config.adspower_url}/api/v1/browser/cookies",
                                params={"user_id": adspower_id},
                                headers=headers,
                            )
                            if ck_r.status_code == 200 and ck_r.json().get("code") == 0:
                                cookies_data = ck_r.json().get("data", {}).get("cookies", [])
                                cookie_count = len(cookies_data)
                                has_cookies  = cookie_count > 0

            # 3. Datos de DB que el backend envió en el payload
            db_data = {
                "total_sessions":         data.get("total_sessions", 0),
                "is_warmed":              data.get("is_warmed", False),
                "total_duration_seconds": data.get("total_duration_seconds", 0),
                "cookie_count":           cookie_count,
                "cookie_status":          "OK" if has_cookies else data.get("cookie_status", "MISSING"),
            }

            # 4. Calcular score
            score_result = self._calculate_profile_score(profile_info, db_data)

            result_payload = {
                "type":              "verify_profile_result",
                "request_id":        request_id,
                "browser_score":     score_result["browser_score"],
                "fingerprint_score": score_result["fingerprint_score"],
                "cookie_status":     score_result["cookie_status"],
                "breakdown":         score_result["breakdown"],
                "grade":             score_result["grade"],
                "has_cookies":       has_cookies,
                "cookie_count":      cookie_count,
            }

        except Exception as e:
            logger.error(f"❌ verify_profile error: {e}")
            result_payload = {
                "type":              "verify_profile_result",
                "request_id":        request_id,
                "browser_score":     0,
                "fingerprint_score": 0,
                "cookie_status":     "MISSING",
                "has_cookies":       False,
                "error":             str(e),
            }

        if self.server.ws and self.server.is_connected:
            await self.server.ws.send(json.dumps(result_payload))
            logger.info(f"✅ verify_profile_result enviado: request_id={request_id}")
            # ========================================
# ENTRY POINT
# ========================================

def main():
    config = AgentConfig.load()

    if not config.is_configured():
        logger.info("Primera ejecución - configuración inicial")
        from agent.first_run import FirstRunSetup
        setup = FirstRunSetup()
        if not setup.run():
            logger.error("Configuración cancelada")
            sys.exit(1)
        config = AgentConfig.load()

    agent = AdsPowerAgent()

    if platform.system() != "Windows":
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, agent.stop)

    asyncio.run(agent.start())

if __name__ == "__main__":
    main()