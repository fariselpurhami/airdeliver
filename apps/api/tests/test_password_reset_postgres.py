import asyncio
import os
from datetime import datetime,timedelta,timezone
from uuid import uuid4
from types import SimpleNamespace
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from sqlalchemy import text,update
from sqlmodel import select
from fastapi import HTTPException
from app.core.config import settings
from app.core.security import get_password_hash,verify_password,create_access_token
from app.models.user import User
from app.models.password_reset import PasswordResetToken,PasswordResetAudit
from app.services.password_reset_service import issue_reset,consume_reset,delivery_ready
from app.api.deps import _get_user_from_token
pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='disposable PostgreSQL required')

@pytest_asyncio.fixture
async def reset_db():
 settings.PASSWORD_RESET_WEB_ORIGIN='https://shop.example.test'
 engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False)
 async with engine.connect() as db:assert (await db.execute(text('select current_database()'))).scalar_one().startswith('airdeliver_test_')
 async with sessions() as db:
  u=User(email=uuid4().hex+'@example.com',hashed_password=get_password_hash('old-test-password'));db.add(u);await db.commit();uid,email=u.id,u.email
 yield sessions,uid,email
 await engine.dispose()

@pytest.mark.asyncio
async def test_hashed_single_use_reset_revokes_access_and_all_other_links(reset_db):
 sessions,uid,email=reset_db
 async with sessions() as db:
  _,link=await issue_reset(db,email,'test-'+uuid4().hex,settings);raw=link.split('#token=')[1]
  stored=(await db.execute(select(PasswordResetToken).where(PasswordResetToken.user_id==uid))).scalars().one()
  assert stored.token_hash!=raw and len(stored.token_hash)==64
  old=create_access_token({'sub':email,'ver':0})
  assert await consume_reset(db,raw,'new-test-password')
  assert not await consume_reset(db,raw,'second-password')
 async with sessions() as db:
  u=await db.get(User,uid);assert u.auth_version==1 and verify_password('new-test-password',u.hashed_password)
  with pytest.raises(HTTPException):await _get_user_from_token(old,db,settings)
  events=(await db.execute(select(PasswordResetAudit).where(PasswordResetAudit.user_id==uid))).scalars().all();assert {e.event for e in events}=={'reset_requested','reset_completed'}

@pytest.mark.asyncio
async def test_two_transactions_cannot_consume_token_twice(reset_db):
 sessions,uid,email=reset_db
 async with sessions() as db:_,link=await issue_reset(db,email,'test-'+uuid4().hex,settings)
 async def reset():
  async with sessions() as db:return await consume_reset(db,link.split('#token=')[1],'new-test-password')
 assert sorted(await asyncio.gather(reset(),reset()))==[False,True]

@pytest.mark.asyncio
async def test_expired_and_superseded_tokens_fail(reset_db):
 sessions,uid,email=reset_db
 async with sessions() as db:
  _,a=await issue_reset(db,email,'ip-a',settings);_,b=await issue_reset(db,email,'ip-b',settings)
  assert not await consume_reset(db,a.split('#token=')[1],'new-password')
  await db.execute(update(PasswordResetToken).where(PasswordResetToken.user_id==uid).values(expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)));await db.commit()
  assert not await consume_reset(db,b.split('#token=')[1],'new-password')

@pytest.mark.asyncio
async def test_absent_account_and_email_quota_do_not_issue(reset_db):
 sessions,uid,email=reset_db
 async with sessions() as db:
  assert await issue_reset(db,uuid4().hex+'@example.com','absent',settings) is None
  for i in range(3):assert await issue_reset(db,email,'new-ip-'+str(i),settings)
  assert await issue_reset(db,email,'different-ip',settings) is None

def test_delivery_is_disabled_without_complete_https_configuration():
 assert not delivery_ready(settings)

