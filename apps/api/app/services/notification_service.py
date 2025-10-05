# file: apps/api/app/services/notification_service.py
# version: 1.0.0
# date: 2025-09-23
# author: Gemini

import json
from pywebpush import webpush
from typing import List
from sqlmodel import Session, select

from app.core.config import settings
from app.models.notification_subscription import NotificationSubscription

VAPID_PRIVATE_KEY = settings.VAPID_PRIVATE_KEY # Add to config
VAPID_PUBLIC_KEY = settings.VAPID_PUBLIC_KEY # Add to config
VAPID_CLAIMS = {"sub": "mailto:admin@airdeliver.com"}

class NotificationService:
    def send_web_push(self, db: Session, user_id: int, title: str, body: str):
        subscriptions = db.exec(
            select(NotificationSubscription).where(NotificationSubscription.user_id == user_id)
        ).all()

        for sub in subscriptions:
            try:
                subscription_info = json.loads(sub.subscription_info_json)
                webpush(
                    subscription_info=subscription_info,
                    data=json.dumps({"title": title, "body": body}),
                    vapid_private_key=VAPID_PRIVATE_KEY,
                    vapid_claims=VAPID_CLAIMS.copy()
                )
            except Exception as e:
                print(f"Error sending push notification: {e}")

    def send_email(self, email_address: str, subject: str, content: str):
        # MOCK: In production, integrate with a service like SendGrid or Mailgun
        print("-" * 20)
        print(f"SENDING EMAIL to {email_address}")
        print(f"Subject: {subject}")
        print(f"Content: {content}")
        print("-" * 20)

    def send_sms(self, phone_number: str, message: str):
        # MOCK: In production, integrate with a service like Twilio
        print("-" * 20)
        print(f"SENDING SMS to {phone_number}")
        print(f"Message: {message}")
        print("-" * 20)
        
notification_service = NotificationService()
