from datetime import datetime,timezone,timedelta
from types import SimpleNamespace
import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlmodel import SQLModel,select
from app.models.user import User
from app.models.enums import NotificationType
from app.models.notification import Notification
from app.models.notification_subscription import NotificationSubscription
from app.api.v1.endpoints import notifications as module

class Adapter:
    def __init__(self,db):self.db=db
    async def execute(self,*args,**kwargs):
        result=self.db.execute(*args,**kwargs)
        # tests explicitly wrote UTC, sqlite reload loses timezone unlike PG19.
        return result
    def add(self,obj):self.db.add(obj)
    async def commit(self):self.db.commit()
    async def refresh(self,obj):self.db.refresh(obj)

@pytest.mark.asyncio
async def test_notification_list_uses_model_rows_and_keeps_user_isolation():
    engine=create_engine('sqlite://');SQLModel.metadata.create_all(engine,tables=[User.__table__,Notification.__table__])
    with Session(engine) as db:
        for i in (1,2):db.add(User(id=i,email=f'u{i}@example.invalid',hashed_password='not-login',full_name='Test'))
        db.add(Notification(user_id=1,title='One',body='Private1',type=NotificationType.SYSTEM_ALERT))
        db.add(Notification(user_id=2,title='Two',body='Private2',type=NotificationType.SYSTEM_ALERT))
        db.commit()
        rows=await module.get_notifications(session=Adapter(db),current_user=SimpleNamespace(id=1))
        assert len(rows)==1 and rows[0].title=='One'


def test_future_timestamp_does_not_render_negative_age():
    assert not module.format_timestamp(datetime.now(timezone.utc)+timedelta(minutes=1)).startswith('-')



def test_historical_naive_time_is_not_silently_assumed_utc():
    assert 'timezone unknown' in module.format_timestamp(datetime(2020,1,2))


def test_read_all_route_is_not_shadowed_by_dynamic_read_route():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app=FastAPI();app.include_router(module.router,prefix='/notifications')
    app.dependency_overrides[module.deps.get_current_active_user]=lambda: SimpleNamespace(id=1)
    class DB:
        async def execute(self,*args):return None
        async def commit(self):return None
    async def db():yield DB()
    app.dependency_overrides[module.get_async_session]=db
    assert TestClient(app).post('/notifications/read-all').status_code==204