@pytest.mark.asyncio
async def test_encrypted_outbox_survives_failed_send_and_scrubs_on_success(reset_db):
 from app.services.password_reset_service import dispatch_pending
 from app.models.password_reset import PasswordResetDelivery
 from pydantic import SecretStr
 sessions,uid,email=reset_db
 configured=settings.model_copy(update={'PASSWORD_RESET_ENABLED':True,'PASSWORD_RESET_WEB_ORIGIN':'https://shop.example.test','RESET_SMTP_HOST':'mail.example.test','RESET_SMTP_USERNAME':'fixture','RESET_SMTP_PASSWORD':SecretStr('fixture-not-real'),'RESET_EMAIL_FROM':'security@example.test'})
 async with sessions() as db:
  await db.execute(update(PasswordResetDelivery).values(expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)));await db.commit()
  _,link=await issue_reset(db,email,'outbox-'+uuid4().hex,configured)
  row=(await db.execute(select(PasswordResetDelivery).where(PasswordResetDelivery.user_id==uid))).scalars().one()
  assert link not in row.encrypted_payload and email not in row.encrypted_payload
  def fail(*args):raise OSError('fixture failure')
  assert await dispatch_pending(db,configured,fail)==0
  received=[]
  assert await dispatch_pending(db,configured,lambda *args:received.append(args))==1
  assert received[0][0:2]==(email,link)
  await db.refresh(row);assert row.encrypted_payload=='' and row.sent_at and row.attempts==2

@pytest.mark.asyncio
async def test_http_real_database_uniform_requests_and_confirmation(reset_db):
 from fastapi import FastAPI
 from httpx import AsyncClient,ASGITransport
 from pydantic import SecretStr
 from app.api.v1.endpoints.password_reset import router
 from app.core.config import get_core_settings
 from app.db.session import get_async_session
 from app.models.password_reset import PasswordResetDelivery
 sessions,uid,email=reset_db
 configured=settings.model_copy(update={'PASSWORD_RESET_ENABLED':True,'PASSWORD_RESET_WEB_ORIGIN':'https://shop.example.test','RESET_SMTP_HOST':'mail.example.test','RESET_SMTP_USERNAME':'fixture','RESET_SMTP_PASSWORD':SecretStr('fixture-not-real'),'RESET_EMAIL_FROM':'security@example.test'})
 app=FastAPI();app.include_router(router)
 async def dbdep():
  async with sessions() as db:yield db
 app.dependency_overrides[get_async_session]=dbdep
 app.dependency_overrides[get_core_settings]=lambda:configured
 async with AsyncClient(transport=ASGITransport(app=app,client=('192.0.2.22',123)),base_url='http://test') as client:
  a=await client.post('/password-reset/request',json={'email':email})
  b=await client.post('/password-reset/request',json={'email':uuid4().hex+'@example.com'})
  assert a.status_code==b.status_code==202 and a.json()==b.json()
  assert a.headers['cache-control']=='no-store'
  async with sessions() as db:
   _,link=await issue_reset(db,email,'http-test',configured)
  result=await client.post('/password-reset/confirm',json={'token':link.split('#token=')[1],'password':'new-http-password'})
  assert result.status_code==200
  replay=await client.post('/password-reset/confirm',json={'token':link.split('#token=')[1],'password':'another-password'})
  assert replay.status_code==400

@pytest.mark.asyncio
async def test_refresh_token_version_revoked_after_reset(reset_db):
 from app.core.security import create_refresh_token
 from app.api.v1.endpoints.auth import refresh_access_token
 from starlette.requests import Request
 sessions,uid,email=reset_db
 async with sessions() as db:
  old=create_refresh_token({'sub':email,'ver':0})
  _,link=await issue_reset(db,email,'refresh-test',settings)
  assert await consume_reset(db,link.split('#token=')[1],'new-refresh-password')
  with pytest.raises(HTTPException) as error:
   await refresh_access_token.__wrapped__(request=Request({'type':'http','method':'POST','headers':[],'path':'/','client':('192.0.2.1',1)}),refresh_token=old,db=db)
  assert error.value.status_code==401


def configured_delivery():
 from pydantic import SecretStr
 return settings.model_copy(update={'PASSWORD_RESET_ENABLED':True,'PASSWORD_RESET_WEB_ORIGIN':'https://shop.example.test','RESET_SMTP_HOST':'mail.example.test','RESET_SMTP_USERNAME':'fixture','RESET_SMTP_PASSWORD':SecretStr('fixture-not-real'),'RESET_EMAIL_FROM':'security@example.test'})

