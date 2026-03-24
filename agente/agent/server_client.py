# agent/server_client.py
"""
Maneja toda la comunicación con el servidor FastAPI:
- Registro de la computadora
- WebSocket persistente (recibir comandos, enviar métricas)
- HTTP para reportar eventos y cerrar sesiones
"""
import asyncio
import json
import platform
import httpx
from websockets.asyncio.client import connect as ws_connect
import psutil
from typing import Optional, Callable, Dict
from loguru import logger

from agent.config import AgentConfig


class ServerClient:

    def __init__(self, config: AgentConfig):
        self.config = config
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False

        self.on_open_browser:   Optional[Callable] = None
        self.on_close_browser:  Optional[Callable] = None
        self.on_create_profile: Optional[Callable] = None
        self.on_update_proxy:   Optional[Callable] = None 
        self.on_check_proxy: Optional[Callable] = None
        self.on_verify_profile: Optional[Callable] = None




    # ========================================
    # REGISTRO
    # ========================================

    async def register(self) -> bool:
        """
        Registra esta computadora en el servidor.
        Guarda el computer_id en config.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.config.server_url}/api/v1/agent/register",
                    json={
                        "name": self.config.agent_name or self.config.get_hostname(),
                        "hostname": self.config.get_hostname(),
                        "ip_address": self.config.get_local_ip(),
                        "adspower_api_url": self.config.adspower_url,
                        "adspower_api_key": "",
                        "os_info": f"{platform.system()} {platform.release()}",
                        "cpu_cores": psutil.cpu_count(),
                        "ram_gb": round(psutil.virtual_memory().total / (1024 ** 3))
                    },
                    headers={"X-Agent-Token": self.config.server_token}
                )

                if response.status_code == 200:
                    data = response.json()
                    self.config.computer_id = data.get("computer_id")
                    self.config.save()
                    logger.info(
                        f"✅ Registrado en servidor. "
                        f"Computer ID: {self.config.computer_id}"
                    )
                    return True
                else:
                    logger.error(
                        f"❌ Error registrando: {response.status_code} - {response.text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"❌ No se pudo conectar al servidor: {e}")
            return False

    # ========================================
    # WEBSOCKET
    # ========================================

    async def connect_websocket(self):
        """
        WebSocket persistente. Se reconecta automáticamente si se pierde la conexión.
        """
        ws_url = (
            f"{self.config.server_url.replace('http', 'ws')}"
            f"/api/v1/agent/ws/{self.config.computer_id}"
        )

        while True:
            try:
                logger.info(f"🔌 Conectando WebSocket a {ws_url}...")

                async with ws_connect(
                    ws_url,
                    additional_headers={
                        "X-Agent-Token": self.config.server_token},
                    ping_interval=30,
                    ping_timeout=10
                ) as ws:
                    self.ws = ws
                    self.is_connected = True
                    logger.info("✅ WebSocket conectado al servidor")

                    # Loop de recepción de mensajes
                    async for message in ws:
                        try:
                            data = json.loads(message)
                            await self._handle_command(data)
                        except json.JSONDecodeError:
                            logger.warning(f"Mensaje inválido: {message}")

            except websockets.exceptions.ConnectionClosed:
                logger.warning("⚠️ WebSocket cerrado. Reconectando en 5s...")
            except Exception as e:
                logger.warning(f"⚠️ Error WebSocket: {e}. Reconectando en 5s...")
            finally:
                self.ws = None
                self.is_connected = False

            await asyncio.sleep(5)

    async def _handle_command(self, data: dict):
        """Procesa comandos enviados por el servidor"""
        command = data.get("command")
        logger.info(f"📥 Comando recibido: {command}")

        if command == "open_browser":
            if self.on_open_browser:
                await self.on_open_browser(
                    session_id=data["session_id"],
                    profile_id=data["profile_id"],
                    target_url=data["target_url"]
                )

        elif command == "close_browser":
            if self.on_close_browser:
                await self.on_close_browser(
                    session_id=data["session_id"]
                )
        elif command == "create_adspower_profile":
            if self.on_create_profile:
                asyncio.create_task(self.on_create_profile(data))

        elif data.get("type") == "pong":
            logger.debug("Pong recibido del servidor")
        
        elif command == "update_proxy":
            if self.on_update_proxy:
                asyncio.create_task(self.on_update_proxy(data))
        
        elif command == "check_proxy":
            if self.on_check_proxy:
                asyncio.create_task(self.on_check_proxy(data))
        
        elif command == "verify_profile":
            if hasattr(self, 'on_verify_profile') and self.on_verify_profile:
                asyncio.create_task(self.on_verify_profile(data))
        

    # ========================================
    # ENVÍO DE DATOS
    # ========================================

    async def send_metrics(self, metrics: dict):
        """Envía métricas periódicas via WebSocket"""
        if self.ws and self.is_connected:
            try:
                await self.ws.send(json.dumps({
                    "type": "metrics",
                    "data": metrics
                }))
            except Exception as e:
                logger.debug(f"Error enviando métricas: {e}")

    async def mark_session_active(self, session_id: int) -> bool:
        """Confirma al servidor que el navegador se abrió — via WebSocket"""
        if self.ws and self.is_connected:
            try:
                await self.ws.send(json.dumps({
                    "type":       "session_opened",
                    "session_id": session_id,
                }))
                return True
            except Exception as e:
                logger.debug(f"Error marcando sesión activa: {e}")
        return False


    async def update_metrics(
        self,
        session_id: int,
        data_sent_mb: float = 0,
        data_received_mb: float = 0,
        pages_visited: int = 0,
        current_url: Optional[str] = None,
        browser_health: str = "healthy",
        cpu_percent: Optional[float] = None,
        ram_mb: Optional[float] = None
    ) -> bool:
        """Métricas de sesión — via WebSocket"""
        if self.ws and self.is_connected:
            try:
                await self.ws.send(json.dumps({
                    "type":       "session_metrics",
                    "session_id": session_id,
                    "data": {
                        "pages_visited":    pages_visited,
                        "total_data_mb":    data_sent_mb + data_received_mb,
                        "current_url":      current_url,
                        "browser_health":   browser_health,
                        "cpu_percent":      cpu_percent,
                        "memory_mb":        ram_mb,
                    }
                }))
                return True
            except Exception as e:
                logger.debug(f"Error enviando métricas: {e}")
        return False

    async def close_session(
        self,
        session_id: int,
        data_sent_mb: float,
        data_received_mb: float,
        pages_visited: int,
        crash_reason: Optional[str] = None
    ) -> bool:
        """Cierra sesión — via WebSocket"""
        if self.ws and self.is_connected:
            try:
                await self.ws.send(json.dumps({
                    "type":             "session_closed",
                    "session_id":       session_id,
                    "pages_visited":    pages_visited,
                    "total_data_mb":    data_sent_mb + data_received_mb,
                    "duration_seconds": None,  # el server lo calcula
                    "crash_reason":     crash_reason,
                }))
                return True
            except Exception as e:
                logger.debug(f"Error cerrando sesión: {e}")
        return False

    async def report_navigation(self, session_id: int, url: str, title: str) -> bool:
        """Reporta navegación — via WebSocket"""
        if self.ws and self.is_connected:
            try:
                await self.ws.send(json.dumps({
                    "type":       "page_visit",
                    "session_id": session_id,
                    "url":        url,
                    "title":      title,
                }))
                return True
            except Exception as e:
                logger.debug(f"Error reportando navegación: {e}")
        return False
    


    async def update_metrics(self, session_id: int, **kwargs) -> bool:
        """Métricas de sesión via WebSocket — type correcto para el backend"""
        if self.ws and self.is_connected:
            try:
                await self.ws.send(json.dumps({
                    "type":       "session_metrics",   # ← CORREGIDO: era "metrics"
                    "session_id": session_id,
                    "data":       kwargs,
                }))
                return True
            except Exception as e:
                logger.debug(f"Error enviando métricas de sesión: {e}")
        return False

    # ========================================
    # HELPER HTTP
    # ========================================

    async def _post(self, endpoint: str, payload: dict) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.config.server_url}{endpoint}",
                    json=payload,
                    headers={"X-Agent-Token": self.config.server_token}
                )
                return response.status_code == 200
        except Exception as e:
            logger.debug(f"Error HTTP {endpoint}: {e}")
            return False

    async def send_log(self, level: str, message: str):
        if self.ws and self.is_connected:
            try:
                await self.ws.send(json.dumps({
                    "type":    "log",
                    "level":   level,
                    "message": message,
                }))
            except Exception:
                pass