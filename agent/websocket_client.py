# agent/websocket_client.py (FIXED VERSION)
import asyncio
import websockets
import json
from loguru import logger
from datetime import datetime
from typing import Optional

class WebSocketClient:
    """Cliente WebSocket para comunicación con orquestrador"""
    
    def __init__(self, config, warming_executor):
        self.config = config
        self.warming_executor = warming_executor
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        self.reconnect_delay = 5
        self.heartbeat_task = None
        
    async def connect(self):
        """Conecta al orquestrador"""
        
        # URL del WebSocket
        ws_url = f"{self.config.ORCHESTRATOR_WS_URL}/api/v1/warming/ws/{self.config.COMPUTER_ID}"
        
        logger.info(f"Connecting to: {ws_url}")
        
        while True:
            try:
                # ✅ PING INTERVAL MÁS LARGO PARA EVITAR DESCONEXIONES
                self.websocket = await websockets.connect(
                    ws_url,
                    ping_interval=60,  # Cambiado de 30 a 60
                    ping_timeout=30,   # Cambiado de 10 a 30
                    close_timeout=10
                )
                
                self.connected = True
                logger.info("✅ Connected to orchestrator!")
                
                # Iniciar heartbeat
                self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                
                # Iniciar escucha de mensajes
                await self._listen()
                
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Connection closed, reconnecting...")
                self.connected = False
                await asyncio.sleep(self.reconnect_delay)
                
            except Exception as e:
                logger.error(f"Connection error: {e}")
                self.connected = False
                await asyncio.sleep(self.reconnect_delay)
    
    async def _listen(self):
        """Escucha mensajes del orquestador"""
        
        try:
            async for message in self.websocket:
                # ✅ NO BLOQUEAR EL LOOP - Procesar en background
                asyncio.create_task(self._handle_message(message))
        
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Connection lost")
            self.connected = False
        
        except Exception as e:
            logger.error(f"Listen error: {e}")
    
    async def _handle_message(self, message: str):
        """Procesa mensaje del orquestador"""
        
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            logger.debug(f"Received message: {message_type}")
            
            if message_type == "connected":
                logger.info(f"Connected confirmation: {data.get('message')}")
            
            elif message_type == "execute_warming":
                # ✅ Ejecutar en background (NO BLOQUEANTE)
                asyncio.create_task(self._execute_warming(data))
            
            elif message_type == "stop_warming":
                await self._stop_warming(data)
            
            elif message_type == "status_request":
                await self._send_status()
            
            elif message_type == "heartbeat_ack":
                logger.debug("Heartbeat acknowledged")
            
            else:
                logger.warning(f"Unknown message type: {message_type}")
        
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def _execute_warming(self, data: dict):
        """Ejecuta warming (NON-BLOCKING)"""
        
        execution_id = data.get("execution_id")
        profile_id = data.get("profile_id")
        actions = data.get("actions", [])
        
        logger.info(f"🔥 Executing warming: execution_id={execution_id}, profile_id={profile_id}")
        
        # ✅ Ejecutar SIN AWAIT (para no bloquear websocket)
        try:
            await self.warming_executor.execute(
                execution_id=execution_id,
                profile_id=profile_id,
                actions=actions,
                progress_callback=self._send_progress
            )
        except Exception as e:
            logger.error(f"Warming execution error: {e}")
            
            # Enviar fallo al orquestador
            await self.send({
                "type": "execution_failed",
                "execution_id": execution_id,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def _stop_warming(self, data: dict):
        """Detiene warming"""
        
        execution_id = data.get("execution_id")
        logger.info(f"Stopping warming: execution_id={execution_id}")
        
        await self.warming_executor.stop(execution_id)
    
    async def _send_progress(self, execution_id: int, progress: int, log_entry: dict):
        """Envía progreso al orquestrador"""
        
        message = {
            "type": "execution_progress",
            "execution_id": execution_id,
            "progress": progress,
            "log_entry": log_entry,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.send(message)
    
    async def _send_status(self):
        """Envía estado al orquestrador"""
        
        import psutil
        
        state = {
            "active_browsers": self.warming_executor.browser_controller.get_active_count(),
            "max_browsers": self.config.MAX_BROWSERS,
            "active_executions": len(self.warming_executor.active_executions),
            "cpu_usage": psutil.cpu_percent(interval=1),
            "memory_usage": psutil.virtual_memory().percent,
            "uptime_seconds": 0
        }
        
        message = {
            "type": "status_update",
            "state": state,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.send(message)
    
    async def _heartbeat_loop(self):
        """✅ Loop de heartbeat MEJORADO"""
        
        heartbeat_interval = 30  # Cada 30 segundos
        
        while self.connected:
            try:
                await asyncio.sleep(heartbeat_interval)
                
                if self.connected and self.websocket:
                    try:
                        await self.send({
                            "type": "heartbeat",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        logger.debug("💓 Heartbeat sent")
                    except Exception as e:
                        logger.error(f"Heartbeat send failed: {e}")
                        break
            
            except asyncio.CancelledError:
                logger.debug("Heartbeat loop cancelled")
                break
            
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                break
    
    async def send(self, message: dict):
        """Envía mensaje al orquestrador"""
        
        if not self.connected or not self.websocket:
            logger.warning("Cannot send message: not connected")
            return False
        
        try:
            await self.websocket.send(json.dumps(message))
            return True
        
        except Exception as e:
            logger.error(f"Send error: {e}")
            return False
    
    async def disconnect(self):
        """Desconecta del orquestrador"""
        
        self.connected = False
        
        # Cancelar heartbeat
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # Cerrar WebSocket
        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass
        
        logger.info("Disconnected from orchestrator")