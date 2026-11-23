import os
from uuid import uuid4
import pytest
from fastapi import FastAPI
from httpx import AsyncClient,ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.api.v1.endpoints import notifications as module
from app.models.user import User
from app.models.notification import Notification
from app.models.enums import NotificationType
pytestmark=pytest.mark.skipif(not os.getenv('TEST_POSTGRES_DSN'),reason='disposable PostgreSQL required')

@pytest.mark.asyncio
async def test_notification_history_older_than100_and_owner_scoped():
 engine=create_async_engine(os.environ['TEST_POSTGRES_DSN']);sessions=async_sessionmaker(engine,expire_on_commit=False)
 async with sessions() as db:
  a=User(email=uuid4().hex+'@example.test',hashed_password='fixture');b=User(email=uuid4().hex+'@example.test',hashed_password='fixture');db.add_all([a,b]);await db.commit()
  db.add_all([Notification(user_id=a.id,title=f'Fixture{i}',body='Order notice',type=NotificationType.ORDER_UPDATE,meta={'cta':'/tracking/7'}) for i in range(105)])
  db.add(Notification(user_id=b.id,title='Other account',body='private',type=NotificationType.SECURITY));await db.commit()
 app=FastAPI();app.include_router(module.router,prefix="/notifications")
 async def dbdep():
  async with sessions() as db:yield db
 app.dependency_overrides[module.get_async_session]=dbdep
 app.dependency_overrides[module.deps.get_current_active_user]=lambda:a
 try:
  async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
   first=await client.get('/notifications/history?page=1&limit=100');second=await client.get('/notifications/history?page=2&limit=100')
   assert first.status_code==second.status_code==200 and first.headers['cache-control']=='no-store'
   assert first.json()['total']==105 and len(first.json()['items'])==100 and len(second.json()['items'])==5
   ids=[n['id'] for n in first.json()['items']+second.json()['items']];assert len(set(ids))==105
   assert all(n['title']!='Other account' and n['cta']=='/tracking/7' for n in first.json()['items'])
   for query in ['page=0','limit=101','limit=0']:
    assert (await client.get('/notifications/history?'+query)).status_code==422
 finally:await engine.dispose()
