# apps/api/app/services/cache_service.py

import json
import logging
from typing import Optional, Any, Set
from abc import ABC, abstractmethod
import redis.asyncio as aioredis
from redis.asyncio.client import Redis
from redis.exceptions import RedisError
from fastapi import Request
from app.core.config import settings

logger = logging.getLogger(__name__)

class IAsyncCacheClient(ABC):
    @abstractmethod
    async def connect(self) -> None: ...
    @abstractmethod
    async def disconnect(self) -> None: ...
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None: ...
    @abstractmethod
    async def get(self, key: str) -> Optional[str]: ...
    @abstractmethod
    async def delete(self, key: str) -> None: ...
    @abstractmethod
    async def set_json(self, key: str, value: dict, ttl: Optional[int] = None) -> None: ...
    @abstractmethod
    async def get_json(self, key: str) -> Optional[dict]: ...
    @abstractmethod
    async def ping(self) -> bool: ...
    @abstractmethod
    async def sadd(self, key: str, *values: Any) -> None: ...
    @abstractmethod
    async def smembers(self, key: str) -> Set[str]: ...
    @abstractmethod
    async def expire(self, key: str, ttl: int) -> None: ...

    @property
    @abstractmethod
    def client(self) -> Any: ...

class RedisCacheClient(IAsyncCacheClient):
    def __init__(self, url: str):
        self._redis: Redis = aioredis.from_url(
            url,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30,
            max_connections=100
        )

    async def connect(self) -> None:
        try:
            await self._redis.ping()
            logger.info(f"Redis connection verified to {settings.REDIS_HOST}")
        except Exception as e:
            logger.error(f"Initial Redis ping failed: {e}")
            raise e

    async def disconnect(self) -> None:
        await self._redis.aclose()
        logger.info("Redis connection pool closed")

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        try:
            await self._redis.set(key, value, ex=ttl)
        except RedisError as e:
            logger.error(f"Redis SET error: {e}")

    async def get(self, key: str) -> Optional[str]:
        try:
            return await self._redis.get(key)
        except RedisError as e:
            logger.error(f"Redis GET error: {e}")
            return None

    async def delete(self, key: str) -> None:
        try:
            await self._redis.delete(key)
        except RedisError as e:
            logger.error(f"Redis DELETE error: {e}")

    async def set_json(self, key: str, value: dict, ttl: Optional[int] = None) -> None:
        await self.set(key, json.dumps(value), ttl=ttl)

    async def get_json(self, key: str) -> Optional[dict]:
        data = await self.get(key)
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return None
        return None

    async def ping(self) -> bool:
        try:
            return await self._redis.ping()
        except Exception as e:
            logger.error(f"Redis PING check failed: {str(e)}")
            return False

    async def sadd(self, key: str, *values: Any) -> None:
        try:
            if values:
                await self._redis.sadd(key, *values)
        except RedisError as e:
            logger.error(f"Redis SADD error: {e}")

    async def smembers(self, key: str) -> Set[str]:
        try:
            members = await self._redis.smembers(key)
            return set(members) if members else set()
        except RedisError as e:
            logger.error(f"Redis SMEMBERS error: {e}")
            return set()

    async def expire(self, key: str, ttl: int) -> None:
        try:
            await self._redis.expire(key, ttl)
        except RedisError as e:
            logger.error(f"Redis EXPIRE error: {e}")

    @property
    def client(self) -> Redis:
        return self._redis

class NoOpCacheClient(IAsyncCacheClient):
    async def connect(self) -> None: pass
    async def disconnect(self) -> None: pass
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None: pass
    async def get(self, key: str) -> Optional[str]: return None
    async def delete(self, key: str) -> None: pass
    async def set_json(self, key: str, value: dict, ttl: Optional[int] = None) -> None: pass
    async def get_json(self, key: str) -> Optional[dict]: return None
    async def ping(self) -> bool: return True
    async def sadd(self, key: str, *values: Any) -> None: pass
    async def smembers(self, key: str) -> Set[str]: return set()
    async def expire(self, key: str, ttl: int) -> None: pass

    @property
    def client(self) -> Any: return None

async def get_cache_client(request: Request) -> IAsyncCacheClient:
    if not hasattr(request.app.state, "cache"):
        return NoOpCacheClient()
    return request.app.state.cache
