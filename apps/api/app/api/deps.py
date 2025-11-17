# apps/api/app/api/deps.py

from fastapi import Depends, HTTPException, status, WebSocket, Query, WebSocketException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Dict, List, Optional
import logging

from app.db.session import get_session
from app.core.config import get_core_settings, CoreSettings
from app.core import security
from app.crud import crud_user
from app import models, schemas
from app.models.user import UserRole

logger = logging.getLogger(__name__)

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{get_core_settings().API_V1_STR}/auth/token"
)

optional_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{get_core_settings().API_V1_STR}/auth/token",
    auto_error=False
)

async def get_current_user(
    settings: CoreSettings = Depends(get_core_settings),
    session: AsyncSession = Depends(get_session),
    token: str = Depends(reusable_oauth2),
) -> models.User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = schemas.TokenPayload(**payload)
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    user = await crud_user.user.get_by_email(db=session, email=token_data.sub)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


async def get_current_active_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

async def get_current_admin_user(
    current_user: models.User = Depends(get_current_active_user),
) -> models.User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user

async def get_optional_current_user(
    settings: CoreSettings = Depends(get_core_settings),
    session: AsyncSession = Depends(get_session), 
    token: Optional[str] = Depends(optional_oauth2)
) -> Optional[models.User]:
    if not token:
        return None
    
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = schemas.TokenPayload(**payload)
    except (JWTError, ValidationError):
        return None
    
    user = await crud_user.user.get_by_email(session, email=token_data.sub)
    
    if not user or not user.is_active:
        return None
            
    return user


class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        if user_id in self.active_connections:
            await self.disconnect(user_id)
        self.active_connections[user_id] = websocket

    async def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            websocket = self.active_connections.pop(user_id)
            try:
                await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
            except RuntimeError:
                pass 
            except Exception as e:
                logger.warning(f"Error closing websocket for user {user_id}: {e}")

    async def send_to_user(self, user_id: int, message: str):
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_text(message)
            except Exception as e:
                logger.error(f"Failed to send message to user {user_id}: {e}. Disconnecting.")
                await self.disconnect(user_id)

_websocket_manager_instance: Optional[WebSocketManager] = None

def get_websocket_manager() -> WebSocketManager:
    global _websocket_manager_instance
    if _websocket_manager_instance is None:
        _websocket_manager_instance = WebSocketManager()
    return _websocket_manager_instance

async def get_current_active_user_ws(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    settings: CoreSettings = Depends(get_core_settings),
    session: AsyncSession = Depends(get_session),
) -> models.User:
    if token is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing auth token")
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Missing auth token")

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = schemas.TokenPayload(**payload)
    except (JWTError, ValidationError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid credentials")
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid credentials")

    user = await crud_user.user.get_by_email(db=session, email=token_data.sub)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User not found")
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="User not found")
    
    if not user.is_active:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Inactive user")
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Inactive user")

    return user
