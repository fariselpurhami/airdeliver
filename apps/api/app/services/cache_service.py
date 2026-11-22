# apps/api/app/services/cache_service.py

import logging
import functools
from abc import ABC, abstractmethod
from typing import (
    Optional, Any, Set, List, Dict, TypeVar, Callable, Coroutine, cast
)

import redis.asyncio as redis_async
from redis.asyncio.client import Redis, PubSub
from redis.asyncio.connection import ConnectionPool
from redis.exceptions import RedisError, TimeoutError, ConnectionError
from starlette.requests import HTTPConnection

from app.core.config import settings

# Fast JSON serialization with a standard library fallback
try:
    import orjson
    JSONDecodeError = orjson.JSONDecodeError
except ImportError:
    import json as orjson
    JSONDecodeError = ValueError

logger = logging.getLogger(__name__)

T = TypeVar("T")
R = TypeVar("R")


def with_resilience(default_factory: Callable[[], Any] = lambda: None) -> Callable:
    """
    Decorator to enforce resilience on cache operations.
    Captures Redis exceptions, emits structured logs, and returns a safe fallback
    to prevent cache infrastructure failures from cascading into application outages.
    """
    def decorator(func: Callable[..., Coroutine[Any, Any, R]]) -> Callable[..., Coroutine[Any, Any, R]]:
        @functools.wraps(func)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> R:
            try:
                if hasattr(self, '_redis') and getattr(self, '_redis', None) is None:
                    logger.warning(
                        "JIT Auto-connect triggered. Explicit lifecycle management missed.",
                        extra={"operation": func.__name__}
                    )
                    await self.connect()
                return await func(self, *args, **kwargs)
            except (ConnectionError, TimeoutError) as e:
                logger.error(
                    "Cache connection/timeout failure",
                    extra={
                        "operation": func.__name__,
                        "error": str(e),
                        "args": args,
                    }
                )
                return default_factory()
            except (RedisError, RuntimeError) as e:
                logger.error(
                    "Cache operation failed",
                    extra={
                        "operation": func.__name__,
                        "error": str(e),
                        "args": args,
                    }
                )
                return default_factory()
        return wrapper
    return decorator


