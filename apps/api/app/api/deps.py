# apps/api/app/api/deps.py

from fastapi import Depends, HTTPException, status, WebSocket, Query, WebSocketDisconnect
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Dict, Optional, Set
import logging
import asyncio

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
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, user_id: int, websocket: WebSocket):
        async with self._lock:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = set()
            self.active_connections[user_id].add(websocket)
            logger.info(f"User {user_id} connected via WebSocket. Total sessions: {len(self.active_connections[user_id])}")

    async def disconnect(self, user_id: int, websocket: WebSocket):
        async with self._lock:
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
                logger.info(f"User {user_id} disconnected. Active sessions left: {len(self.active_connections.get(user_id, []))}")

    async def send_to_user(self, user_id: int, message: str):

        connections = self.active_connections.get(user_id, set()).copy()
        
        if not connections:
            logger.debug(f"No active connections for user {user_id} to send message.")
            return

        for websocket in connections:
            try:
                if websocket.client_state.value == 1: 
                    await websocket.send_text(message)
            except (WebSocketDisconnect, RuntimeError) as e:
                logger.warning(f"Failed to send to user {user_id} (Socket closed): {e}")
            except Exception as e:
                logger.error(f"Unexpected error sending to user {user_id}: {e}")

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
        raise HTTPException(status_code=403, detail="Missing auth token")

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = schemas.TokenPayload(**payload)
    except (JWTError, ValidationError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid credentials")
        raise HTTPException(status_code=403, detail="Invalid credentials")

    user = await crud_user.user.get_by_email(db=session, email=token_data.sub)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User not found")
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.is_active:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Inactive user")
        raise HTTPException(status_code=400, detail="Inactive user")

    return user
