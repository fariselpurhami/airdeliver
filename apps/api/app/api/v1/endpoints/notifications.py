# file: apps/api/app/api/v1/endpoints/notifications.py
# version: 1.0.0
# date: 2025-09-23
# author: Gemini

from fastapi import APIRouter, Depends, Body
from sqlmodel import Session
from typing import Any

from app.db.session import get_session
from app.api import deps
from app.models.user import User
from app.models.notification_subscription import NotificationSubscription

router = APIRouter()

@router.post("/subscribe")
def subscribe_to_push_notifications(
    *,
    session: Session = Depends(get_session),
    current_user: User = Depends(deps.get_current_active_user),
    subscription_info: Any = Body(...)
):
    """
    Save a user's web push subscription info.
    """
    import json
    db_subscription = NotificationSubscription(
        user_id=current_user.id,
        subscription_info_json=json.dumps(subscription_info)
    )
    session.add(db_subscription)
    session.commit()
    return {"status": "subscribed"}

