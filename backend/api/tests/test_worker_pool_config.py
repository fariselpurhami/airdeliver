"""Worker infrastructure must honor the same bounded DB pools as the API."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from app.services.orchestration import worker_entrypoint as worker


@pytest.mark.asyncio
async def test_worker_uses_configured_database_pool(monkeypatch):
    settings = SimpleNamespace(
        DATABASE_URI="postgresql+asyncpg://test", REDIS_URL="redis://test",
        DB_POOL_SIZE=3, DB_MAX_OVERFLOW=5)
    engine_factory = Mock(return_value=object())
    cache = SimpleNamespace(connect=AsyncMock())
    client = SimpleNamespace(aclose=AsyncMock())
    monkeypatch.setattr(worker, "get_core_settings", lambda: settings)
    monkeypatch.setattr(worker, "create_async_engine", engine_factory)
    monkeypatch.setattr(worker, "sessionmaker", Mock())
    monkeypatch.setattr(worker, "RedisCacheClient", Mock(return_value=cache))
    monkeypatch.setattr(worker.httpx, "AsyncClient", Mock(return_value=client))
    runtime = worker.WorkerRuntime()
    await runtime.initialize_infrastructure()
    assert engine_factory.call_args.kwargs["pool_size"] == 3
    assert engine_factory.call_args.kwargs["max_overflow"] == 5
