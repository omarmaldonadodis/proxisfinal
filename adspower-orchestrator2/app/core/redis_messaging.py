# adspower-orchestrator2/app/core/redis_messaging.py (ACTUALIZACIÓN)
"""
Sistema de mensajería Redis Pub/Sub para comunicación entre procesos
ACTUALIZADO: Soporte para batch_id en comandos de warming
"""
import redis.asyncio as redis
import json
from typing import Dict, Callable, Optional
from loguru import logger
from datetime import datetime


class RedisMessaging:
    """Sistema de mensajería Redis Pub/Sub"""
    
    WARMING_COMMANDS_CHANNEL = "warming:commands"
    WARMING_RESPONSES_CHANNEL = "warming:responses"
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self.listener_task = None
    
    async def connect(self):
        """Conecta a Redis"""
        from app.config import settings
        
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info("✓ Redis connected")
            
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise
    
    async def stop(self):
        """Desconecta de Redis"""
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
        
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("Redis disconnected")
    
    async def publish_warming_command(
        self,
        computer_id: int,
        execution_id: int,
        profile_id: str,
        script_actions: list,
        batch_id: Optional[str] = None  # ✅ NUEVO
    ) -> bool:
        """
        Publica comando de warming
        
        ✅ NUEVO: Incluye batch_id para sincronización paralela
        """
        
        command = {
            "type": "execute_warming",
            "computer_id": computer_id,
            "execution_id": execution_id,
            "profile_id": profile_id,
            "script_actions": script_actions,
            "batch_id": batch_id,  # ✅ NUEVO
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            channel = self.WARMING_COMMANDS_CHANNEL
            
            await self.redis_client.publish(
                channel,
                json.dumps(command)
            )
            
            logger.debug(f"Published warming command: execution_id={execution_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to publish warming command: {e}")
            return False
    
    async def publish_warming_response(
        self,
        execution_id: int,
        status: str,
        result: Dict
    ) -> bool:
        """Publica respuesta de warming"""
        
        response = {
            "execution_id": execution_id,
            "status": status,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            await self.redis_client.publish(
                self.WARMING_RESPONSES_CHANNEL,
                json.dumps(response)
            )
            
            logger.debug(f"Published warming response: execution_id={execution_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to publish warming response: {e}")
            return False
    
    async def subscribe_warming_commands(
        self,
        callback: Callable[[Dict], None]
    ):
        """
        Escucha comandos de warming
        
        callback: Función async que procesa comandos
        """
        
        try:
            self.pubsub = self.redis_client.pubsub()
            await self.pubsub.subscribe(self.WARMING_COMMANDS_CHANNEL)
            
            logger.info(f"Subscribed to {self.WARMING_COMMANDS_CHANNEL}")
            
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    try:
                        command = json.loads(message["data"])
                        await callback(command)
                    except Exception as e:
                        logger.error(f"Error processing warming command: {e}")
        
        except Exception as e:
            logger.error(f"Warming commands subscription error: {e}")
    
    async def subscribe_warming_responses(
        self,
        callback: Callable[[Dict], None]
    ):
        """Escucha respuestas de warming"""
        
        try:
            if not self.pubsub:
                self.pubsub = self.redis_client.pubsub()
            
            await self.pubsub.subscribe(self.WARMING_RESPONSES_CHANNEL)
            
            logger.info(f"Subscribed to {self.WARMING_RESPONSES_CHANNEL}")
            
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    try:
                        response = json.loads(message["data"])
                        await callback(response)
                    except Exception as e:
                        logger.error(f"Error processing warming response: {e}")
        
        except Exception as e:
            logger.error(f"Warming responses subscription error: {e}")


# Instancia global
redis_messaging = RedisMessaging()