# agent/browser_launcher.py
"""
Abre un navegador AdsPower con un perfil específico,
navega a la URL asignada y monitorea lo que ocurre dentro.

MONITOREO: usa CDP /json (polling todas las pestañas)
en lugar de Selenium driver.current_url (solo pestaña activa).

FIX 1: filtra chrome://, about:*, etc. de tracking de navegación de usuario
FIX 2: detección rápida de cierre via /json/version (timeout 2s, 2 fallos = cerrado)
FIX 3: navega explícitamente a target_url via CDP si el browser arranca en about:blank
"""
import asyncio
import json
import time
import httpx
import websockets
from typing import Optional, Callable, Dict, Set
from loguru import logger

from agent.adspower_monitor import AdsPowerMonitor


# URLs internas del navegador que NO se deben registrar como navegación del usuario
_INTERNAL_URL_PREFIXES = (
    "chrome://",
    "chrome-extension://",
    "devtools://",
    "about:",
    "data:",
)


def _is_internal_url(url: str) -> bool:
    """Retorna True si la URL es interna del navegador (no acción del usuario)."""
    if not url:
        return True
    return any(url.startswith(prefix) for prefix in _INTERNAL_URL_PREFIXES)


# ──────────────────────────────────────────────────────────────────────────────
# CDP NAVIGATE HELPER
# ──────────────────────────────────────────────────────────────────────────────

# DESPUÉS — compatible con Python 3.8+
# REEMPLAZAR la función completa
async def _cdp_navigate(ws_url: str, target_url: str, timeout: float = 8.0) -> bool:
    """
    Navega via CDP esperando correctamente la respuesta con id=1.
    Compatible con Python 3.8+ (usa asyncio.wait_for en vez de asyncio.timeout).
    """
    try:
        async def _do():
            async with websockets.connect(ws_url, ping_interval=None, open_timeout=6) as ws:
                # 1. Habilitar el dominio Page (necesario en algunos builds de Chrome/Mac)
                await ws.send(json.dumps({"id": 0, "method": "Page.enable"}))

                # 2. Enviar navigate
                await ws.send(json.dumps({
                    "id": 1,
                    "method": "Page.navigate",
                    "params": {"url": target_url}
                }))

                # 3. Esperar la respuesta con id=1 (ignorar eventos intermedios)
                for _ in range(10):   # máximo 10 mensajes antes de rendirse
                    raw = await asyncio.wait_for(ws.recv(), timeout=3.0)
                    msg = json.loads(raw)
                    if msg.get("id") == 1:
                        # Verificar que no hubo error en la navegación
                        err = msg.get("result", {}).get("errorText")
                        if err:
                            logger.warning(f"CDP navigate error: {err}")
                        return True
                return False

        await asyncio.wait_for(_do(), timeout=timeout)
        return True

    except Exception as e:
        logger.debug(f"_cdp_navigate error: {e}")
        return False

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

        # { target_id: last_url } — rastrea la última URL conocida por pestaña
        self._known_urls: Dict[str, str] = {}

        # Callbacks
        self.on_navigation: Optional[Callable] = None
        self.on_close:      Optional[Callable] = None
        self.on_error:      Optional[Callable] = None


