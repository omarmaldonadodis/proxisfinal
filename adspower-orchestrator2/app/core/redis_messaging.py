# app/core/redis_messaging.py
import json
import redis.asyncio as aioredis
from loguru import logger
from app.config import settings


class RedisMessaging:
    """Pub/Sub para comunicación en tiempo real entre servidor y agentes"""

    def __init__(self):
        self._redis = None

    async def connect(self):
        try:
            self._redis = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("✅ Redis messaging connected")
        except Exception as e:
            logger.error(f"Redis messaging error: {e}")

    async def disconnect(self):
        if self._redis:
            await self._redis.close()

    async def publish(self, channel: str, message: dict):
        if not self._redis:
            return
        try:
            await self._redis.publish(channel, json.dumps(message))
        except Exception as e:
            logger.error(f"Redis publish error: {e}")

    async def subscribe(self, channel: str):
        if not self._redis:
            return None
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(channel)
        return pubsub

    def get_agent_channel(self, computer_id: int) -> str:
        return f"agent:{computer_id}"

    def get_admin_channel(self) -> str:
        return "admin:broadcast"


redis_messaging = RedisMessaging()