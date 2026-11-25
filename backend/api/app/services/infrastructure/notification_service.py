"""Delivery results must reflect a real adapter outcome, never mock success."""
import asyncio
from dataclasses import dataclass
import json
import logging
from pywebpush import webpush,WebPushException
from sqlmodel import select
from app.core.config import get_core_settings
from app.models.notification_subscription import NotificationSubscription
from sqlmodel.ext.asyncio.session import AsyncSession

logger=logging.getLogger('app.services.notification_service')


class NotificationUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class PushResult:
    sent: int=0
    failed: int=0
    subscriptions: int=0


class NotificationService:
    async def send_web_push(self,db: AsyncSession,user_id: int,title: str,body: str) -> PushResult:
        if type(user_id) is not int or user_id<=0:raise ValueError('Invalid notification subject')
        if not isinstance(title,str) or not isinstance(body,str):raise ValueError('Push text must be strings')
        payload=json.dumps({'title':title,'body':body})
        if len(payload.encode())>3072:raise ValueError('Push payload exceeds application limit')
        # A real SQLAlchemy result contains Row wrappers; materialize model scalars.
        subscriptions=(await db.execute(select(NotificationSubscription).where(NotificationSubscription.user_id==user_id))).scalars().all()
        sent=failed=0
        for sub in subscriptions:
            # Each call is awaited before the next, avoiding a closure capturing
            # another subscriber's data. Provider details/recipient are not logged.
            accepted=await asyncio.to_thread(self._safe_webpush,sub.subscription_info_json,payload)
            sent+=int(accepted is True)
            failed+=int(accepted is not True)
        return PushResult(sent=sent,failed=failed,subscriptions=len(subscriptions))

    def _safe_webpush(self,subscription_info,payload) -> bool:
        settings=get_core_settings()
        private=settings.VAPID_PRIVATE_KEY
        if hasattr(private,'get_secret_value'):private=private.get_secret_value()
        if not private:raise NotificationUnavailable('Web Push VAPID private key is not configured')
        try:
            webpush(subscription_info=subscription_info,data=payload,vapid_private_key=private,
                    vapid_claims={'sub':'mailto:admin@airdeliver.com'},timeout=5)
        except WebPushException:
            logger.warning('Push provider rejected or failed delivery')
            return False
        return True

    def send_email(self,email_address: str,subject: str,content: str):
        # Preserve the adapter boundary; no fake receipt or PII-bearing log.
        raise NotificationUnavailable('Email delivery adapter is not configured')

    def send_sms(self,phone_number: str,message: str):
        raise NotificationUnavailable('SMS delivery adapter is not configured')


notification_service=NotificationService()
