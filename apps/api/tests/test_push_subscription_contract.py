import base64
from types import SimpleNamespace
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlmodel import SQLModel,select
from app.models.user import User
from app.models.notification_subscription import NotificationSubscription
from app.api.v1.endpoints import notifications as module
from tests.test_notification_endpoints import Adapter


def subscription():
    import cryptography.hazmat.primitives.asymmetric.ec as ec
    from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
    public=ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(Encoding.X962,PublicFormat.UncompressedPoint)
    enc=lambda x:base64.urlsafe_b64encode(x).decode().rstrip('=')
    return {'endpoint':'https://push.example.com/subscription/test','keys':{'auth':enc(b'x'*16),'p256dh':enc(public)}}


@pytest.mark.asyncio
async def test_subscribe_stores_object_and_repeat_updates_existing_row():
    engine=create_engine('sqlite://');SQLModel.metadata.create_all(engine,tables=[User.__table__,NotificationSubscription.__table__])
    with Session(engine) as db:
        db.add(User(id=1,email='test@example.invalid',hashed_password='not-login',full_name='Test'));db.commit()
        first=subscription()
        await module.subscribe_to_push_notifications(session=Adapter(db),current_user=SimpleNamespace(id=1),subscription_info=first)
        row=db.execute(select(NotificationSubscription)).scalar_one()
        assert isinstance(row.subscription_info_json,dict)
        second=subscription()
        await module.subscribe_to_push_notifications(session=Adapter(db),current_user=SimpleNamespace(id=1),subscription_info=second)
        assert len(db.execute(select(NotificationSubscription)).scalars().all())==1
        db.expire_all()
        assert row.subscription_info_json==second


@pytest.mark.parametrize('endpoint', ['http://push.example.com/x','https://127.0.0.1/x','https://localhost/x','https://user:password@push.example.com/x','https://push.example.com:8443/x'])
def test_subscription_rejects_unsafe_endpoint_shape(endpoint):
    from app.schemas.notification import PushSubscriptionCreate
    data=subscription();data['endpoint']=endpoint
    with pytest.raises(ValueError):PushSubscriptionCreate.model_validate(data)


def test_subscription_rejects_invalid_encryption_keys():
    from app.schemas.notification import PushSubscriptionCreate
    data=subscription();data['keys']['p256dh']='not-valid-key'
    with pytest.raises(ValueError):PushSubscriptionCreate.model_validate(data)