class IAsyncCacheClient(ABC):
    """
    Architectural contract for distributed cache backends.
    Enforces strict separation of application logic from caching infrastructure.
    """

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...
    
    @abstractmethod
    async def ping(self) -> bool: ...

    @property
    @abstractmethod
    def client(self) -> Any: ...

    # --- Scalar Operations ---
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None: ...
    
    @abstractmethod
    async def add(self, key: str, value: Any, ttl: Optional[int] = None) -> bool: ...

    @abstractmethod
    async def get(self, key: str) -> Optional[str]: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...
    
    @abstractmethod
    async def exists(self, key: str) -> bool: ...
    
    @abstractmethod
    async def expire(self, key: str, ttl: int) -> None: ...
    
    @abstractmethod
    async def incr(self, key: str) -> int: ...

    # --- Structured Data (JSON) Operations ---
    @abstractmethod
    async def set_json(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> None: ...

    @abstractmethod
    async def get_json(self, key: str) -> Optional[Dict[str, Any]]: ...

    # --- Sequential Memory (Lists) Operations ---
    @abstractmethod
    async def lpush(self, key: str, *values: str) -> int: ...
        
    @abstractmethod
    async def rpush(self, key: str, *values: str) -> int: ...

    @abstractmethod
    async def lrange(self, key: str, start: int, end: int) -> List[str]: ...
    
    @abstractmethod
    async def ltrim(self, key: str, start: int, end: int) -> None: ...

    # --- Unique Collection (Sets) Operations ---
    @abstractmethod
    async def sadd(self, key: str, *values: str) -> int: ...

    @abstractmethod
    async def smembers(self, key: str) -> Set[str]: ...
    
    @abstractmethod
    async def srem(self, key: str, *values: str) -> int: ...

    # --- Hash Map Operations ---
    @abstractmethod
    async def hset(self, name: str, mapping: Dict[str, Any]) -> int: ...
    
    @abstractmethod
    async def hgetall(self, name: str) -> Dict[str, str]: ...

    # --- Event Streaming (Pub/Sub) ---
    @abstractmethod
    async def publish(self, channel: str, message: str) -> int: ...

    async def publish_required(self, channel: str, message: str) -> int:
        """Required delivery must not turn a backend failure into zero listeners."""
        raise NotImplementedError("This cache backend has no strict publication contract")

    @abstractmethod
    async def subscribe(self, channel: str) -> Any: ...


class RedisCacheClient(IAsyncCacheClient):
    """
    Production-grade Redis implementation of the cache contract.
    Features connection pooling, transparent serialization, automatic
    fault tolerance, and deterministic resource lifecycle management.
    """
    
    def __init__(self, url: str) -> None:
        self._url = url
        self._pool: Optional[ConnectionPool] = None
        self._redis: Optional[Redis] = None

    @property
    def client(self) -> Redis:
        """
        Exposes raw client for advanced use cases (e.g., pipelines, transactions).
        Consumers must handle RedisError explicitly when bypassing the interface.
        """
        if self._redis is None:
            raise RuntimeError("Cache client accessed before connection is established.")
        return self._redis

    async def connect(self) -> None:
        """Initializes connection pool with sensible timeouts and health checks."""
        timeout = float(getattr(settings, 'REDIS_TIMEOUT', 5.0))
        max_connections = int(getattr(settings, 'REDIS_MAX_CONNECTIONS', 100))
        
        self._pool = ConnectionPool.from_url(
            self._url,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=timeout,
            socket_connect_timeout=timeout,
            retry_on_timeout=True,
            health_check_interval=30,
            max_connections=max_connections
        )
        self._redis = Redis(connection_pool=self._pool)
        
        try:
            await self._redis.ping()
            # Do not log the full URL to prevent credential leakage
            logger.info("Redis connection pool initialized successfully.")
        except RedisError as e:
            logger.critical("Failed to establish initial Redis connection", extra={"error": str(e)})
            raise RuntimeError(f"Cache initialization failed: {e}") from e

    async def disconnect(self) -> None:
        """Deterministically releases connection pool resources."""
        if self._redis:
            await self._redis.aclose()
        if self._pool:
            await self._pool.disconnect()
        logger.info("Redis connection pool resources released.")

    @with_resilience(default_factory=lambda: False)
    async def ping(self) -> bool:
        return await self.client.ping()

    # --- Scalar Operations ---
    
    @with_resilience(default_factory=lambda: None)
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        await self.client.set(key, value, ex=ttl)
  
    @with_resilience(default_factory=lambda: False)
    async def add(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Atomically sets a key only if it does not exist (SETNX). Resolves TOCTOU."""
        result = await self.client.set(key, value, ex=ttl, nx=True)
        return bool(result)

    @with_resilience(default_factory=lambda: None)
    async def get(self, key: str) -> Optional[str]:
        return await self.client.get(key)

    @with_resilience(default_factory=lambda: None)
    async def delete(self, key: str) -> None:
        await self.client.delete(key)

    @with_resilience(default_factory=lambda: False)
    async def exists(self, key: str) -> bool:
        return await self.client.exists(key) > 0

    @with_resilience(default_factory=lambda: None)
    async def expire(self, key: str, ttl: int) -> None:
        await self.client.expire(key, ttl)

    @with_resilience(default_factory=lambda: 1)
    async def incr(self, key: str) -> int:
        return await self.client.incr(key)

    # --- Structured Data (JSON) Operations ---
    
    async def set_json(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """Serializes dictionary to JSON and stores atomically."""
        try:
            # orjson returns bytes; Redis decodes responses natively.
            json_payload = orjson.dumps(value).decode("utf-8")
        except TypeError as e:
            logger.error("JSON serialization failed", extra={"key": key, "error": str(e)})
            return
            
        await self.set(key, json_payload, ttl=ttl)

    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieves and deserializes JSON data securely."""
        data = await self.get(key)
        if not data:
            return None
            
        try:
            return orjson.loads(data)
        except JSONDecodeError as e:
            logger.warning("JSON payload corruption detected", extra={"key": key, "error": str(e)})
            return None

    # --- Sequential Memory (Lists) Operations ---
    
    @with_resilience(default_factory=lambda: 0)
    async def lpush(self, key: str, *values: str) -> int:
        if not values:
            return 0
        return await self.client.lpush(key, *values)

    @with_resilience(default_factory=lambda: 0)
    async def rpush(self, key: str, *values: str) -> int:
        if not values:
            return 0
        return await self.client.rpush(key, *values)

    @with_resilience(default_factory=list)
    async def lrange(self, key: str, start: int, end: int) -> List[str]:
        return await self.client.lrange(key, start, end)

    @with_resilience(default_factory=lambda: None)
    async def ltrim(self, key: str, start: int, end: int) -> None:
        await self.client.ltrim(key, start, end)

    # --- Unique Collection (Sets) Operations ---
    
    @with_resilience(default_factory=lambda: 0)
    async def sadd(self, key: str, *values: str) -> int:
        if not values:
            return 0
        return await self.client.sadd(key, *values)

    @with_resilience(default_factory=set)
    async def smembers(self, key: str) -> Set[str]:
        members = await self.client.smembers(key)
        return set(members) if members else set()

    @with_resilience(default_factory=lambda: 0)
    async def srem(self, key: str, *values: str) -> int:
        if not values:
            return 0
        return await self.client.srem(key, *values)

    # --- Hash Map Operations ---
    
    @with_resilience(default_factory=lambda: 0)
    async def hset(self, name: str, mapping: Dict[str, Any]) -> int:
        if not mapping:
            return 0
        return await self.client.hset(name, mapping=mapping)

    @with_resilience(default_factory=dict)
    async def hgetall(self, name: str) -> Dict[str, str]:
        return await self.client.hgetall(name)

    # --- Event Streaming (Pub/Sub) ---
    
    @with_resilience(default_factory=lambda: 0)
    async def publish(self, channel: str, message: str) -> int:
        return await self.client.publish(channel, message)

    async def publish_required(self, channel: str, message: str) -> int:
        if self._redis is None:
            await self.connect()
        return await self.client.publish(channel, message)

    @with_resilience(default_factory=lambda: None)
    async def subscribe(self, channel: str) -> Optional[PubSub]:
        """
        Subscribes to a channel.
        Warning: The caller is responsible for invoking `.close()` on the returned
        PubSub object to prevent connection leaks.
        """
        pubsub = self.client.pubsub()
        await pubsub.subscribe(channel)
        return pubsub


class NoOpCacheClient(IAsyncCacheClient):
    """
    Null Object Pattern implementation for the cache interface.
    Used as a safe fallback when caching infrastructure is intentionally disabled
    or entirely unavailable, preventing application crashes.
    """
    
    async def connect(self) -> None: pass
    async def disconnect(self) -> None: pass
    async def ping(self) -> bool: return True
    
    @property
    def client(self) -> Any: return None
    
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None: pass
    async def add(self, key: str, value: Any, ttl: Optional[int] = None) -> bool: return False
    async def get(self, key: str) -> Optional[str]: return None
    async def delete(self, key: str) -> None: pass
    async def exists(self, key: str) -> bool: return False
    async def expire(self, key: str, ttl: int) -> None: pass
    async def incr(self, key: str) -> int: return 1
    
    async def set_json(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> None: pass
    async def get_json(self, key: str) -> Optional[Dict[str, Any]]: return None
    
    async def lpush(self, key: str, *values: str) -> int: return 0
    async def rpush(self, key: str, *values: str) -> int: return 0
    async def lrange(self, key: str, start: int, end: int) -> List[str]: return []
    async def ltrim(self, key: str, start: int, end: int) -> None: pass

    async def sadd(self, key: str, *values: str) -> int: return 0
    async def smembers(self, key: str) -> Set[str]: return set()
    async def srem(self, key: str, *values: str) -> int: return 0
    
    async def hset(self, name: str, mapping: Dict[str, Any]) -> int: return 0
    async def hgetall(self, name: str) -> Dict[str, str]: return {}

    async def publish(self, channel: str, message: str) -> int: return 0
    async def subscribe(self, channel: str) -> Optional[PubSub]: return None


# =========================================================================
# Dependency Injection
# =========================================================================

async def get_cache_from_request(conn: HTTPConnection) -> IAsyncCacheClient:
    """
    FastAPI dependency injection for the cache client.
    Extracts the application-scoped cache instance from the state to ensure
    connection pool sharing across requests.
    """
    state_cache = getattr(conn.app.state, "cache", None)
    if state_cache is None or not isinstance(state_cache, IAsyncCacheClient):
        logger.warning("Cache client not found in app state. Falling back to NoOpCacheClient.")
        return NoOpCacheClient()
    return state_cache


def get_cache_client() -> IAsyncCacheClient:
    """
    Factory function for background tasks or workers operating outside the
    HTTP request lifecycle. Requires explicit lifecycle management (connect/disconnect)
    by the caller.
    """
    redis_url = getattr(settings, 'REDIS_URL', None)
    if not redis_url:
        logger.warning("REDIS_URL missing from settings. Falling back to NoOpCacheClient.")
        return NoOpCacheClient()
        
    return RedisCacheClient(str(redis_url))
