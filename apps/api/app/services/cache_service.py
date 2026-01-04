# apps/api/app/services/cache_service.py

import logging
from typing import Optional, Any, Set, List, Dict, Union
from abc import ABC, abstractmethod
import redis.asyncio as aioredis
from redis.asyncio.client import Redis
from redis.exceptions import RedisError
from starlette.requests import HTTPConnection
from app.core.config import settings
# ⚡ Performance: Use orjson for ultra-fast serialization if available
try:
    import orjson
except ImportError:
    import json as orjson 

logger = logging.getLogger(__name__)

class IAsyncCacheClient(ABC):
    """
    💎 DIAMOND INTERFACE: THE UNIVERSAL CACHE CONTRACT.
    Defines the strict architectural standard for any caching backend (Redis/Valkey).
    Ensures support for AI Memory (Lists), Objects (Hashes), and Real-time Events (Pub/Sub).
    """

    # --- 🔌 LIFECYCLE ---
    @abstractmethod
    async def connect(self) -> None: 
        """Establishes the connection pool."""
        ...

    @abstractmethod
    async def disconnect(self) -> None: 
        """Closes connections gracefully."""
        ...
    
    @abstractmethod
    async def ping(self) -> bool: 
        """Health check pulse."""
        ...

    @property
    @abstractmethod
    def client(self) -> Any: 
        """Access to the raw underlying client."""
        ...

    # --- 🔑 BASIC KEY-VALUE ---
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None: 
        """Atomic set with optional TTL."""
        ...

    @abstractmethod
    async def get(self, key: str) -> Optional[str]: 
        """Retrieve a raw string value."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None: 
        """Remove a key instantly."""
        ...
    
    @abstractmethod
    async def exists(self, key: str) -> bool: 
        """Check if a key exists."""
        ...
    
    @abstractmethod
    async def expire(self, key: str, ttl: int) -> None: 
        """Set a time-to-live on a key."""
        ...
    
    @abstractmethod
    async def incr(self, key: str) -> int: 
        """Atomic increment (useful for counters/rate limiting)."""
        ...

    # --- 📦 JSON OBJECTS (SMART STORAGE) ---
    @abstractmethod
    async def set_json(self, key: str, value: dict, ttl: Optional[int] = None) -> None: 
        """Serialize and store a dictionary as JSON."""
        ...

    @abstractmethod
    async def get_json(self, key: str) -> Optional[dict]: 
        """Retrieve and deserialize a JSON object."""
        ...

    # --- 🧠 LISTS (CRITICAL FOR AI MEMORY) ---
    # �� Fixes previous 'AttributeError' in NLU Service
    @abstractmethod
    async def lpush(self, key: str, *values: Any) -> int: 
        """Push values to the head of a list (Stack Memory)."""
        ...
        
    @abstractmethod
    async def rpush(self, key: str, *values: Any) -> int: 
        """Push values to the tail of a list (Queue Memory)."""
        ...

    @abstractmethod
    async def lrange(self, key: str, start: int, end: int) -> List[str]: 
        """Retrieve a range of elements (Context Window Retrieval)."""
        ...
    
    @abstractmethod
    async def ltrim(self, key: str, start: int, end: int) -> None: 
        """Trim list to keep only recent memory (Context Management)."""
        ...

    # --- 📚 SETS (UNIQUE COLLECTIONS) ---
    @abstractmethod
    async def sadd(self, key: str, *values: Any) -> None: 
        """Add unique members to a set."""
        ...

    @abstractmethod
    async def smembers(self, key: str) -> Set[str]: 
        """Get all members of a set."""
        ...
    
    @abstractmethod
    async def srem(self, key: str, *values: Any) -> None: 
        """Remove members from a set."""
        ...

    # --- 🗂️ HASHES (STRUCTURED DATA) ---
    @abstractmethod
    async def hset(self, name: str, mapping: Dict[str, Any]) -> int: 
        """Set fields in a hash (Object Storage)."""
        ...
    
    @abstractmethod
    async def hgetall(self, name: str) -> Dict[str, str]: 
        """Get all fields and values from a hash."""
        ...

    # --- 📡 REAL-TIME PUB/SUB (WEBSOCKET BACKBONE) ---
    @abstractmethod
    async def publish(self, channel: str, message: str) -> int: 
        """Broadcast a message to a channel."""
        ...

    @abstractmethod
    async def subscribe(self, channel: str) -> Any: 
        """Listen to a channel (Returns PubSub object)."""
        ...

class RedisCacheClient(IAsyncCacheClient):
    """
    💎 TITANIUM IMPLEMENTATION.
    A robust, fault-tolerant Redis wrapper that handles:
    - Automatic JSON Serialization (Orjson).
    - Connection Pooling & Health Checks.
    - AI Memory Operations (Lists).
    - Real-time Events (Pub/Sub).
    - Fallback Magic (Passes unknown commands directly to Redis).
    """
    def __init__(self, url: str):
        # 🛡️ Connection Pool Config
        self._redis: Redis = aioredis.from_url(
            url,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=getattr(settings, 'REDIS_TIMEOUT', 5),
            socket_connect_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30,
            max_connections=getattr(settings, 'REDIS_MAX_CONNECTIONS', 100)
        )

    @property
    def client(self) -> Redis:
        """Expose raw client for power users."""
        return self._redis

    # 💎 THE MAGIC FIX: Forward any unknown method to the real Redis client
    # This solves 'AttributeError: lpush' forever.
    def __getattr__(self, name):
        return getattr(self._redis, name)

    async def connect(self) -> None:
        try:
            await self._redis.ping()
            host = getattr(settings, 'REDIS_HOST', 'unknown')
            logger.info(f"✅ Redis connection verified to {host}")
        except Exception as e:
            logger.error(f"❌ Initial Redis ping failed: {e}")
            raise e

    async def disconnect(self) -> None:
        await self._redis.aclose()
        logger.info("Redis connection pool closed")

    # --- 🔑 KEY-VALUE OPS ---
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        try:
            await self._redis.set(key, value, ex=ttl)
        except RedisError as e:
            logger.error(f"Redis SET error [{key}]: {e}")

    async def get(self, key: str) -> Optional[str]:
        try:
            return await self._redis.get(key)
        except RedisError as e:
            logger.error(f"Redis GET error [{key}]: {e}")
            return None

    async def delete(self, key: str) -> None:
        try:
            await self._redis.delete(key)
        except RedisError as e:
            logger.error(f"Redis DELETE error [{key}]: {e}")

    async def exists(self, key: str) -> bool:
        try:
            return await self._redis.exists(key) > 0
        except RedisError:
            return False

    async def incr(self, key: str) -> int:
        try:
            return await self._redis.incr(key)
        except RedisError as e:
            logger.error(f"Redis INCR error [{key}]: {e}")
            return 0

    # --- 📦 JSON OPS ---
    async def set_json(self, key: str, value: dict, ttl: Optional[int] = None) -> None:
        try:
            # Ultra-fast serialization
            json_bytes = orjson.dumps(value)
            # orjson returns bytes, Redis needs str if decode_responses=True?
            # Actually, decode_responses=True usually expects we send str or bytes.
            # Safe to send decoded string:
            await self.set(key, json_bytes.decode('utf-8'), ttl=ttl)
        except Exception as e:
             logger.error(f"Serialization error for key {key}: {e}")

    async def get_json(self, key: str) -> Optional[dict]:
        data = await self.get(key)
        if data:
            try:
                return orjson.loads(data)
            except Exception:
                logger.warning(f"Failed to decode JSON for key {key}")
                return None
        return None

    async def ping(self) -> bool:
        try:
            return await self._redis.ping()
        except Exception as e:
            logger.error(f"Redis PING check failed: {str(e)}")
            return False

    # --- 🧠 LISTS (AI MEMORY) ---
    async def lpush(self, key: str, *values: Any) -> int:
        if not values: return 0
        return await self._redis.lpush(key, *values)

    async def rpush(self, key: str, *values: Any) -> int:
        if not values: return 0
        return await self._redis.rpush(key, *values)

    async def lrange(self, key: str, start: int, end: int) -> List[str]:
        try:
            return await self._redis.lrange(key, start, end)
        except RedisError:
            return []

    async def ltrim(self, key: str, start: int, end: int) -> None:
        try:
            await self._redis.ltrim(key, start, end)
        except RedisError:
            pass

    # --- 📚 SETS ---
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

    async def srem(self, key: str, *values: Any) -> None:
        try:
            if values:
                await self._redis.srem(key, *values)
        except RedisError:
            pass

    async def expire(self, key: str, ttl: int) -> None:
        try:
            await self._redis.expire(key, ttl)
        except RedisError as e:
            logger.error(f"Redis EXPIRE error: {e}")

    # --- 🗂️ HASHES ---
    async def hset(self, name: str, mapping: Dict[str, Any]) -> int:
        return await self._redis.hset(name, mapping=mapping)

    async def hgetall(self, name: str) -> Dict[str, str]:
        return await self._redis.hgetall(name)

    async def incr(self, key: str) -> int:
        """
        Atomically increments the value of key by 1.
        Critical for Rate Limiting.
        """
        try:
            return await self._redis.incr(key)
        except RedisError as e:
            logger.error(f"Redis INCR error: {e}")
            return 1 # Fallback to allow traffic if cache fails

    # 💎 NEW: Pub/Sub Implementation
    async def publish(self, channel: str, message: str) -> int:
        """Publishes a message to a Redis channel."""
        try:
            return await self._redis.publish(channel, message)
        except RedisError as e:
            logger.error(f"Redis PUBLISH error to {channel}: {e}")
            return 0

    async def subscribe(self, channel: str) -> Any:
        """Subscribes to a channel and returns the PubSub object."""
        try:
            pubsub = self._redis.pubsub()
            await pubsub.subscribe(channel)
            return pubsub
        except RedisError as e:
            logger.error(f"Redis SUBSCRIBE error to {channel}: {e}")
            return None

# =========================================================================
# 🛡️ THE SAFETY NET: NO-OP CLIENT (FOR FALLBACKS)
# =========================================================================

class NoOpCacheClient(IAsyncCacheClient):
    """
    💎 GHOST CLIENT.
    Implements the FULL Interface but does nothing.
    Prevents 'AttributeError' if Redis is disabled or fails.
    """
    async def connect(self) -> None: pass
    async def disconnect(self) -> None: pass
    
    @property
    def client(self) -> Any: return None
    
    # Key-Value
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None: pass
    async def get(self, key: str) -> Optional[str]: return None
    async def delete(self, key: str) -> None: pass
    async def exists(self, key: str) -> bool: return False
    async def expire(self, key: str, ttl: int) -> None: pass
    async def incr(self, key: str) -> int: return 1
    
    # JSON
    async def set_json(self, key: str, value: dict, ttl: Optional[int] = None) -> None: pass
    async def get_json(self, key: str) -> Optional[dict]: return None
    
    # Health
    async def ping(self) -> bool: return True
    
    # 💎 LISTS (AI MEMORY) - Essential to prevent crashes
    async def lpush(self, key: str, *values: Any) -> int: return 0
    async def rpush(self, key: str, *values: Any) -> int: return 0
    async def lrange(self, key: str, start: int, end: int) -> list: return []
    async def ltrim(self, key: str, start: int, end: int) -> None: pass

    # Sets
    async def sadd(self, key: str, *values: Any) -> None: pass
    async def smembers(self, key: str) -> Set[str]: return set()
    async def srem(self, key: str, *values: Any) -> None: pass
    
    # Hashes
    async def hset(self, name: str, mapping: dict) -> int: return 0
    async def hgetall(self, name: str) -> dict: return {}

    # Pub/Sub
    async def publish(self, channel: str, message: str) -> int: return 0
    async def subscribe(self, channel: str) -> Any: return None

# =========================================================================
# 💉 DEPENDENCY INJECTION (FASTAPI)
# =========================================================================

async def get_cache_from_request(conn: HTTPConnection) -> IAsyncCacheClient:
    """
    Retrieves the cache client from the FastAPI app state.
    Used by Routes/Endpoints.
    """
    if not hasattr(conn.app.state, "cache") or conn.app.state.cache is None:
        return NoOpCacheClient()
    return conn.app.state.cache

def get_cache_client() -> IAsyncCacheClient:
    """
    💎 Creates a new Redis client instance.
    Used explicitly by the Worker Node to establish connection.
    """
    # تأكد أن settings مستوردة من app.core.config
    return RedisCacheClient(str(settings.REDIS_URL))
