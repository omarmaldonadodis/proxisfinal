# agent/websocket_client.py - VERSIÓN CORREGIDA
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
        self.listen_task = None
        
    async def connect(self):
        """Conecta al orquestador CON JWT y mantiene conexión"""
        
        # ✅ 1. Cargar token JWT guardado
        from registration_client import RegistrationClient
        
        registration_client = RegistrationClient(
            self.config.ORCHESTRATOR_URL,
            self.config
        )
        
        token = registration_client.load_token()
        
        if not token:
            logger.error("No JWT token found. Please register first.")
            raise Exception("Missing authentication token")
        
        # ✅ 2. Loop de reconexión automática
        while True:
            try:
                # Construir URL con token
                ws_url = f"{self.config.ORCHESTRATOR_WS_URL}/api/v1/warming/ws/{self.config.COMPUTER_ID}?token={token}"
                
                logger.info(f"Connecting to: {ws_url}")
                
                # Conectar
                self.websocket = await websockets.connect(
                    ws_url,
                    ping_interval=30,
                    ping_timeout=10,
                    close_timeout=5
                )
                
                self.connected = True
                logger.info("✅ Connected to orchestrator!")
                
                # ✅ CRÍTICO: Iniciar tareas de comunicación
                self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                self.listen_task = asyncio.create_task(self._listen())
                
                # ✅ ESPERAR a que se cierre la conexión
                try:
                    await self.listen_task
                except asyncio.CancelledError:
                    logger.info("Listen task cancelled")
                
                # Si llegamos aquí, la conexión se cerró
                logger.warning("Connection closed, will reconnect...")
                
            except websockets.exceptions.InvalidStatusCode as e:
                logger.error(f"❌ Connection rejected: {e}")
                logger.error("   Possible causes:")
                logger.error("   - Invalid JWT token")
                logger.error("   - Computer not found")
                logger.error("   - Token expired")
                await asyncio.sleep(self.reconnect_delay)
                
            except websockets.exceptions.WebSocketException as e:
                logger.error(f"WebSocket error: {e}")
                await asyncio.sleep(self.reconnect_delay)
                
            except Exception as e:
                logger.error(f"Connection error: {e}")
                await asyncio.sleep(self.reconnect_delay)
            
            finally:
                # Limpiar estado
                self.connected = False
                
                if self.heartbeat_task:
                    self.heartbeat_task.cancel()
                    try:
                        await self.heartbeat_task
                    except asyncio.CancelledError:
                        pass
                
                if self.websocket:
                    try:
                        await self.websocket.close()
                    except:
                        pass
                
                logger.info(f"Reconnecting in {self.reconnect_delay} seconds...")
                await asyncio.sleep(self.reconnect_delay)
    
    async def _listen(self):
        """Escucha mensajes del orquestador"""
        
        try:
            async for message in self.websocket:
                # Procesar en background para no bloquear
                asyncio.create_task(self._handle_message(message))
        
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"Connection lost: {e}")
            self.connected = False
        
        except Exception as e:
            logger.error(f"Listen error: {e}")
            self.connected = False
    
    async def _handle_message(self, message: str):
        """Procesa mensaje del orquestador"""
        
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            logger.debug(f"📨 Received: {message_type}")
            
            if message_type == "connected":
                logger.info(f"✅ {data.get('message')}")
            
            elif message_type == "execute_warming":
                asyncio.create_task(self._execute_warming(data))
            
            elif message_type == "stop_warming":
                await self._stop_warming(data)
            
            elif message_type == "status_request":
                await self._send_status()
            
            elif message_type == "heartbeat_ack":
                logger.debug("💓 Heartbeat OK")
            
            else:
                logger.warning(f"Unknown message type: {message_type}")
        
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
        
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def _execute_warming(self, data: dict):
        """Ejecuta warming (NON-BLOCKING)"""
        
        execution_id = data.get("execution_id")
        profile_id = data.get("profile_id")
        actions = data.get("actions", [])
        
        logger.info(f"🔥 Executing warming: execution_id={execution_id}, profile={profile_id}")
        
        try:
            await self.warming_executor.execute(
                execution_id=execution_id,
                profile_id=profile_id,
                actions=actions,
                progress_callback=self._send_progress
            )
        except Exception as e:
            logger.error(f"❌ Warming failed: {e}")
            
            await self.send({
                "type": "execution_failed",
                "execution_id": execution_id,
                "error": str(e),
                "error_type": "execution_error",
                "timestamp": datetime.utcnow().isoformat()
            })
    
    async def _stop_warming(self, data: dict):
        """Detiene warming"""
        
        execution_id = data.get("execution_id")
        logger.info(f"🛑 Stopping warming: {execution_id}")
        
        await self.warming_executor.stop(execution_id)
    
    async def _send_progress(self, execution_id: int, progress: int, log_entry: dict):
        """Envía progreso al orquestrador"""

        if log_entry.get("is_event"):
            event_data = log_entry.get("event", {})
            
            message = {
                "type": "event_detected",  # ✅ NUEVO TIPO
                "execution_id": execution_id,
                "event": event_data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Log local
            severity = event_data.get("severity", "info")
            event_type = event_data.get("event_type", "unknown")
            event_message = event_data.get("message", "")
            
            if severity == "critical":
                logger.error(f"🔴 CRITICAL EVENT: {event_type} - {event_message}")
            elif severity == "warning":
                logger.warning(f"🟡 WARNING EVENT: {event_type} - {event_message}")
            else:
                logger.info(f"🟢 EVENT: {event_type} - {event_message}")
            
            await self.send(message)
            return
        
        if not log_entry.get("completed", True) and log_entry.get("error"):
            # Error
            message = {
                "type": "execution_failed",
                "execution_id": execution_id,
                "error": log_entry.get("error"),
                "error_type": log_entry.get("error_type", "unknown"),
                "retry_count": log_entry.get("retry_count", 0),
                "timestamp": datetime.utcnow().isoformat()
            }
        elif log_entry.get("completed"):
            # Completado
            message = {
                "type": "execution_completed",
                "execution_id": execution_id,
                "result": log_entry,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            # Progreso
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
            "cpu_usage": round(psutil.cpu_percent(interval=0.1), 1),
            "memory_usage": round(psutil.virtual_memory().percent, 1)
        }
        
        message = {
            "type": "status_update",
            "state": state,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.send(message)
    
    async def _heartbeat_loop(self):
        """Loop de heartbeat cada 30 segundos"""
        
        try:
            while self.connected:
                await asyncio.sleep(30)
                
                if self.connected and self.websocket:
                    try:
                        await self.send({
                            "type": "heartbeat",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        logger.debug("💓 Heartbeat")
                    except Exception as e:
                        logger.error(f"Heartbeat failed: {e}")
                        break
        
        except asyncio.CancelledError:
            logger.debug("Heartbeat stopped")
    
    # agent/websocket_client.py (LÍNEA 210)

    async def send(self, message: dict):
        """Envía mensaje al orquestrador"""
        
        if not self.connected or not self.websocket:
            logger.warning("⚠️ Cannot send: not connected")
            return False
        
        try:
            # ✅ Serialización segura con manejo de datetime
            def datetime_converter(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
            
            json_str = json.dumps(message, default=datetime_converter)
            await self.websocket.send(json_str)
            return True
        
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Send failed: connection closed")
            self.connected = False
            return False
        
        except Exception as e:
            logger.error(f"Send error: {e}")
            return False
    
    async def disconnect(self):
        """Desconecta del orquestrador"""
        
        logger.info("Disconnecting...")
        
        self.connected = False
        
        # Cancelar tareas
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        
        if self.listen_task:
            self.listen_task.cancel()
        
        # Cerrar WebSocket
        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass
        
        logger.info("✅ Disconnected")