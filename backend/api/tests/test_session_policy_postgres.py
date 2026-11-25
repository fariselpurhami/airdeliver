"""C01 transaction semantics against authorized disposable PostgreSQL only.

Preparation service is deliberately not wired to existing auth endpoints.
"""
import asyncio
import hashlib
import os
from datetime import datetime,timedelta,timezone
from uuid import uuid4
import pytest
import pytest_asyncio
from sqlalchemy import delete
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.models.user import User
from app.models.auth_session import AuthSession,RefreshCredential
from app.services.session_policy import SessionPolicy,SessionRejected

@pytest_asyncio.fixture
async def policy_store():
    dsn=os.getenv('TEST_POSTGRES_DSN')
    if not dsn:pytest.skip('authorized disposable PostgreSQL required')
    url=make_url(dsn)
    assert url.drivername=='postgresql+asyncpg' and url.database.startswith('airdeliver_test_')
    assert os.getenv('GITHUB_ACTIONS')=='true'
    engine=create_async_engine(dsn);factory=async_sessionmaker(engine,expire_on_commit=False)
    async with factory() as db:
        user=User(email=uuid4().hex+'@example.com',hashed_password='isolated-policy-only');db.add(user);await db.commit();uid=user.id
    try:yield factory,uid
    finally:
        async with factory() as db:
            ids=__import__('sqlalchemy').select(AuthSession.id).where(AuthSession.user_id==uid)
            await db.execute(delete(RefreshCredential).where(RefreshCredential.session_id.in_(ids)))
            await db.execute(delete(AuthSession).where(AuthSession.user_id==uid));await db.execute(delete(User).where(User.id==uid));await db.commit()
        await engine.dispose()

async def issue(factory,uid):
    async with factory() as db:return await SessionPolicy(db).issue(uid,datetime.now(timezone.utc)+timedelta(minutes=10))

@pytest.mark.asyncio
async def test_rotation_is_single_use_and_replay_revokes_the_whole_family(policy_store):
    factory,uid=policy_store;first=await issue(factory,uid)
    async with factory() as db:second=await SessionPolicy(db).rotate(uid,first.session_id,first.refresh_token)
    assert second.refresh_token!=first.refresh_token and second.expires_at==first.expires_at
    async with factory() as db:
        with pytest.raises(SessionRejected):await SessionPolicy(db).rotate(uid,first.session_id,first.refresh_token)
    async with factory() as db:
        with pytest.raises(SessionRejected):await SessionPolicy(db).rotate(uid,second.session_id,second.refresh_token)

@pytest.mark.asyncio
async def test_parallel_reuse_has_one_winner_and_then_revokes_descendant(policy_store):
    factory,uid=policy_store;first=await issue(factory,uid)
    async def rotate():
        async with factory() as db:
            try:return await SessionPolicy(db).rotate(uid,first.session_id,first.refresh_token)
            except SessionRejected:return None
    results=await asyncio.gather(*[rotate() for _ in range(4)])
    winners=[r for r in results if r is not None];assert len(winners)==1
    async with factory() as db:
        with pytest.raises(SessionRejected):await SessionPolicy(db).rotate(uid,first.session_id,winners[0].refresh_token)

@pytest.mark.asyncio
async def test_logout_only_current_session_disable_all_and_reenable_does_not_restore(policy_store):
    factory,uid=policy_store;a=await issue(factory,uid);b=await issue(factory,uid)
    async with factory() as db:await SessionPolicy(db).logout(uid,a.session_id)
    async with factory() as db:
        with pytest.raises(SessionRejected):await SessionPolicy(db).rotate(uid,a.session_id,a.refresh_token)
    async with factory() as db:b2=await SessionPolicy(db).rotate(uid,b.session_id,b.refresh_token)
    async with factory() as db:await SessionPolicy(db).disable(uid)
    async with factory() as db:
        user=await db.get(User,uid);user.is_active=True;db.add(user);await db.commit()
    async with factory() as db:
        with pytest.raises(SessionRejected):await SessionPolicy(db).rotate(uid,b2.session_id,b2.refresh_token)

@pytest.mark.asyncio
async def test_foreign_or_forged_token_cannot_revoke_valid_session(policy_store):
    factory,uid=policy_store;a=await issue(factory,uid)
    async with factory() as db:
        with pytest.raises(SessionRejected):await SessionPolicy(db).rotate(uid,a.session_id,'unrecognized-opaque-token')
    async with factory() as db:
        with pytest.raises(SessionRejected):await SessionPolicy(db).rotate(uid+999999,a.session_id,a.refresh_token)
    async with factory() as db:assert await SessionPolicy(db).rotate(uid,a.session_id,a.refresh_token)

@pytest.mark.asyncio
async def test_only_digest_is_stored_and_revocation_blocks_access_check(policy_store):
    factory,uid=policy_store;a=await issue(factory,uid)
    async with factory() as db:
        row=await db.get(RefreshCredential,hashlib.sha256(a.refresh_token.encode()).hexdigest())
        assert row is not None and a.refresh_token not in str(row.model_dump())
        assert await SessionPolicy(db).is_active(uid,a.session_id)
    async with factory() as db:await SessionPolicy(db).logout(uid,a.session_id)
    async with factory() as db:assert not await SessionPolicy(db).is_active(uid,a.session_id)
