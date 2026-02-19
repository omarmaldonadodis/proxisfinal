# app/core/connection_manager.py
from fastapi import WebSocket
from typing import Dict, List, Optional
import json
from loguru import logger
from datetime import datetime


class ConnectionManager:
    """
    Gestiona conexiones WebSocket:
    - Agentes (ejecutables en cada computadora)
    - Admins (panel web)
    """

    def __init__(self):
        # computer_id -> WebSocket del ejecutable
        self.agent_connections: Dict[int, WebSocket] = {}

        # Lista de WebSockets de admins conectados al panel
        self.admin_connections: List[WebSocket] = []

        # Métricas en vivo por computadora
        self.live_metrics: Dict[int, dict] = {}

    # ========================================
    # AGENTES
    # ========================================

    async def connect_agent(self, websocket: WebSocket, computer_id: int):
        await websocket.accept()
        self.agent_connections[computer_id] = websocket
        logger.info(f"✅ Agente conectado: computer_id={computer_id}")

        # Notificar a admins que este agente está online
        await self.broadcast_to_admins({
            "type": "agent_online",
            "computer_id": computer_id,
            "timestamp": datetime.utcnow().isoformat()
        })

    def disconnect_agent(self, computer_id: int):
        if computer_id in self.agent_connections:
            del self.agent_connections[computer_id]
            logger.info(f"❌ Agente desconectado: computer_id={computer_id}")

        if computer_id in self.live_metrics:
            del self.live_metrics[computer_id]

    def is_agent_online(self, computer_id: int) -> bool:
        return computer_id in self.agent_connections

    async def send_command_to_agent(
        self,
        computer_id: int,
        command: str,
        payload: dict
    ) -> bool:
        """Envía un comando al ejecutable de una computadora"""
        if computer_id not in self.agent_connections:
            logger.warning(f"⚠️ Agente {computer_id} no conectado")
            return False

        ws = self.agent_connections[computer_id]
        try:
            await ws.send_json({
                "command": command,
                **payload
            })
            logger.info(f"📤 Comando '{command}' enviado a agente {computer_id}")
            return True
        except Exception as e:
            logger.error(f"Error enviando comando a agente {computer_id}: {e}")
            self.disconnect_agent(computer_id)
            return False

    async def handle_agent_message(self, computer_id: int, data: dict):
        """Procesa mensajes entrantes del ejecutable"""
        msg_type = data.get("type")

        if msg_type == "metrics":
            # Guardar métricas en vivo
            self.live_metrics[computer_id] = {
                **data.get("data", {}),
                "last_update": datetime.utcnow().isoformat()
            }
            # Reenviar a admins
            await self.broadcast_to_admins({
                "type": "agent_metrics",
                "computer_id": computer_id,
                "data": data.get("data")
            })

        elif msg_type == "browser_event":
            await self.broadcast_to_admins({
                "type": "browser_event",
                "computer_id": computer_id,
                "data": data.get("data")
            })

        elif msg_type == "session_update":
            await self.broadcast_to_admins({
                "type": "session_update",
                "computer_id": computer_id,
                "data": data.get("data")
            })

        elif msg_type == "heartbeat":
            # Responder con pong
            if computer_id in self.agent_connections:
                await self.agent_connections[computer_id].send_json({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })

    # ========================================
    # ADMINS
    # ========================================

    async def connect_admin(self, websocket: WebSocket):
        await websocket.accept()
        self.admin_connections.append(websocket)
        logger.info(f"✅ Admin conectado. Total admins: {len(self.admin_connections)}")

        # Enviar estado actual al nuevo admin
        await websocket.send_json({
            "type": "initial_state",
            "online_agents": list(self.agent_connections.keys()),
            "live_metrics": self.live_metrics
        })

    def disconnect_admin(self, websocket: WebSocket):
        if websocket in self.admin_connections:
            self.admin_connections.remove(websocket)

    async def broadcast_to_admins(self, message: dict):
        """Envía mensaje a todos los admins conectados"""
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


connection_manager = ConnectionManager()