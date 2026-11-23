"""Self-only HTTP surface, with controlled auth/database dependencies."""
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api import deps
from app.db.session import get_async_session
from app.api.v1.endpoints import customer_memory
from app.core.config import get_core_settings


@pytest.fixture
def client(monkeypatch):
    service=SimpleNamespace(export=AsyncMock(return_value={'preferences':[]}),set_consent=AsyncMock())
    monkeypatch.setattr(customer_memory,'CustomerMemoryService',lambda db:service)
    async def session():yield object()
    app.dependency_overrides[get_async_session]=session
    app.dependency_overrides[deps.get_current_active_user]=lambda:SimpleNamespace(id=17)
    yield TestClient(app),service
    app.dependency_overrides.clear()


def test_export_has_no_customer_id_selector(client):
    client,service=client
    result=client.get('/api/v1/users/me/memory?user_id=99')
    assert result.status_code==200
    assert result.headers['cache-control']=='no-store'
    service.export.assert_awaited_once_with(17)


def test_delete_revokes_only_authenticated_customers_memory(client):
    client,service=client
    result=client.delete('/api/v1/users/me/memory')
    assert result.status_code==200
    service.set_consent.assert_awaited_once_with(17,False)
    assert 'recent chat history' in result.json()['scope']


def test_optin_requires_enabled_environment_and_strict_contract(client,monkeypatch):
    client,service=client
    monkeypatch.setattr(get_core_settings(),'CUSTOMER_MEMORY_ENABLED',False)
    assert client.put('/api/v1/users/me/memory/consent',json={'enabled':True}).status_code==503
    service.set_consent.assert_not_awaited()
    assert client.put('/api/v1/users/me/memory/consent',json={'enabled':'true'}).status_code==422
    assert client.put('/api/v1/users/me/memory/consent',json={'enabled':True,'user_id':99}).status_code==422
    monkeypatch.setattr(get_core_settings(),'CUSTOMER_MEMORY_ENABLED',True)
    assert client.put('/api/v1/users/me/memory/consent',json={'enabled':True}).status_code==200
    service.set_consent.assert_awaited_once_with(17,True)


def test_memory_requires_real_authentication_without_override(client):
    client,_=client
    app.dependency_overrides.pop(deps.get_current_active_user)
    assert client.get('/api/v1/users/me/memory').status_code in (401,403)