class BrowserLauncher:

    def __init__(self, adspower_monitor: AdsPowerMonitor, api_key: Optional[str] = None):
        self.monitor = adspower_monitor
        self.active_sessions: Dict[int, BrowserSession] = {}
        self.api_key = api_key

    # ──────────────────────────────────────────────────────────────────────────
    # LAUNCH
    # ──────────────────────────────────────────────────────────────────────────

    async def launch(
        self,
        session_id: int,
        profile_id: str,
        target_url: str,
        on_navigation: Optional[Callable] = None,
        on_close:      Optional[Callable] = None,
        on_error:      Optional[Callable] = None
    ) -> Dict:
        logger.info(
            f"🚀 Abriendo navegador: perfil={profile_id}, "
            f"url={target_url}, sesión={session_id}"
        )

        loop = asyncio.get_event_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self.monitor.open_browser(profile_id, target_url)
                ),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            error_msg = "Timeout: AdsPower no respondió en 30 segundos"
            logger.error(
                f"❌ {error_msg} — perfil={profile_id}, sesión={session_id}")
            if on_error:
                await on_error(session_id, error_msg)
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"Error inesperado al contactar AdsPower: {e}"
            logger.error(f"❌ {error_msg}")
            if on_error:
                await on_error(session_id, error_msg)
            return {"success": False, "error": error_msg}

        if not result.get("success"):
            error_msg = result.get("error", "Error desconocido")
            logger.error(f"❌ Error abriendo navegador: {error_msg}")
            if on_error:
                await on_error(session_id, error_msg)
            return {"success": False, "error": error_msg}

        # Extraer debug_address para CDP
        selenium_ws = result.get("selenium", "")
        debug_address = None
        if selenium_ws:
            debug_address = selenium_ws.replace(
                "ws://", "").split("/devtools/")[0]

        # Crear sesión
        session = BrowserSession(
            session_id, profile_id, target_url, self.monitor)
        session.on_navigation = on_navigation
        session.on_close = on_close
        session.on_error = on_error
        session.is_running = True
        session.opened_at = time.time()
        session._debug_address = debug_address

        self.active_sessions[session_id] = session

        asyncio.create_task(self._monitor_session(session))

        logger.info(
            f"✅ Navegador abierto: sesión={session_id}, CDP={debug_address}")
        return {"success": True, "session_id": session_id}

    # ──────────────────────────────────────────────────────────────────────────
    # MONITOR PRINCIPAL — CDP polling
    # ──────────────────────────────────────────────────────────────────────────

    async def _monitor_session(self, session: BrowserSession):
        """
        Bucle de monitoreo usando dos endpoints CDP:

        1. GET /json/version  → detecta si Chrome sigue vivo (timeout 2s)
           - 2 fallos consecutivos = navegador cerrado
           - Tiempo de detección: ~4-6s (vs los ~27s anteriores)

        2. GET /json          → obtiene todas las pestañas y sus URLs
           - Filtra URLs internas (chrome://, about:*, etc.)
           - Solo reporta URLs reales como navegación del usuario
        """
        CHECK_INTERVAL = 2    # segundos entre polls normales
        VERSION_TIMEOUT = 2.0  # timeout para /json/version
        TARGETS_TIMEOUT = 4.0  # timeout para /json
        MAX_CONSECUTIVE_ERRORS = 2    # fallos antes de declarar cerrado

        debug_address = getattr(session, '_debug_address', None)

        if not debug_address:
            logger.warning(
                f"⚠️ Sesión {session.session_id}: sin debug_address CDP. "
                f"Usando polling básico de AdsPower API."
            )
            await self._monitor_session_fallback(session)
            return

        logger.info(
            f"🔍 Monitor CDP activo: sesión={session.session_id}, addr={debug_address}"
        )

        consecutive_errors = 0

        # Espera a que Chrome arranque y fuerza navegación si está en about:blank
