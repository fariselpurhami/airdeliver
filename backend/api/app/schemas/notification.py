# backend/api/app/schemas/notification.py

from sqlmodel import SQLModel
from datetime import datetime
from app.models.enums import NotificationType

class NotificationRead(SQLModel):
    id: int
    title: str
    body: str
    type: NotificationType
    read: bool
    cta: str | None
    created_at: datetime
    timestamp: str 

class NotificationCreate(SQLModel):
    user_id: int
    title: str
    body: str
    type: NotificationType = NotificationType.SYSTEM_ALERT
    cta: str | None = None
    meta: dict | None = None


from pydantic import BaseModel,ConfigDict,Field,field_validator,model_validator
import base64
import ipaddress
from urllib.parse import urlsplit
from cryptography.hazmat.primitives.asymmetric import ec


class PushKeys(BaseModel):
    model_config=ConfigDict(extra='forbid')
    p256dh: str=Field(min_length=1,max_length=128,pattern=r'^[A-Za-z0-9_-]+={0,2}$')
    auth: str=Field(min_length=1,max_length=32,pattern=r'^[A-Za-z0-9_-]+={0,2}$')

    @model_validator(mode='after')
    def valid_key_material(self):
        try:
            auth=base64.urlsafe_b64decode(self.auth+'='*(-len(self.auth)%4))
            public=base64.urlsafe_b64decode(self.p256dh+'='*(-len(self.p256dh)%4))
            if len(auth)!=16 or len(public)!=65 or public[0]!=4:raise ValueError()
            ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(),public)
        except (ValueError,TypeError) as exc:
            raise ValueError('Invalid Web Push key material') from exc
        return self


class PushSubscriptionCreate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    endpoint: str=Field(min_length=10,max_length=2048)
    keys: PushKeys
    expirationTime: int | None=Field(default=None,ge=0)

    @field_validator('endpoint')
    @classmethod
    def https_public_hostname(cls,value):
        try:
            url=urlsplit(value);host=url.hostname
            if (url.scheme!='https' or not host or url.username or url.password or url.fragment
                    or url.port not in (None,443) or any(x.isspace() for x in value)):
                raise ValueError()
            if '.' not in host or host.endswith(('.localhost','.local','.internal')):
                raise ValueError()
            try:ipaddress.ip_address(host)
            except ValueError:pass
            else:raise ValueError('IP endpoints are not supported')
        except ValueError as exc:
            raise ValueError('Web Push requires an HTTPS public hostname on port443') from exc
        return value
