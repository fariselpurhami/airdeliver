# apps/api/app/api/v1/endpoints/notifications.py 

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlmodel import Session, select, update
from typing import Any, List
from app.db.session import get_session
from app.api import deps
from app.models.user import User
from app.models.notification import Notification 
from app.schemas.notification import NotificationRead 
from app.models.notification_subscription import NotificationSubscription
from datetime import datetime, timezone

router = APIRouter()

def format_timestamp(dt: datetime) -> str:

    now = datetime.now(timezone.utc)
    diff = now - dt
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return f"{int(seconds)} seconds ago"
    elif seconds < 3600:
        return f"{int(seconds / 60)} min ago"
    elif seconds < 86400:
        return f"{int(seconds / 3600)} hours ago"
    elif seconds < 604800: # 7 days
        return f"{int(seconds / 86400)} days ago"
    else:
        return dt.strftime("%Y-%m-%d")

@router.get(
    "/", 
    response_model=List[NotificationRead]
)
def get_notifications(
    *,
    session: Session = Depends(get_session),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Get all notifications for the current user.
    """
    statement = (
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc()) 
        .limit(100) 
    )
    notifications = session.exec(statement).all()
    
    response_notifications = []
    for notif in notifications:
        notif_read = NotificationRead.model_validate(notif)
        notif_read.timestamp = format_timestamp(notif.created_at)
        response_notifications.append(notif_read)
        
    return response_notifications


@router.post(
    "/{id}/read", 
    response_model=NotificationRead
)
def mark_notification_as_read(
    *,
    session: Session = Depends(get_session),
    current_user: User = Depends(deps.get_current_active_user),
    id: int
):

    notif = session.get(Notification, id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notif.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized") # Forbidden
        
    notif.read = True
    session.add(notif)
    session.commit()
    session.refresh(notif)
    notif_read = NotificationRead.model_validate(notif)
    notif_read.timestamp = format_timestamp(notif.created_at)
    return notif_read


@router.post(
    "/read-all",
    status_code=status.HTTP_204_NO_CONTENT
)
def mark_all_notifications_as_read(
    *,
    session: Session = Depends(get_session),
    current_user: User = Depends(deps.get_current_active_user),
):

    statement = (
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.read == False)
        .values(read=True)
    )
    session.exec(statement)
    session.commit()
    return None 


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def dismiss_notification(
    *,
    session: Session = Depends(get_session),
    current_user: User = Depends(deps.get_current_active_user),
    id: int
):
    """
    Delete (dismiss) a notification.
    """
    notif = session.get(Notification, id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notif.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    session.delete(notif)
    session.commit()
    return None 

@router.post("/subscribe")
def subscribe_to_push_notifications(
    *,
    session: Session = Depends(get_session),
    current_user: User = Depends(deps.get_current_active_user),
    subscription_info: Any = Body(...)
):
    
    import json

    db_subscription = NotificationSubscription(
        user_id=current_user.id,
        subscription_info_json=json.dumps(subscription_info)
    )
    session.add(db_subscription)
    session.commit()

    return {"status": "subscribed"}
