# app/core/connection_manager.py
from fastapi import WebSocket
from typing import Dict, List, Optional
import json
from loguru import logger
from datetime import datetime, timezone
import asyncio


def _utcnow_iso() -> str:
    """
    TIMEZONE FIX: datetime.utcnow().isoformat() genera '2026-03-04T23:00:00'
    sin zona horaria. El browser lo interpreta como hora LOCAL → uptime negativo
    en clientes que no están en UTC.
    Esta función siempre agrega 'Z' para que el browser lo trate como UTC.
    """
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


class ConnectionManager:
    def __init__(self):
        self.agent_connections: Dict[int, WebSocket] = {}
        self.admin_connections: List[WebSocket] = []
        self.live_metrics: Dict[int, dict] = {}
        self.agent_logs: Dict[int, list] = {}
        self.connection_times: Dict[int, datetime] = {}
        self._pending_proxy_checks: dict[str, asyncio.Future] = {}

        MAX_LOGS = 100

    # ========================================
    # AGENTES
    # ========================================

    async def connect_agent(self, websocket: WebSocket, computer_id: int):
        await websocket.accept()
        self.agent_connections[computer_id] = websocket

        if computer_id not in self.connection_times:
            self.connection_times[computer_id] = datetime.now(timezone.utc)

        logger.info(f"✅ Agente conectado: computer_id={computer_id}")
        asyncio.create_task(self._update_computer_status(computer_id, "online"))

        await self.broadcast_to_admins({
            "type":            "agent_online",
            "computer_id":     computer_id,
            # FIX: timestamp con Z explícita → browser lo parsea como UTC
            "connected_since": self.connection_times[computer_id].strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
            "timestamp":       _utcnow_iso(),
        })

    def disconnect_agent(self, computer_id: int):
        if computer_id in self.agent_connections:
            del self.agent_connections[computer_id]
            logger.info(f"❌ Agente desconectado: computer_id={computer_id}")

        if computer_id in self.live_metrics:
            del self.live_metrics[computer_id]

        self.connection_times.pop(computer_id, None)

        asyncio.create_task(self._update_computer_status(computer_id, "offline"))
        asyncio.create_task(self.broadcast_to_admins({
            "type":        "agent_offline",
            "computer_id": computer_id,
            "timestamp":   _utcnow_iso(),
        }))

    def get_connected_since(self, computer_id: int) -> Optional[datetime]:
        return self.connection_times.get(computer_id)

    async def _update_computer_status(self, computer_id: int, status: str):
        try:
            from app.database import AsyncSessionLocal
            from app.models.computer import Computer, ComputerStatus
            from sqlalchemy import update

            status_map = {
                "online":  ComputerStatus.ONLINE,
                "offline": ComputerStatus.OFFLINE,
            }

            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(Computer)
                    .where(Computer.id == computer_id)
                    .values(
                        status=status_map[status],
                        last_seen_at=datetime.now(timezone.utc) if status == "online" else Computer.last_seen_at
                    )
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Error actualizando status de computer {computer_id}: {e}")

    def is_agent_online(self, computer_id: int) -> bool:
        return computer_id in self.agent_connections

    async def send_command_to_agent(self, computer_id: int, command: str, payload: dict) -> bool:
        if computer_id not in self.agent_connections:
            logger.warning(f"⚠️ Agente {computer_id} no conectado")
            return False

        ws = self.agent_connections[computer_id]
        try:
            await ws.send_json({"command": command, **payload})
            return True
        except Exception as e:
            logger.error(f"Error enviando comando a agente {computer_id}: {e}")
            self.disconnect_agent(computer_id)
            return False

    async def handle_agent_message(self, computer_id: int, data: dict):
        msg_type = data.get("type")

        if msg_type == "metrics":
            metrics_data = data.get("data", {})
            self.live_metrics[computer_id] = {
                **metrics_data,
                "last_update": _utcnow_iso()
            }

            asyncio.create_task(self._save_metrics_to_db(computer_id, metrics_data))

            await self.broadcast_to_admins({
                "type":        "agent_metrics",
                "computer_id": computer_id,
                "data":        metrics_data,
            })

        elif msg_type == "browser_event":
            await self.broadcast_to_admins({
                "type":        "browser_event",
                "computer_id": computer_id,
                "data":        data.get("data")
            })

        elif msg_type == "session_update":
            await self.broadcast_to_admins({
                "type":        "session_update",
                "computer_id": computer_id,
                "data":        data.get("data")
            })

        elif msg_type == "heartbeat":
            if computer_id in self.agent_connections:
                await self.agent_connections[computer_id].send_json({
                    "type":      "pong",
                    "timestamp": _utcnow_iso(),
                })

    # ========================================
    # ADMINS
    # ========================================

    async def connect_admin(self, websocket: WebSocket):
        await websocket.accept()
        self.admin_connections.append(websocket)
        logger.info(f"✅ Admin conectado. Total: {len(self.admin_connections)}")

        try:
            await websocket.send_json({
                "type":      "connected",
                "message":   "Admin WebSocket conectado",
                "timestamp": _utcnow_iso(),
            })
        except Exception:
            self.admin_connections.remove(websocket)
            return

    def disconnect_admin(self, websocket: WebSocket):
        if websocket in self.admin_connections:
            self.admin_connections.remove(websocket)
        logger.info(f"❌ Admin desconectado. Total: {len(self.admin_connections)}")

    async def broadcast_to_admins(self, message: dict):
        disconnected = []
        for ws in self.admin_connections:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect_admin(ws)

    def get_live_metrics(self, computer_id: Optional[int] = None) -> dict:
        if computer_id:
            return self.live_metrics.get(computer_id, {})
        return self.live_metrics

    async def _save_metrics_to_db(self, computer_id: int, metrics: dict):
        try:
            from app.database import AsyncSessionLocal
            from app.models.health_check import HealthCheck

            sys_stats = metrics.get("system", metrics)
            memory = (
                sys_stats.get("memory_percent") or
                sys_stats.get("ram_percent")    or
                sys_stats.get("mem_percent")    or
                sys_stats.get("memory_usage")   or 0
            )

            if memory == 0:
                return

            async with AsyncSessionLocal() as db:
                check = HealthCheck(
                    computer_id=     computer_id,
                    is_healthy=      True,
                    cpu_usage=       sys_stats.get("cpu_percent") or sys_stats.get("cpu") or 0,
                    memory_usage=    memory,
                    disk_usage=      sys_stats.get("disk_percent") or sys_stats.get("disk") or 0,
                    active_profiles= metrics.get("active_browsers_count", 0),
                    adspower_status= "online" if metrics.get("adspower_running") else "offline",
                    checks_details=  metrics,
                    errors=[]
                )
                db.add(check)
                await db.commit()
        except Exception as e:
            logger.error(f"Error guardando métricas de computer {computer_id}: {e}")

    async def add_agent_log(self, computer_id: int, level: str, message: str):
        if computer_id not in self.agent_logs:
            self.agent_logs[computer_id] = []

        log_entry = {
            "timestamp": _utcnow_iso(),
            "level":     level,
            "message":   message,
        }

        self.agent_logs[computer_id].append(log_entry)
        if len(self.agent_logs[computer_id]) > 100:
            self.agent_logs[computer_id] = self.agent_logs[computer_id][-100:]

        await self.broadcast_to_admins({
            "type":        "agent_log",
            "computer_id": computer_id,
            "log":         log_entry,
        })

    def get_agent_logs(self, computer_id: int) -> list:
        return self.agent_logs.get(computer_id, [])



    def get_online_agents(self) -> set[int]:
        """Retorna computer_ids de agentes conectados"""
        return set(self.agent_connections.keys())

    # Método nuevo:
    async def request_proxy_check(
        self,
        computer_id: int,
        proxy_id: int,
        proxy_host: str,
        proxy_port: int,
        proxy_user: str,
        proxy_password: str,
        timeout: float = 15.0
    ) -> dict | None:
        """
        Envía check_proxy al agente y espera la respuesta.
        Retorna {"latency_ms": int|None, "error": str|None} o None si timeout.
        """
        import uuid
        request_id = str(uuid.uuid4())
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        self._pending_proxy_checks[request_id] = future

        sent = await self.send_command_to_agent(computer_id, "check_proxy", {
            "request_id":    request_id,
            "proxy_id":      proxy_id,
            "proxy_host":    proxy_host,
            "proxy_port":    proxy_port,
            "proxy_user":    proxy_user,
            "proxy_password": proxy_password,
        })

        if not sent:
            del self._pending_proxy_checks[request_id]
            return None

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            self._pending_proxy_checks.pop(request_id, None)
            return None

    def resolve_proxy_check(self, request_id: str, result: dict):
        """Llamado cuando llega proxy_check_result desde el agente."""
        future = self._pending_proxy_checks.pop(request_id, None)
        if future and not future.done():
            future.set_result(result)


connection_manager = ConnectionManager()