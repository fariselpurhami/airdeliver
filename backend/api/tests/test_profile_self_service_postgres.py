"""Real HTTP + disposable migrated PostgreSQL, never an owner's account."""
import os
from uuid import uuid4
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.api import deps
from app.api.v1.endpoints.users import router
from app.db.session import get_async_session
from app.models.user import User
from app.models.enums import UserRole
from app.core import security

pytestmark = pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'), reason='disposable migrated PostgreSQL required')

@pytest.mark.asyncio
async def test_profile_and_password_http_persist_and_reject_privilege_injection():
    engine = create_async_engine(os.environ['TEST_POSTGRES_DSN'])
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as db:
        assert (await db.execute(text('select current_database()'))).scalar_one().startswith('airdeliver_test_')
        owner = User(email=uuid4().hex+'@example.com', full_name='Original', hashed_password=security.get_password_hash('old-test-password'))
        db.add(owner); await db.commit(); owner_id = owner.id
    app = FastAPI(); app.include_router(router)
    async def dbdep():
        async with sessions() as db: yield db
    async def current():
        async with sessions() as db: return await db.get(User, owner_id)
    app.dependency_overrides[get_async_session] = dbdep
    app.dependency_overrides[deps.get_current_active_user] = current
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
            for payload in [{'role':'admin'}, {'is_active':False}, {'password':'bypass-password'}, {'email':'new@example.com'}]:
                response = await client.put('/me', json=payload)
                assert response.status_code == 422
            response = await client.put('/me', json={'full_name':'Updated','phone_number':'123456','address':'Test address'})
            assert response.status_code == 200 and response.json()['full_name'] == 'Updated'
            assert 'hashed_password' not in response.json()
            assert (await client.post('/me/change-password', json={'current_password':'wrong','new_password':'valid-new-password'})).status_code == 401
            assert (await client.post('/me/change-password', json={'current_password':'old-test-password','new_password':'short'})).status_code == 422
            response = await client.post('/me/change-password', json={'current_password':'old-test-password','new_password':'valid-new-password'})
            assert response.status_code == 200
            assert (await client.post('/me/change-password', json={'current_password':'old-test-password','new_password':'another-password'})).status_code == 401
        async with sessions() as db:
            saved = await db.get(User, owner_id)
            assert saved.full_name == 'Updated' and saved.address == 'Test address' and saved.phone_number == '123456'
            assert saved.role == UserRole.USER and saved.is_active is True
            assert security.verify_password('valid-new-password', saved.hashed_password)
            assert not security.verify_password('old-test-password', saved.hashed_password)
    finally:
        await engine.dispose()

@pytest.mark.asyncio
async def test_self_service_requires_authentication_without_dependency_override():
    app = FastAPI(); app.include_router(router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        assert (await client.get('/me')).status_code == 401
        assert (await client.put('/me', json={'full_name':'Not allowed'})).status_code == 401
        assert (await client.post('/me/change-password', json={'current_password':'x','new_password':'long-enough-password'})).status_code == 401
