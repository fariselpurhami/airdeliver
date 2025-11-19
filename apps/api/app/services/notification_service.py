# apps/api/app/services/notification_service.py

import json
from pywebpush import webpush
from typing import List
from sqlmodel import select
from app.core.config import settings
from app.models.notification_subscription import NotificationSubscription
from sqlmodel.ext.asyncio.session import AsyncSession

VAPID_PRIVATE_KEY = settings.VAPID_PRIVATE_KEY
VAPID_PUBLIC_KEY = settings.VAPID_PUBLIC_KEY
VAPID_CLAIMS = {"sub": "mailto:admin@airdeliver.com"}

class NotificationService:
    async def send_web_push(self, db: AsyncSession, user_id: int, title: str, body: str):
        result = await db.exec(
            select(NotificationSubscription).where(NotificationSubscription.user_id == user_id)
        )
        subscriptions = result.all()

        for sub in subscriptions:
            try:
                subscription_info = sub.subscription_info_json
                webpush(
                    subscription_info=subscription_info,
                    data=json.dumps({"title": title, "body": body}),
                    vapid_private_key=VAPID_PRIVATE_KEY,
                    vapid_claims=VAPID_CLAIMS.copy()
                )
            except Exception as e:
                print(f"Error sending push notification: {e}")

    def send_email(self, email_address: str, subject: str, content: str):
        print("-" * 20)
        print(f"SENDING EMAIL to {email_address}")
        print(f"Subject: {subject}")
        print(f"Content: {content}")
        print("-" * 20)

    def send_sms(self, phone_number: str, message: str):
        print("-" * 20)
        print(f"SENDING SMS to {phone_number}")
        print(f"Message: {message}")
        print("-" * 20)

notification_service = NotificationService()
