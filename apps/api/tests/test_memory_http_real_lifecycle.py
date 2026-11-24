"""Mounted memory endpoints plus canonical SQL, not an in-memory service stub."""
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from httpx import AsyncClient,ASGITransport
from app.main import app
from app.api import deps
from app.db.session import get_async_session
from app.services.customer_memory_service import CustomerMemoryService
from tests.test_customer_memory_postgres import memory_db

@pytest.mark.asyncio
async def test_mounted_self_service_consent_collect_export_cross_owner_and_delete(memory_db):
    sessions,(uid,other)=memory_db;active={'id':uid}
    async def db_session():
        async with sessions() as db:yield db
    app.dependency_overrides[get_async_session]=db_session
    app.dependency_overrides[deps.get_current_active_user]=lambda:SimpleNamespace(id=active['id'])
    llm=SimpleNamespace(extract_shopping_preferences=AsyncMock(return_value={'category':'color','value':'blue','evidence':'I prefer blue'}))
    try:
        async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
            assert (await client.put('/api/v1/users/me/memory/consent',json={'enabled':True,'user_id':other})).status_code==422
            async with sessions() as db:assert not await CustomerMemoryService(db).collect(uid,'I prefer blue',llm)
            llm.extract_shopping_preferences.assert_not_awaited()
            assert (await client.put('/api/v1/users/me/memory/consent',json={'enabled':True})).json()['enabled'] is True
            async with sessions() as db:assert await CustomerMemoryService(db).collect(uid,'I prefer blue',llm)
            response=await client.get('/api/v1/users/me/memory?user_id='+str(other))
            assert response.headers['cache-control']=='no-store'
            assert response.json()['enabled'] is True
            assert response.json()['preferences'][0]['value']=='blue'
            active['id']=other
            assert (await client.get('/api/v1/users/me/memory?user_id='+str(uid))).json()['preferences']==[]
            await client.delete('/api/v1/users/me/memory')
            async with sessions() as db:assert await CustomerMemoryService(db).recall(uid)==['Customer explicitly prefers color: blue']
            active['id']=uid
            deleted=await client.delete('/api/v1/users/me/memory')
            assert deleted.json()['deleted'] is True
            async with sessions() as db:
                memory=CustomerMemoryService(db)
                assert await memory.recall(uid)==[]
                assert not await memory.collect(uid,'I prefer blue',llm)
            assert (await client.get('/api/v1/users/me/memory')).json()['preferences']==[]
            assert (await client.put('/api/v1/users/me/memory/consent',json={'enabled':True})).status_code==200
            assert (await client.get('/api/v1/users/me/memory')).json()['preferences']==[]
    finally:
        app.dependency_overrides.clear()
