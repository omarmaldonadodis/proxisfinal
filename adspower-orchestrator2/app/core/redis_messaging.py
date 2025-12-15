# app/core/redis_messaging.py - VERSIÓN MEJORADA
"""
Sistema de mensajería distribuida via Redis Pub/Sub
Permite comunicación entre procesos (Celery ↔ FastAPI)
"""
import redis.asyncio as aioredis
import json
import asyncio
from typing import Callable, Optional, Dict, Awaitable
from loguru import logger
from app.config import settings

class RedisMessaging:
    """
    Gestor de mensajería distribuida via Redis Pub/Sub
    
    Canales:
    - warming_commands: Comandos de ejecución de warming
    - warming_responses: Respuestas de ejecución
    """
    
    # Nombres de canales
    CHANNEL_WARMING_COMMANDS = "warming:commands"
    CHANNEL_WARMING_RESPONSES = "warming:responses"
    
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self.pubsub: Optional[aioredis.client.PubSub] = None
        self._listeners: Dict[str, asyncio.Task] = {}
        self._running = False
        self._connected = False  # ✅ NUEVO: Flag de estado
    
    async def connect(self):
        """Conecta a Redis (idempotente)"""
        
        # ✅ Si ya está conectado, no hacer nada
        if self._connected and self.redis:
            logger.debug("Redis already connected, skipping...")
            return
        
        try:
            self.redis = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            
            # Test conexión
            await self.redis.ping()
            
            self._connected = True
            logger.info("✓ Redis Pub/Sub connected")
            
        except Exception as e:
            self._connected = False
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def publish_warming_command(
        self,
        computer_id: int,
        execution_id: int,
        profile_id: str,
        script_actions: list
    ) -> bool:
        """
        Publica comando de warming para que FastAPI lo envíe via WebSocket
        
        Args:
            computer_id: ID de computadora destino
            execution_id: ID de ejecución
            profile_id: AdsPower profile ID
            script_actions: Acciones del script
            
        Returns:
            True si se publicó correctamente
        """
        
        # ✅ Verificar conexión antes de publicar
        if not self._connected or not self.redis:
            logger.error("Redis not connected - attempting reconnect...")
            try:
                await self.connect()
            except Exception as e:
                logger.error(f"Failed to reconnect: {e}")
                return False
        
        command = {
            "type": "execute_warming",
            "computer_id": computer_id,
            "execution_id": execution_id,
            "profile_id": profile_id,
            "script_actions": script_actions,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        try:
            await self.redis.publish(
                self.CHANNEL_WARMING_COMMANDS,
                json.dumps(command)
            )
            
            logger.info(
                f"📤 Published warming command: "
                f"Execution {execution_id}, Computer {computer_id}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish warming command: {e}")
            self._connected = False  # ✅ Marcar como desconectado
            return False
    
    async def subscribe_warming_commands(
        self,
        callback: Callable[[dict], Awaitable[None]]
    ):
        """
        Suscribe a comandos de warming (corre en FastAPI)
        
        Args:
            callback: Función async que procesa comandos
        """
        
        if not self._connected:
            await self.connect()
        
        self.pubsub = self.redis.pubsub()
        await self.pubsub.subscribe(self.CHANNEL_WARMING_COMMANDS)
        
        self._running = True
        
        logger.info(f"👂 Listening for warming commands on '{self.CHANNEL_WARMING_COMMANDS}'")
        
        try:
            async for message in self.pubsub.listen():
                if not self._running:
                    break
                
                if message['type'] == 'message':
                    try:
                        command = json.loads(message['data'])
                        logger.debug(f"📥 Received command: {command.get('execution_id')}")
                        
                        # Ejecutar callback
                        await callback(command)
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON in message: {e}")
                    except Exception as e:
                        logger.error(f"Error processing command: {e}")
        
        except asyncio.CancelledError:
            logger.info("Warming commands listener cancelled")
        
        finally:
            await self.pubsub.unsubscribe(self.CHANNEL_WARMING_COMMANDS)
            await self.pubsub.close()
    
    async def publish_warming_response(
        self,
        execution_id: int,
        status: str,
        result: dict
    ):
        """
        Publica respuesta de ejecución (desde FastAPI)
        
        Args:
            execution_id: ID de ejecución
            status: success, failed, timeout
            result: Datos del resultado
        """
        
        if not self._connected or not self.redis:
            return
        
        response = {
            "execution_id": execution_id,
            "status": status,
            "result": result,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        try:
            await self.redis.publish(
                self.CHANNEL_WARMING_RESPONSES,
                json.dumps(response)
            )
            
            logger.debug(f"📤 Published response for execution {execution_id}")
            
        except Exception as e:
            logger.error(f"Failed to publish response: {e}")
    
    async def stop(self):
        """Detiene listeners y cierra conexiones"""
        self._running = False
        self._connected = False
        
        if self.pubsub:
            await self.pubsub.close()
        
        if self.redis:
            await self.redis.close()
        
        logger.info("Redis Pub/Sub disconnected")

# Instancia global
redis_messaging = RedisMessaging()