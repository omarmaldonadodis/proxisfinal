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

        # Módulos
        from agent.adspower_monitor import AdsPowerMonitor
        from agent.network_monitor import NetworkMonitor
        from agent.server_client import ServerClient
        from agent.browser_launcher import BrowserLauncher
        from agent.tray_icon import TrayIcon

        self.adspower = AdsPowerMonitor(self.config.adspower_url)
        self.network = NetworkMonitor()
        self.server = ServerClient(self.config)
        self.launcher = BrowserLauncher(self.adspower, api_key=self.config.adspower_api_key)
        self.tray = TrayIcon(self)

        # Conectar callbacks del servidor
        self.server.on_open_browser = self._on_open_browser_command
        self.server.on_close_browser = self._on_close_browser_command

    async def start(self):
        """Inicia el agente"""
        logger.info("=" * 50)
        logger.info(f"AdsPower Agent iniciando")
        logger.info(f"Servidor: {self.config.server_url}")
        logger.info(f"Agente: {self.config.agent_name}")
        logger.info("=" * 50)

        self.is_running = True

        # 1. Registrar computadora en servidor
        registered = await self.server.register()
        if not registered:
            logger.error("❌ No se pudo registrar en el servidor. Verifica la URL y el token.")
            # Seguir corriendo de todas formas para no dejar al usuario sin tray icon
        else:
            self.is_connected = True
            self.tray.update_status(True)

        # 2. Iniciar tareas concurrentes
        tasks = [
            asyncio.create_task(self.server.connect_websocket()),
            asyncio.create_task(self._metrics_loop()),
            asyncio.create_task(self._heartbeat_loop()),
        ]

        # 3. Iniciar tray icon (en thread separado, no bloquea el event loop)
        self.tray.start()

        logger.info("✅ Agente iniciado correctamente")

        # Esperar hasta que se llame stop()
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

                # También actualizar métricas de sesiones activas
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
        """Recolecta todas las métricas locales"""
        adspower_stats = self.adspower.get_process_stats()
        net_stats = self.network.get_stats()
        sys_stats = self.network.get_system_stats()
        active_browsers = self.adspower.get_active_browsers()

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

    async def _on_open_browser_command(
        self,
        session_id: int,
        profile_id: str,
        target_url: str
    ):
        """El servidor ordena abrir un navegador"""
        logger.info(f"📥 Comando open_browser: sesión={session_id}, perfil={profile_id}")

        # Resetear contador de red para esta sesión
        self.network.reset_session()

        # Abrir navegador
        result = await self.launcher.launch(
            session_id=session_id,
            profile_id=profile_id,
            target_url=target_url,
            on_navigation=self._on_navigation,
            on_close=self._on_browser_close,
            on_error=self._on_browser_error
        )

        if result.get("success"):
            # Confirmar al servidor
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