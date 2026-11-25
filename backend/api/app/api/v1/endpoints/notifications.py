# backend/api/app/api/v1/endpoints/notifications.py

from fastapi import APIRouter, Depends, HTTPException, status, Body, Query, Response
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, update, func
from typing import Any, List, Annotated
from app.db.session import get_async_session
from app.api import deps
from app.models.user import User
from app.models.notification import Notification
from app.schemas.notification import NotificationRead, PushSubscriptionCreate
from sqlalchemy.dialects.postgresql import insert
from app.models.notification_subscription import NotificationSubscription
from datetime import datetime, timezone

router = APIRouter()


def format_timestamp(dt: datetime) -> str:
    # Never guess a timezone for historical naive values.
    if dt.tzinfo is None or dt.utcoffset() is None:
        return dt.isoformat()+" (timezone unknown)"
    now = datetime.now(timezone.utc)
    diff = now - dt

    seconds = diff.total_seconds()

    if seconds < 0:
        return dt.isoformat()
    if seconds < 60:
        return f"{int(seconds)} seconds ago"
    elif seconds < 3600:
        return f"{int(seconds / 60)} min ago"
    elif seconds < 86400:
        return f"{int(seconds / 3600)} hours ago"
    elif seconds < 604800:  
        return f"{int(seconds / 86400)} days ago"
    else:
        return dt.strftime("%Y-%m-%d")


def serialize_notification(notif: Notification) -> NotificationRead:
    return NotificationRead(
        id=notif.id,title=notif.title,body=notif.body,type=notif.type,
        read=notif.read,created_at=notif.created_at,
        cta=notif.meta.get("cta") if isinstance(notif.meta,dict) and isinstance(notif.meta.get("cta"),str) else None,
        timestamp=format_timestamp(notif.created_at),
    )


@router.get("", response_model=List[NotificationRead])
async def get_notifications(
    *,
    session: AsyncSession = Depends(get_async_session),
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
    notifications = (await session.execute(statement)).scalars().all()

    response_notifications = []
    for notif in notifications:
        notif_read = serialize_notification(notif)
        response_notifications.append(notif_read)

    return response_notifications


@router.get('/history')
async def notification_history(
    response: Response,
    page: Annotated[int,Query(ge=1,le=1000000)]=1,
    limit: Annotated[int,Query(ge=1,le=100)]=20,
    session: AsyncSession=Depends(get_async_session),
    current_user: User=Depends(deps.get_current_active_user),
):
    response.headers['Cache-Control']='no-store'
    total=(await session.execute(select(func.count(Notification.id)).where(Notification.user_id==current_user.id))).scalar_one()
    rows=(await session.execute(select(Notification).where(Notification.user_id==current_user.id)
        .order_by(Notification.created_at.desc(),Notification.id.desc()).offset((page-1)*limit).limit(limit))).scalars().all()
    return {'items':[serialize_notification(row) for row in rows],'total':total,'page':page,'limit':limit}


@router.post("/{id}/read", response_model=NotificationRead)
async def mark_notification_as_read(
    *,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(deps.get_current_active_user),
    id: int,
):
    notif = await session.get(Notification, id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notif.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")  

    notif.read = True
    session.add(notif)
    await session.commit()
    await session.refresh(notif)
    notif_read = serialize_notification(notif)
    return notif_read


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_notifications_as_read(
    *,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(deps.get_current_active_user),
):
    statement = (
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.read == False)
        .values(read=True)
    )
    await session.execute(statement)
    await session.commit()
    return None


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_notification(
    *,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(deps.get_current_active_user),
    id: int,
):
    """
    Delete (dismiss) a notification.
    """
    notif = await session.get(Notification, id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notif.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    await session.delete(notif)
    await session.commit()
    return None


@router.post("/subscribe")
async def subscribe_to_push_notifications(
    *,
    session: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(deps.get_current_active_user),
    subscription_info: PushSubscriptionCreate = Body(...),
):
    # Validate also at this reusable boundary; HTTP requests are validated by FastAPI.
    payload = PushSubscriptionCreate.model_validate(subscription_info).model_dump(exclude_none=True)
    statement = insert(NotificationSubscription).values(
        user_id=current_user.id, subscription_info_json=payload
    ).on_conflict_do_update(
        index_elements=[NotificationSubscription.user_id],
        set_={"subscription_info_json": payload},
    )
    await session.execute(statement)
    await session.commit()
    return {"status": "subscribed"}
