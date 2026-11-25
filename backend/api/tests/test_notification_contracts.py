import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock,Mock
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlmodel import SQLModel
from app.models.notification_subscription import NotificationSubscription
from app.models.user import User
from app.services.notification_service import NotificationService

@pytest.mark.asyncio
async def test_push_reads_real_orm_scalar_not_row(monkeypatch):
    from app.services import notification_service as module
    engine=create_engine('sqlite://')
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(User(id=41,email='push-test@example.invalid',hashed_password='not-a-login',full_name='Test'))
        db.add(NotificationSubscription(user_id=41,subscription_info_json={'endpoint':'https://fcm.googleapis.com/fcm/send/test','keys':{'p256dh':'test','auth':'test'}}))
        db.commit()
        class Adapter:
            async def execute(self,statement):return db.execute(statement)
        service=NotificationService()
        calls=[]
        def send(info,payload):calls.append(info);return True
        monkeypatch.setattr(service,'_safe_webpush',send)
        result=await service.send_web_push(Adapter(),41,'Title','Body')
        assert len(calls)==1
        assert result.sent==1 and result.failed==0


def test_unconfigured_email_and_sms_do_not_claim_delivery_or_log_private_payload(caplog):
    from app.services.notification_service import NotificationUnavailable
    with caplog.at_level(logging.INFO):
        for method,args in [('send_email',('private@example.invalid','private subject','private body')),('send_sms',('+15550000000','private body'))]:
            with pytest.raises(NotificationUnavailable):getattr(NotificationService(),method)(*args)
    assert 'private' not in caplog.text and '+1555' not in caplog.text
