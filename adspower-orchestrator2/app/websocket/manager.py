# app/websocket/manager.py
from typing import Dict, List, Optional
from fastapi import WebSocket
from loguru import logger
import json
import asyncio
from datetime import datetime

class ConnectionManager:
    """Gestor de conexiones WebSocket para agentes (Computadoras B)"""
    
    def __init__(self):
        # computer_id -> WebSocket
        self.active_connections: Dict[int, WebSocket] = {}
        # computer_id -> última actividad
        self.last_activity: Dict[int, datetime] = {}
        # computer_id -> estado del agente
        self.agent_states: Dict[int, Dict] = {}
    
    async def connect(self, websocket: WebSocket, computer_id: int):
        """Conecta un agente"""
        await websocket.accept()
        self.active_connections[computer_id] = websocket
        self.last_activity[computer_id] = datetime.utcnow()
        
        logger.info(f"Agent connected: Computer {computer_id}")
        
        # Enviar mensaje de bienvenida
        await self.send_message(computer_id, {
            "type": "connected",
            "computer_id": computer_id,
            "message": "Connected to orchestrator",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def disconnect(self, computer_id: int):
        """Desconecta un agente"""
        if computer_id in self.active_connections:
            del self.active_connections[computer_id]
        if computer_id in self.last_activity:
            del self.last_activity[computer_id]
        if computer_id in self.agent_states:
            del self.agent_states[computer_id]
        
        logger.info(f"Agent disconnected: Computer {computer_id}")
    
    async def send_message(self, computer_id: int, message: Dict):
        """Envía mensaje a un agente específico"""
        if computer_id in self.active_connections:
            try:
                websocket = self.active_connections[computer_id]
                await websocket.send_json(message)
                self.last_activity[computer_id] = datetime.utcnow()
                return True
            except Exception as e:
                logger.error(f"Error sending message to computer {computer_id}: {e}")
                self.disconnect(computer_id)
                return False
        return False
    
    async def broadcast(self, message: Dict):
        """Envía mensaje a todos los agentes conectados"""
        disconnected = []
        
        for computer_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
                self.last_activity[computer_id] = datetime.utcnow()
            except Exception as e:
                logger.error(f"Error broadcasting to computer {computer_id}: {e}")
                disconnected.append(computer_id)
        
        # Limpiar conexiones fallidas
        for computer_id in disconnected:
            self.disconnect(computer_id)
    
    async def execute_warming(
        self,
        computer_id: int,
        execution_id: int,
        profile_id: str,  # ✅ CAMBIAR: Ahora es adspower_id (string)
        script_actions: List[Dict]
    ) -> bool:
        """Ejecuta warming en un agente"""
        
        command = {
            "type": "execute_warming",
            "execution_id": execution_id,
            "profile_id": profile_id,  # ✅ Ahora envía adspower_id
            "actions": script_actions,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        success = await self.send_message(computer_id, command)
        
        if success:
            logger.info(f"Warming command sent: Execution {execution_id}, Computer {computer_id}")
        else:
            logger.error(f"Failed to send warming command to Computer {computer_id}")
        
        return success
    
    async def stop_warming(self, computer_id: int, execution_id: int) -> bool:
        """Detiene warming en ejecución"""
        
        command = {
            "type": "stop_warming",
            "execution_id": execution_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return await self.send_message(computer_id, command)
    
    async def request_status(self, computer_id: int) -> bool:
        """Solicita estado del agente"""
        
        command = {
            "type": "status_request",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return await self.send_message(computer_id, command)
    
    def update_agent_state(self, computer_id: int, state: Dict):
        """Actualiza estado del agente"""
        self.agent_states[computer_id] = {
            **state,
            "last_updated": datetime.utcnow()
        }
    
    def get_agent_state(self, computer_id: int) -> Optional[Dict]:
        """Obtiene estado del agente"""
        return self.agent_states.get(computer_id)
    
    def get_connected_agents(self) -> List[int]:
        """Lista de computer_ids conectados"""
        return list(self.active_connections.keys())
    
    def is_connected(self, computer_id: int) -> bool:
        """Verifica si agente está conectado"""
        return computer_id in self.active_connections
    
    async def heartbeat_monitor(self):
        """Monitor de heartbeat (ejecutar en background)"""
        while True:
            await asyncio.sleep(30)  # Cada 30 segundos
            
            now = datetime.utcnow()
            timeout_seconds = 60
            
            disconnected = []
            
            for computer_id, last_activity in self.last_activity.items():
                if (now - last_activity).total_seconds() > timeout_seconds:
                    logger.warning(f"Agent timeout: Computer {computer_id}")
                    disconnected.append(computer_id)
            
            for computer_id in disconnected:
                self.disconnect(computer_id)

# Instancia global
connection_manager = ConnectionManager()