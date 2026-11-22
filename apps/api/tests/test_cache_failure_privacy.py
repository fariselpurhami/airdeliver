from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from redis.exceptions import ConnectionError,RedisError
from app.services.cache_service import with_resilience


@pytest.mark.asyncio
@pytest.mark.parametrize('error',[ConnectionError,RedisError])
async def test_cache_failure_returns_fallback_without_logging_private_arguments(error,caplog):
    class Cache:
        _redis=object()
        @with_resilience(default_factory=lambda:False)
        async def operation(self,key,value):
            raise error('provider exception contains private-provider-content')
    assert await Cache().operation('private-session-key','private-chat-content') is False
    assert 'private-session-key' not in caplog.text
    assert 'private-chat-content' not in caplog.text
    assert 'private-provider-content' not in caplog.text
    assert caplog.records[-1].operation=='operation'


@pytest.mark.asyncio
async def test_json_serialization_also_works_with_documented_stdlib_fallback(monkeypatch):
    import json
    import app.services.cache_service as module
    cache=object.__new__(module.RedisCacheClient)
    cache.set=AsyncMock()
    monkeypatch.setattr(module,'orjson',json)
    await cache.set_json('key',{'message':'text'},ttl=5)
    assert json.loads(cache.set.await_args.args[1])=={'message':'text'}
