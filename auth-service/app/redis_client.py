import redis.asyncio as redis
from app.config import settings
from typing import Optional
import json


class RedisClient:
    def __init__(self):
        self.redis: Optional[redis.Redis] = None

    async def connect(self):
        """Connect to Redis"""
        self.redis = await redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
        print(f"✓ Connected to Redis at {settings.REDIS_URL}")

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
            print("✓ Disconnected from Redis")

    async def store_refresh_token(
        self,
        token: str,
        user_email: str,
        device_info: str = "electron_app",
        ttl_days: int = None
    ) -> bool:
        """Store refresh token in Redis with TTL"""
        if not self.redis:
            raise Exception("Redis not connected")

        ttl_days = ttl_days or settings.REFRESH_TOKEN_EXPIRE_DAYS
        ttl_seconds = ttl_days * 24 * 60 * 60

        token_data = {
            "user_email": user_email,
            "device_info": device_info,
        }

        key = f"refresh_token:{token}"
        await self.redis.setex(
            key,
            ttl_seconds,
            json.dumps(token_data)
        )
        return True

    async def get_refresh_token(self, token: str) -> Optional[dict]:
        """Get refresh token data from Redis"""
        if not self.redis:
            raise Exception("Redis not connected")

        key = f"refresh_token:{token}"
        data = await self.redis.get(key)

        if data:
            return json.loads(data)
        return None

    async def revoke_refresh_token(self, token: str) -> bool:
        """Revoke (delete) refresh token from Redis"""
        if not self.redis:
            raise Exception("Redis not connected")

        key = f"refresh_token:{token}"
        result = await self.redis.delete(key)
        return result > 0


# Global instance
redis_client = RedisClient()