@pytest.mark.asyncio
async def test_concurrent_workers_and_reset_have_consistent_lock_order(reset_db):
 import threading
 from app.services.password_reset_service import dispatch_pending
 from app.models.password_reset import PasswordResetDelivery
 sessions,uid,email=reset_db;cfg=configured_delivery()
 async with sessions() as db:
  await db.execute(update(PasswordResetDelivery).values(expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)));await db.commit()
  _,link=await issue_reset(db,email,'worker-lock-'+uuid4().hex,cfg)
 entered=threading.Event();release=threading.Event();received=[]
 def sender(*args):
  received.append(args)
  entered.set()
  assert release.wait(5)
 async def worker():
  async with sessions() as db:return await dispatch_pending(db,cfg,sender)
 async def reset():
  async with sessions() as db:return await consume_reset(db,link.split('#token=')[1],'new-worker-test-password')
 first=asyncio.create_task(worker())
 try:
  assert await asyncio.to_thread(entered.wait,5)
  second=asyncio.create_task(worker())
  assert await asyncio.wait_for(second,2)==0
  reset_task=asyncio.create_task(reset())
  await asyncio.sleep(.05)
  assert not reset_task.done()
 finally:release.set()
 assert await asyncio.wait_for(first,5)==1
 assert await asyncio.wait_for(reset_task,5)
 assert len(received)==1
 async with sessions() as db:
  assert await dispatch_pending(db,cfg,sender)==0
  user=await db.get(User,uid);assert user.auth_version==1

@pytest.mark.asyncio
async def test_final_delivery_failure_scrubs_retry_secret(reset_db):
 from app.services.password_reset_service import dispatch_pending
 from app.models.password_reset import PasswordResetDelivery
 sessions,uid,email=reset_db;cfg=configured_delivery()
 async with sessions() as db:
  await db.execute(update(PasswordResetDelivery).values(expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)));await db.commit()
  await issue_reset(db,email,'final-failure-'+uuid4().hex,cfg)
  await db.execute(update(PasswordResetDelivery).where(PasswordResetDelivery.user_id==uid).values(attempts=4));await db.commit()
  def fail(*args):raise OSError('fixture failure')
  assert await dispatch_pending(db,cfg,fail)==0
  row=(await db.execute(select(PasswordResetDelivery).where(PasswordResetDelivery.user_id==uid))).scalars().one()
  assert row.attempts==5 and not row.encrypted_payload
  events=(await db.execute(select(PasswordResetAudit).where(PasswordResetAudit.user_id==uid))).scalars().all()
  assert 'delivery_exhausted' in {event.event for event in events}
  assert await dispatch_pending(db,cfg,fail)==0


@pytest.mark.asyncio
async def test_password_change_rechecks_fresh_password_after_concurrent_reset(reset_db):
 from app.api.v1.endpoints.users import change_user_password,ChangePasswordRequest
 sessions,uid,email=reset_db
 async with sessions() as stale:
  before_reset=await stale.get(User,uid)
  async with sessions() as db:
   _,link=await issue_reset(db,email,'change-race-'+uuid4().hex,settings)
   assert await consume_reset(db,link.split('#token=')[1],'reset-won-password')
  with pytest.raises(HTTPException) as error:
   await change_user_password(session=stale,current_user=before_reset,password_data=ChangePasswordRequest(current_password='old-test-password',new_password='must-not-overwrite'))
  assert error.value.status_code==401
  await stale.rollback()
 async with sessions() as db:
  user=await db.get(User,uid)
  assert user.auth_version==1 and verify_password('reset-won-password',user.hashed_password)
  assert await change_user_password(session=db,current_user=user,password_data=ChangePasswordRequest(current_password='reset-won-password',new_password='legitimate-new-password'))
  await db.refresh(user)
  assert user.auth_version==2 and verify_password('legitimate-new-password',user.hashed_password)
