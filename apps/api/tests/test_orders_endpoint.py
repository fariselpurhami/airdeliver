# apps/api/tests/test_orders_endpoint.py
"""HTTP tests for GET /api/v1/orders/me: pagination, empty fast-path, error boundary."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.api import deps
from app.main import app


FAKE_USER = SimpleNamespace(id=1, email="user@test.local", is_active=True)


class _CountResult:
    def __init__(self, n):
        self._n = n

    def scalar_one(self):
        return self._n


class _OrdersResult:
    def __init__(self, orders):
        self._orders = orders

    def scalars(self):
        return self

    def all(self):
        return self._orders


class FakeSession:
    """Serves count query then orders query, or raises."""

    def __init__(self, count=0, orders=None, exc=None):
        self._count = count
        self._orders = orders or []
        self._exc = exc

    async def execute(self, statement):
        if self._exc:
            raise self._exc
        # first call is the COUNT, second the page fetch
        if not hasattr(self, "_called"):
            self._called = True
            return _CountResult(self._count)
        return _OrdersResult(self._orders)


@pytest.fixture
def client():
    app.dependency_overrides[deps.get_current_active_user] = lambda: FAKE_USER
    yield TestClient(app)
    app.dependency_overrides.clear()


def _override_session(fake):
    async def _get_session():
        yield fake

    app.dependency_overrides[deps.get_async_session] = _get_session


def test_orders_empty_fast_path(client):
    _override_session(FakeSession(count=0))
    resp = client.get("/api/v1/orders/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0 and body["orders"] == []
    assert body["page"] == 1 and body["limit"] == 10


def test_orders_pagination_bounds_enforced(client):
    _override_session(FakeSession(count=0))
    assert client.get("/api/v1/orders/me?page=0").status_code == 422
    assert client.get("/api/v1/orders/me?limit=0").status_code == 422
    assert client.get("/api/v1/orders/me?limit=101").status_code == 422
    assert client.get("/api/v1/orders/me?page=2&limit=5").status_code == 200


def test_orders_db_error_returns_generic_500(client):
    _override_session(FakeSession(exc=SQLAlchemyError("connection reset by peer")))
    resp = client.get("/api/v1/orders/me")
    assert resp.status_code == 500
    # no infrastructure detail leaks to the client
    assert "connection reset" not in resp.text
    assert "sqlalchemy" not in resp.text.lower()


def test_detail_database_outage_is_generic503(client):
    _override_session(FakeSession(exc=SQLAlchemyError('private-database-connection')))
    response=client.get('/api/v1/orders/me/1')
    assert response.status_code==503 and 'private-database-connection' not in response.text


def test_detail_requires_authentication():
    from fastapi import FastAPI
    from app.api.v1.endpoints.orders import router
    isolated=FastAPI();isolated.include_router(router)
    async def unauthorized():
        from fastapi import HTTPException
        raise HTTPException(status_code=401,detail='Authentication required')
    isolated.dependency_overrides[deps.get_current_active_user]=unauthorized
    async def no_database():yield None
    isolated.dependency_overrides[deps.get_async_session]=no_database
    response=TestClient(isolated).get('/me/1')
    assert response.status_code==401
