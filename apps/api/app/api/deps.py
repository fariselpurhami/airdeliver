# apps/api/app/api/deps.py

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from functools import lru_cache
from typing import Optional

from fastapi import Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app import models, schemas
from app.core import security
from app.core.config import CoreSettings, get_core_settings
from app.db.session import get_async_session
from app.models.user import UserRole
from app.services.ai_commerce_engine import get_ai_commerce_engine
from app.services.cache_service import IAsyncCacheClient, get_cache_client
from app.services.free_llm_service import FreeLLMService
from app.services.rabbitmq_service import RabbitMQService

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{get_core_settings().API_V1_STR}/auth/token",
)

optional_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{get_core_settings().API_V1_STR}/auth/token",
    auto_error=False,
)


def _get_secret_key_value(settings: CoreSettings) -> str:
    secret = settings.SECRET_KEY
    return secret.get_secret_value() if hasattr(secret, "get_secret_value") else str(secret)


def _forbidden_credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Could not validate credentials",
    )


async def _load_user_by_subject(session: AsyncSession, subject: str) -> models.User | None:

    result = await session.execute(select(models.User).where(models.User.email == subject))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _decode_token_subject(token: str, settings: CoreSettings) -> str:
    try:
        payload = jwt.decode(
            token,
            _get_secret_key_value(settings),
            algorithms=[security.ALGORITHM],
        )
        token_data = schemas.TokenPayload(**payload)
    except (JWTError, ValidationError) as exc:
        raise _forbidden_credentials_exception() from exc

    if not token_data.sub:
        raise _forbidden_credentials_exception()

    return token_data.sub


async def _get_user_from_token(
    token: str,
    session: AsyncSession,
    settings: CoreSettings,
) -> models.User:
    subject = _decode_token_subject(token, settings)
    user = await _load_user_by_subject(session, subject)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


def _ensure_active_user(user: models.User) -> models.User:
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return user


def _ensure_admin_user(user: models.User) -> models.User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return user


async def get_current_user(
    settings: CoreSettings = Depends(get_core_settings),
    session: AsyncSession = Depends(get_async_session),
    token: str = Depends(oauth2_scheme),
) -> models.User:
    return await _get_user_from_token(token=token, session=session, settings=settings)


async def get_current_active_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    return _ensure_active_user(current_user)


async def get_current_admin_user(
    current_user: models.User = Depends(get_current_active_user),
) -> models.User:
    return _ensure_admin_user(current_user)


async def get_optional_current_user(
    settings: CoreSettings = Depends(get_core_settings),
    session: AsyncSession = Depends(get_async_session),
    token: Optional[str] = Depends(optional_oauth2_scheme),
) -> models.User | None:
    if token is None:
        return None

    try:
        user = await _get_user_from_token(token=token, session=session, settings=settings)
    except HTTPException:
        return None

    return user if user.is_active else None


class WebSocketManager:
    def __init__(self) -> None:
        self._active_connections: dict[int, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        async with self._lock:
            connections = self._active_connections.setdefault(user_id, set())
            connections.add(websocket)
            logger.info(
                "WebSocket connected.",
                extra={
                    "user_id": user_id,
                    "active_connections": len(connections),
                },
            )

    async def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        async with self._lock:
            connections = self._active_connections.get(user_id)
            if not connections:
                return

            connections.discard(websocket)
            remaining = len(connections)

            if not connections:
                self._active_connections.pop(user_id, None)

            logger.info(
                "WebSocket disconnected.",
                extra={
                    "user_id": user_id,
                    "active_connections": remaining,
                },
            )

    async def send_to_user(self, user_id: int, message: str) -> None:
        async with self._lock:
            connections = tuple(self._active_connections.get(user_id, set()))

        if not connections:
            logger.debug("No active WebSocket connections for user.", extra={"user_id": user_id})
            return

        stale_connections: list[WebSocket] = []

        for websocket in connections:
            try:
                await websocket.send_text(message)
            except (WebSocketDisconnect, RuntimeError):
                stale_connections.append(websocket)
            except Exception:
                stale_connections.append(websocket)
                logger.exception(
                    "Unexpected WebSocket send failure.",
                    extra={"user_id": user_id},
                )

        if stale_connections:
            async with self._lock:
                current_connections = self._active_connections.get(user_id)
                if current_connections is not None:
                    for websocket in stale_connections:
                        current_connections.discard(websocket)
                    if not current_connections:
                        self._active_connections.pop(user_id, None)

    async def disconnect_all(self, user_id: int) -> None:
        async with self._lock:
            self._active_connections.pop(user_id, None)


_websocket_manager = WebSocketManager()


def get_websocket_manager() -> WebSocketManager:
    return _websocket_manager


async def get_current_active_user_ws(
    websocket: WebSocket,
    token: str | None = Query(default=None),
    settings: CoreSettings = Depends(get_core_settings),
    session: AsyncSession = Depends(get_async_session),
) -> models.User:
    if token is None or not token.strip():
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Missing auth token",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing auth token",
        )

    try:
        user = await _get_user_from_token(token=token, session=session, settings=settings)
        return _ensure_active_user(user)
    except HTTPException as exc:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason=str(exc.detail),
        )
        raise


async def get_current_active_user_ws_ticket(
    websocket: WebSocket,
    ticket: str | None = Query(default=None),
    session: AsyncSession = Depends(get_async_session),
    cache: IAsyncCacheClient = Depends(get_cache_client),
) -> models.User:
    if ticket is None or not ticket.strip():
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Missing ticket",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing auth ticket",
        )

    ticket_key = f"ws_ticket:{ticket}"
    user_id_raw = await cache.get(ticket_key)

    if not user_id_raw:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid or expired ticket",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired ticket",
        )

    await cache.delete(ticket_key)

    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError) as exc:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid ticket payload",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid ticket payload",
        ) from exc

    user = await session.get(models.User, user_id)

    if user is None:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="User not found",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return _ensure_active_user(user)


@lru_cache(maxsize=1)
def get_llm_service() -> FreeLLMService:
    return FreeLLMService()


def get_rabbitmq_service_dependency(
    settings: CoreSettings = Depends(get_core_settings),
) -> RabbitMQService:
    return RabbitMQService(settings)


def get_ai_engine():
    return get_ai_commerce_engine()

get_async_session = get_async_session

import fastapi

def get_rabbitmq_service(request: fastapi.Request):
    return request.app.state.rabbitmq

