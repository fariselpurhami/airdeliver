# apps/api/app/services/notification_service.py

import json
import logging
import asyncio
from pywebpush import webpush, WebPushException
from typing import List
from sqlmodel import select
from app.core.config import settings
from app.models.notification_subscription import NotificationSubscription
from sqlmodel.ext.asyncio.session import AsyncSession

logger = logging.getLogger(__name__)

VAPID_PRIVATE_KEY = settings.VAPID_PRIVATE_KEY
VAPID_PUBLIC_KEY = settings.VAPID_PUBLIC_KEY
VAPID_CLAIMS = {"sub": "mailto:admin@airdeliver.com"}

class NotificationService:
    async def send_web_push(self, db: AsyncSession, user_id: int, title: str, body: str):

        try:
            result = await db.execute(
                select(NotificationSubscription).where(NotificationSubscription.user_id == user_id)
            )
            subscriptions = result.all()

            if not subscriptions:
                return

            loop = asyncio.get_running_loop()
            
            payload = json.dumps({"title": title, "body": body})

            for sub in subscriptions:
                try:
                    subscription_info = sub.subscription_info_json
                    await loop.run_in_executor(
                        None, 
                        lambda: self._safe_webpush(subscription_info, payload)
                    )
                except Exception as e:
                    logger.error(f"Failed to schedule push for user {user_id}: {e}")

        except Exception as e:
             logger.error(f"Error in notification service flow: {e}")

    def _safe_webpush(self, subscription_info, payload):

        try:
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims=VAPID_CLAIMS.copy(),
                timeout=5 
            )
        except WebPushException as e:
            logger.warning(f"WebPush failed: {e}")

        except Exception as e:
             logger.error(f"Unexpected WebPush error: {e}")

    def send_email(self, email_address: str, subject: str, content: str):

        logger.info(f"📧 [MOCK EMAIL] To: {email_address} | Subject: {subject}")

    def send_sms(self, phone_number: str, message: str):

        logger.info(f"📱 [MOCK SMS] To: {phone_number} | Msg: {message}")

notification_service = NotificationService()
