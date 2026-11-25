"""Refresh route against real PostgreSQL, using only disposable CI data.

No model/provider calls. Stateful replay policy is deliberately not changed here.
"""
import asyncio
import os
from datetime import timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1.endpoints import auth
from app.core import security
from app.db.session import get_async_session
from app.models.enums import UserRole
from app.models.user import User


@pytest_asyncio.fixture
async def refresh_http(monkeypatch):
    dsn = os.getenv("TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("real disposable PostgreSQL required")
    url = make_url(dsn)
    assert url.drivername == "postgresql+asyncpg"
    assert (url.database or "").startswith("airdeliver_test_")
    assert os.getenv("GITHUB_ACTIONS") == "true", "fixture writes authorized only in disposable GitHub Actions"
    engine = create_async_engine(dsn)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    email = uuid4().hex + "@example.com"
    async with sessions() as db:
        user = User(email=email, hashed_password="offline-test-only", role=UserRole.ADMIN)
        db.add(user)
        await db.commit()
        uid = user.id
    app = FastAPI()
    app.include_router(auth.router, prefix="/auth")
    # Isolate route semantics from the shared limiter's cross-test counters.
    monkeypatch.setattr(auth.limiter, "enabled", False)

    async def db_session():
        async with sessions() as db:
            yield db

    app.dependency_overrides[get_async_session] = db_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="https://test") as client:
            yield client, app, email, sessions
    finally:
        async with sessions() as db:
            await db.execute(delete(User).where(User.id == uid))
            await db.commit()
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize("channel", ["header", "cookie"])
async def test_refresh_real_postgres_http_issues_subject_and_database_role(refresh_http, channel):
    client, _, email, _ = refresh_http
    token = security.create_refresh_token({"sub": email})
    if channel == "cookie":
        client.cookies.set("refresh_token", token)
        response = await client.post("/auth/refresh")
    else:
        response = await client.post("/auth/refresh", headers={"Authorization": "Bearer " + token})
    assert response.status_code == 200, response.text
    assert response.json()["token_type"] == "bearer"
    from app.api.deps import _decode_token_subject
    from app.core.config import settings
    from jose import jwt
    access = response.json()["access_token"]
    assert _decode_token_subject(access, settings) == email
    payload = jwt.decode(access, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["role"] == UserRole.ADMIN.value


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["missing", "garbage", "expired", "access", "unknown"])
async def test_refresh_real_postgres_http_rejection(refresh_http, kind):
    client, _, email, _ = refresh_http
    tokens = {
        "missing": None,
        "garbage": "invalid-token",
        "expired": security.create_refresh_token({"sub": email}, expires_delta=timedelta(seconds=-30)),
        "access": security.create_access_token({"sub": email}),
        "unknown": security.create_refresh_token({"sub": uuid4().hex + "@example.com"}),
    }
    headers = {"Authorization": "Bearer " + tokens[kind]} if tokens[kind] else {}
    response = await client.post("/auth/refresh", headers=headers)
    assert response.status_code == 401
    assert "access_token" not in response.json()
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.asyncio
async def test_refresh_real_postgres_http_concurrent_reuse_preserves_existing_stateless_policy(refresh_http):
    client, _, email, _ = refresh_http
    headers = {"Authorization": "Bearer " + security.create_refresh_token({"sub": email})}
    responses = await asyncio.gather(*(client.post("/auth/refresh", headers=headers) for _ in range(4)))
    assert [r.status_code for r in responses] == [200] * 4
    assert all("access_token" in r.json() for r in responses)
    # Refresh rotation/replay invalidation is the separately held C01 policy.


@pytest.mark.asyncio
async def test_refresh_http_database_outage_never_issues_a_token(refresh_http):
    client, app, email, _ = refresh_http
    class UnavailableSession:
        async def execute(self, statement):
            raise ConnectionError("synthetic unavailable database")
    async def unavailable():
        yield UnavailableSession()
    app.dependency_overrides[get_async_session] = unavailable
    response = await client.post("/auth/refresh", headers={"Authorization": "Bearer " + security.create_refresh_token({"sub": email})})
    assert response.status_code == 500
    assert "access_token" not in response.text


@pytest.mark.asyncio
async def test_refresh_http_cancellation_propagates_without_token_issuance(refresh_http, monkeypatch):
    client, app, email, _ = refresh_http
    entered = asyncio.Event()
    class WaitingSession:
        async def execute(self, statement):
            entered.set()
            await asyncio.Event().wait()
    async def waiting():
        yield WaitingSession()
    app.dependency_overrides[get_async_session] = waiting
    from unittest.mock import Mock
    mint = Mock(wraps=security.create_access_token)
    monkeypatch.setattr(security, "create_access_token", mint)
    task = asyncio.create_task(client.post("/auth/refresh", headers={"Authorization": "Bearer " + security.create_refresh_token({"sub": email})}))
    await asyncio.wait_for(entered.wait(), timeout=5)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    mint.assert_not_called()
