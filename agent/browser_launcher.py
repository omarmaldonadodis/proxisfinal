# agent/browser_launcher.py
"""
Abre un navegador AdsPower con un perfil específico,
navega a la URL asignada y monitorea lo que ocurre dentro.
Usa Selenium CDP para detectar navegación.
"""
import asyncio
import time
from typing import Optional, Callable, Dict
from loguru import logger

from agent.adspower_monitor import AdsPowerMonitor


class BrowserSession:
    """Representa una sesión de navegador activa"""

    def __init__(
        self,
        session_id: int,
        profile_id: str,
        target_url: str,
        monitor: AdsPowerMonitor
    ):
        self.session_id = session_id
        self.profile_id = profile_id
        self.target_url = target_url
        self.monitor = monitor

        self.driver = None
        self.is_running = False
        self.pages_visited = 0
        self.opened_at = None
        self.current_url = ""

        # Callbacks
        self.on_navigation: Optional[Callable] = None
        self.on_close: Optional[Callable] = None
        self.on_error: Optional[Callable] = None


class BrowserLauncher:

    def __init__(self, adspower_monitor: AdsPowerMonitor, api_key: Optional[str] = None):
        self.monitor = adspower_monitor
        self.active_sessions: Dict[int, BrowserSession] = {}
        self.api_key = api_key

    async def launch(
        self,
        session_id: int,
        profile_id: str,
        target_url: str,
        on_navigation: Optional[Callable] = None,
        on_close: Optional[Callable] = None,
        on_error: Optional[Callable] = None
    ) -> Dict:
        """
        Abre AdsPower con el perfil dado y navega a target_url.
        Inicia monitoreo en background.
        """
        logger.info(
            f"🚀 Abriendo navegador: perfil={profile_id}, "
            f"url={target_url}, sesión={session_id}"
        )

        # 1. Abrir via AdsPower API
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self.monitor.open_browser(profile_id, target_url)
        )
        if not result.get("success"):
            error_msg = result.get("error", "Error desconocido")
            logger.error(f"❌ Error abriendo navegador: {error_msg}")
            if on_error:
                await on_error(session_id, error_msg)
            return {"success": False, "error": error_msg}

        # 2. Crear sesión
        session = BrowserSession(session_id, profile_id, target_url, self.monitor)
        session.on_navigation = on_navigation
        session.on_close = on_close
        session.on_error = on_error
        session.is_running = True
        session.opened_at = time.time()

        # 3. Conectar Selenium si hay endpoint disponible
        selenium_ws = result.get("selenium")
        webdriver_path = result.get("webdriver")

        if selenium_ws and webdriver_path:
            try:
                await asyncio.wait_for(
                    self._connect_selenium(session, selenium_ws, webdriver_path),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                logger.warning("⚠️ Timeout conectando Selenium, continuando sin él")
                session.driver = None        
        else:
            logger.warning(
                "⚠️ Sin endpoint Selenium, usando polling básico de AdsPower API"
            )

        self.active_sessions[session_id] = session

        # 4. Iniciar monitoreo en background
        asyncio.create_task(self._monitor_session(session))

        logger.info(f"✅ Navegador abierto correctamente: sesión={session_id}")
        return {"success": True, "session_id": session_id}

    async def _connect_selenium(self, session, selenium_ws, webdriver_path):
        try:
            from selenium import webdriver as wd
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service

            debug_address = (
                selenium_ws.replace("ws://", "").split("/devtools/")[0]
            )

            loop = asyncio.get_event_loop()

            def _init_driver():
                options = Options()
                options.add_experimental_option("debuggerAddress", debug_address)
                service = Service(executable_path=webdriver_path)
                driver = wd.Chrome(service=service, options=options)
                if session.target_url and session.target_url != "about:blank":
                    driver.get(session.target_url)
                return driver

            # Ejecutar en thread pool — evita bloquear el event loop
            session.driver = await loop.run_in_executor(None, _init_driver)
            logger.info(f"✅ Selenium conectado: {debug_address}")

        except Exception as e:
            logger.warning(f"⚠️ No se pudo conectar Selenium: {e}. Usando polling.")
            session.driver = None

    async def _monitor_session(self, session: BrowserSession):
        """
        Loop de monitoreo: detecta navegación y cierre del navegador.
        Si hay Selenium usa driver.current_url.
        Si no, usa AdsPower API polling.
        """
        last_url = session.target_url
        check_interval = 2  # segundos

        while session.is_running:
            try:
                if session.driver:
                    # Monitoreo via Selenium
                    try:
                        current_url = session.driver.current_url
                        current_title = session.driver.title

                        if current_url and current_url != last_url:
                            if session.on_navigation:
                                await session.on_navigation(
                                    session.session_id,
                                    current_url,
                                    current_title
                                )
                            last_url = current_url
                            session.current_url = current_url
                            session.pages_visited += 1

                    except Exception:
                        # El navegador fue cerrado
                        logger.info(
                            f"🔴 Navegador cerrado (Selenium): sesión={session.session_id}"
                        )
                        await self._handle_browser_closed(session)
                        break

                else:
                    # Monitoreo via AdsPower API polling
                    status = self.monitor.get_browser_status(session.profile_id)

                    if not status.get("is_running"):
                        logger.info(
                            f"🔴 Navegador cerrado (polling): sesión={session.session_id}"
                        )
                        await self._handle_browser_closed(session)
                        break

                await asyncio.sleep(check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error en monitor loop sesión {session.session_id}: {e}")
                await asyncio.sleep(check_interval)

    async def _handle_browser_closed(self, session: BrowserSession):
        if not session.is_running:
            return   # ← ya fue procesado por otra coroutine, ignorar
        session.is_running = False
        self.active_sessions.pop(session.session_id, None)   # ← pop es seguro, no lanza KeyError

        if session.on_close:
            await session.on_close(
                session.session_id,
                {
                    "pages_visited":    session.pages_visited,
                    "duration_seconds": int(time.time() - (session.opened_at or time.time()))
                }
            )

    async def close_browser(self, session_id: int) -> bool:
        """Cierra un navegador por session_id"""
        session = self.active_sessions.get(session_id)
        if not session:
            return False

        logger.info(f"⏹️ Cerrando navegador: sesión={session_id}")

        # Cerrar via AdsPower API
        self.monitor.close_browser(session.profile_id)

        session.is_running = False
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]

        return True

    def get_active_count(self) -> int:
        return len(self.active_sessions)