# DESPUÉS
        import platform as _platform

        # Mac necesita más tiempo para que Chrome registre sus targets en CDP
        _startup_wait = 4.0 if _platform.system() == "Darwin" else 3.5  # Windows necesita más
        await asyncio.sleep(_startup_wait)
        await self._ensure_navigated(session, debug_address, TARGETS_TIMEOUT)

        while session.is_running:
            try:
                # 1. ¿Sigue vivo el proceso Chrome?
                alive = await self._is_browser_alive(debug_address, VERSION_TIMEOUT)

                if not alive:
                    consecutive_errors += 1
                    if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                        logger.info(
                            f"🔴 Navegador cerrado (CDP no responde): "
                            f"sesión={session.session_id}"
                        )
                        await self._handle_browser_closed(session)
                        break
                    # Reintento rápido
                    await asyncio.sleep(1)
                    continue

                # Chrome vivo → reset contador de errores
                consecutive_errors = 0

                # 2. Obtener todas las pestañas y detectar navegación
                targets = await self._get_all_page_targets(debug_address, TARGETS_TIMEOUT)
                if targets is not None:
                    await self._process_targets(session, targets)

            except asyncio.CancelledError:
                break
            except Exception as e:
                consecutive_errors += 1
                logger.debug(
                    f"Error inesperado monitor sesión {session.session_id}: {e} "
                    f"(consecutivos: {consecutive_errors})"
                )
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    logger.error(
                        f"❌ Demasiados errores sesión {session.session_id}, "
                        f"cerrando monitor"
                    )
                    if session.on_error:
                        await session.on_error(
                            session.session_id, f"Error de monitoreo: {e}"
                        )
                    await self._handle_browser_closed(session)
                    break

            await asyncio.sleep(CHECK_INTERVAL)

    # ──────────────────────────────────────────────────────────────────────────
    # CDP HELPERS
    # ──────────────────────────────────────────────────────────────────────────

    async def _ensure_navigated(
        self,
        session: BrowserSession,
        debug_address: str,
        timeout: float
    ):
        import platform as _platform

        max_attempts = 4 if _platform.system() == "Darwin" else 4 
        retry_delay  = 1.5

        for attempt in range(max_attempts):
            targets = await self._get_all_page_targets(debug_address, timeout)

            if not targets:
                # Chrome aún no registró sus targets — esperar y reintentar
                logger.debug(
                    f"Sesión {session.session_id}: sin targets CDP "
                    f"(intento {attempt + 1}/{max_attempts}), esperando {retry_delay}s..."
                )
                await asyncio.sleep(retry_delay)
                continue

            for target in targets:
                url    = target.get("url", "")
                ws_url = target.get("webSocketDebuggerUrl", "")

                if _is_internal_url(url) and ws_url:
                    logger.info(
                        f"🔀 Sesión {session.session_id}: pestaña en '{url}', "
                        f"navegando a {session.target_url} (intento {attempt + 1})"
                    )
                    ok = await _cdp_navigate(ws_url, session.target_url)
                    if ok:
                        logger.info(
                            f"✅ Navegación forzada enviada: sesión={session.session_id}"
                        )
                        return  # éxito
                    else:
                        logger.warning(
                            f"⚠️ CDP navigate falló, reintentando... sesión={session.session_id}"
                        )
                        await asyncio.sleep(retry_delay)
                        break  # ir al siguiente intento del for externo
            else:
                # Todos los targets ya tienen URL real — no hace falta navegar
                return

        logger.warning(
            f"⚠️ _ensure_navigated agotó intentos para sesión {session.session_id}"
        )

    async def _is_browser_alive(self, debug_address: str, timeout: float) -> bool:
        """
        Consulta /json/version para saber si el proceso Chrome sigue corriendo.
        Este endpoint responde aunque no haya pestañas con URLs reales.
        Falla inmediatamente si Chrome fue cerrado (conexión rechazada).
        """
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.get(f"http://{debug_address}/json/version")
                return r.status_code == 200
        except Exception:
            return False

    async def _get_all_page_targets(
        self, debug_address: str, timeout: float
    ) -> Optional[list]:
        """
        Consulta /json y retorna todos los targets de tipo 'page'.
        Incluye pestañas internas (chrome://newtab/) para rastrear su existencia,
        pero el filtrado de navegación ocurre en _process_targets.
        """
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.get(f"http://{debug_address}/json")
                if r.status_code != 200:
                    return None
                all_targets = r.json()
                return [
                    t for t in all_targets
                    if t.get("type") == "page"
                    and not t.get("url", "").startswith("chrome-extension://")
                    and not t.get("url", "").startswith("devtools://")
                ]
        except Exception:
            return None

    async def _process_targets(self, session: BrowserSession, targets: list):
        """
        Para cada pestaña detecta si la URL cambió desde el último poll.

        IMPORTANTE — dos listas separadas:
        - _known_urls: rastrea TODAS las pestañas (incluye chrome://) para
          detectar cierres de pestañas correctamente.
        - Navegación reportada: SOLO URLs reales (no chrome://, no about:*).

        Esto evita que chrome://newtab/ aparezca en el historial de páginas
        visitadas del usuario.
        """
        seen_ids: Set[str] = set()

        for target in targets:
            target_id = target.get("id", "")
            url = target.get("url", "").strip()
            title = target.get("title", "").strip()

            if not target_id:
                continue

            seen_ids.add(target_id)
            last_url = session._known_urls.get(target_id)

            if url == last_url:
                continue  # Sin cambio

            # Actualizar URL conocida siempre (para detectar futuros cambios)
            session._known_urls[target_id] = url

            # Solo reportar como navegación si es URL real del usuario
            if _is_internal_url(url):
                logger.debug(
                    f"[sesión={session.session_id}] pestaña={target_id[:8]} "
                    f"URL interna (no registrada): {url}"
                )
                continue

            # URL real → registrar
            session.current_url = url
            session.pages_visited += 1

            logger.debug(
                f"🌐 [sesión={session.session_id}] pestaña={target_id[:8]} → {url}"
            )

            if session.on_navigation:
                await session.on_navigation(session.session_id, url, title)

        # Limpiar pestañas que fueron cerradas
        closed_tabs = set(session._known_urls.keys()) - seen_ids
        for closed_id in closed_tabs:
            del session._known_urls[closed_id]
            logger.debug(
                f"🗑️ Pestaña cerrada en sesión {session.session_id}: {closed_id[:8]}"
            )

    # ──────────────────────────────────────────────────────────────────────────
    # FALLBACK — sin CDP
    # ──────────────────────────────────────────────────────────────────────────

    async def _monitor_session_fallback(self, session: BrowserSession):
        """Fallback cuando no hay endpoint CDP: solo detecta cierre."""
        logger.warning(
            f"⚠️ Sesión {session.session_id}: modo fallback (sin CDP)."
        )
        while session.is_running:
            try:
                status = self.monitor.get_browser_status(session.profile_id)
                if not status.get("is_running"):
                    logger.info(
                        f"🔴 Navegador cerrado (fallback): sesión={session.session_id}"
                    )
                    await self._handle_browser_closed(session)
                    break
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Error en fallback monitor: {e}")
            await asyncio.sleep(3)

    # ──────────────────────────────────────────────────────────────────────────
    # CIERRE
    # ──────────────────────────────────────────────────────────────────────────

    async def _handle_browser_closed(self, session: BrowserSession):
        if not session.is_running:
            return
        session.is_running = False
        self.active_sessions.pop(session.session_id, None)

        if session.on_close:
            await session.on_close(
                session.session_id,
                {
                    "pages_visited":    session.pages_visited,
                    "duration_seconds": int(
                        time.time() - (session.opened_at or time.time())
                    )
                }
            )

    async def close_browser(self, session_id: int) -> bool:
        session = self.active_sessions.get(session_id)
        if not session:
            return False

        logger.info(f"⏹️ Cerrando navegador: sesión={session_id}")
        self.monitor.close_browser(session.profile_id)
        session.is_running = False
        self.active_sessions.pop(session_id, None)
        return True

    def get_active_count(self) -> int:
        return len(self.active_sessions)
