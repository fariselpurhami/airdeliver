# apps/api/app/api/v1/endpoints/ai_ordering.py

import asyncio
import json
import logging
import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, EmailStr, Field, ValidationError
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.websockets import WebSocketState

from app import models
from app.api import deps
from app.core.config import settings
from app.services.ai_voice_service import AIVoiceOrchestrator
from app.services.cache_service import IAsyncCacheClient
from app.services.rabbitmq_service import RabbitMQService, get_rabbitmq_service

logger = logging.getLogger("airdeliver.websocket")
router = APIRouter()

# --- 🧱 DOMAIN CONSTANTS & ENUMS ---

WS_TICKET_TTL_SECONDS = 30
RATE_LIMIT_WINDOW_SECONDS = 10
MAX_MESSAGES_PER_WINDOW = 20
VOICE_SESSION_LOCK_TTL = 300  # 5 minutes absolute timeout

class ClientEventType(str, Enum):
    CHAT_MESSAGE = "CHAT_MESSAGE"
    ADD_TO_CART = "ADD_TO_CART"
    REMOVE_FROM_CART = "REMOVE_FROM_CART"
    CLEAR_CART = "CLEAR_CART"
    CONFIRM_ORDER = "CONFIRM_ORDER"
    CANCEL_INTENT = "CANCEL_INTENT"

class EventRoutingMap(str, Enum):
    CHAT_MESSAGE = "airdeliver.ai.chat.in"
    ADD_TO_CART = "airdeliver.ai.cart.add"
    REMOVE_FROM_CART = "airdeliver.ai.cart.remove"
    CLEAR_CART = "airdeliver.ai.cart.clear"
    CONFIRM_ORDER = "airdeliver.ai.order.confirm"
    CANCEL_INTENT = "airdeliver.ai.intent.cancel_order"

# Immutable Static Data
LIFESTYLE_MATRIX = (
    {"id": str(uuid.uuid4()), "title": "Titanium Minimalist", "description": "Pure efficiency.", "theme": "titanium", "icon": "focus_mode", "priority": 1},
    {"id": str(uuid.uuid4()), "title": "Eco-Luxury", "description": "Sustainable logic.", "theme": "eco", "icon": "leaf_sparkle", "priority": 2},
    {"id": str(uuid.uuid4()), "title": "Cyberpunk Aesthetic", "description": "Neon and speed.", "theme": "cyberpunk", "icon": "lightning", "priority": 3},
    {"id": str(uuid.uuid4()), "title": "Silence & Audio", "description": "Acoustic experience.", "theme": "acoustic", "icon": "sound_wave", "priority": 4},
)


# --- 📦 DOMAIN TRANSFER OBJECTS (DTOs) ---

class WSTicketResponse(BaseModel):
    ticket: str = Field(..., description="Short-lived, one-time WebSocket access token.")

class IncomingClientMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: ClientEventType = Field(default=ClientEventType.CHAT_MESSAGE)
    message: Optional[str] = None
    image: Optional[str] = None
    product_id: Optional[int] = None
    quantity: int = Field(default=1, ge=1)
    timestamp: float = Field(default_factory=time.time)

class RoutedMessagePayload(BaseModel):
    user_id: int
    connection_id: str
    email: EmailStr
    country: str
    phone: str
    address: str
    city: str
    message: Optional[str]
    type: str
    image: Optional[str]
    product_id: Optional[int]
    quantity: int
    client_msg_id: str
    timestamp: float


# --- 🎫 SECTION 1: SECURE AUTHENTICATION & RATE LIMITING ---

@router.post("/ticket", response_model=WSTicketResponse)
async def generate_websocket_ticket(
    current_user: models.User = Depends(deps.get_current_active_user),
    cache: IAsyncCacheClient = Depends(deps.get_cache_client),
) -> WSTicketResponse:
    """
    Issues a cryptographically secure, ephemeral ticket to avoid passing Bearer tokens via URI.
    """
    ticket = str(uuid.uuid4())
    await cache.set(f"ws_ticket:{ticket}", str(current_user.id), ttl=WS_TICKET_TTL_SECONDS)
    return WSTicketResponse(ticket=ticket)

async def _check_rate_limit(user_id: int, cache: IAsyncCacheClient) -> bool:
    """
    Evaluates connection throughput via Redis sliding window counter.
    Employs a fail-closed protocol under internal exceptions to protect message queues,
    unless configured explicitly for fail-open.
    """
    key = f"ws_ratelimit:{user_id}"
    try:
        current_count = await cache.incr(key)
        if current_count == 1:
            await cache.expire(key, RATE_LIMIT_WINDOW_SECONDS)

        if current_count > MAX_MESSAGES_PER_WINDOW:
            logger.warning("Rate limit exceeded", extra={"user_id": user_id, "count": current_count})
            return False
        return True
    except Exception as e:
        logger.error("Rate limiter failure", extra={"user_id": user_id, "error": str(e)})
        return False  # Strict fail-closed boundary


# --- 🔌 SECTION 2: UNIVERSAL CHAT SOCKET ---

@router.websocket("/chat")
async def handle_chat_websocket(
    websocket: WebSocket,
    ticket: str = Query(...),
    session: AsyncSession = Depends(deps.get_async_session),
    rabbitmq: RabbitMQService = Depends(get_rabbitmq_service),
    cache: IAsyncCacheClient = Depends(deps.get_cache_client),
) -> None:
    """
    THE UNIVERSAL SOCKET HANDLER.
    Maintains persistent connections, applies input sanitization, and bridges client
    intent to the event-driven RabbitMQ backend.
    """
    try:
        current_user = await deps.get_current_active_user_ws_ticket(
            websocket=websocket, ticket=ticket, session=session, cache=cache
        )
    except Exception as e:
        logger.error("WebSocket auth failure", extra={"error": str(e)})
        if websocket.client_state != WebSocketState.DISCONNECTED:
             await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    connection_id = str(uuid.uuid4())
    connection_manager = deps.get_websocket_manager()
    await connection_manager.connect(current_user.id, websocket)

    logger.info("Chat socket connected", extra={"user_id": current_user.id, "connection_id": connection_id})

    # Destroy the ticket to prevent replay attacks
    await cache.delete(f"ws_ticket:{ticket}")

    # Inject Welcome Payload
    try:
        welcome_payload = {
            "user_id": current_user.id,
            "connection_id": connection_id,
            "email": current_user.email,
            "type": "WELCOME_INTENT",
            "data": {
                "mode": "selection_required",
                "header_text": "Select your lifestyle archetype:",
                "matrix_cards": LIFESTYLE_MATRIX
            },
            "message": "User Initiated Matrix Selection",
            "client_msg_id": str(uuid.uuid4()),
            "timestamp": time.time(),
        }
        await rabbitmq.publish(
            body=welcome_payload,
            routing_key=EventRoutingMap.CHAT_MESSAGE.value,
            max_retries=2
        )
    except Exception as e:
        logger.error("Failed to inject matrix context", extra={"user_id": current_user.id, "error": str(e)})

    # Initialize PubSub Listener
    redis_channel = f"airdeliver:response:{current_user.id}"
    pubsub = None
    listener_task = None

    async def _listen_for_ai_responses() -> None:
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    await websocket.send_text(message["data"])
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Redis listener exception", extra={"user_id": current_user.id, "error": str(e)})

    try:
        if hasattr(cache, 'subscribe'):
            pubsub = await cache.subscribe(redis_channel)
            listener_task = asyncio.create_task(_listen_for_ai_responses())
        else:
            logger.error("Cache client lacks PubSub capability. Async responses disabled.")

        # Message Event Loop
        while True:
            raw_data = await websocket.receive_text()

            if not await _check_rate_limit(current_user.id, cache):
                await websocket.send_json({
                    "type": "ERROR",
                    "code": "RATE_LIMIT_EXCEEDED",
                    "content": "Message rate exceeded limits. Throttling active."
                })
                continue

            try:
                msg_dict = json.loads(raw_data)
                validated_msg = IncomingClientMessage(**msg_dict)
            except (json.JSONDecodeError, ValidationError) as e:
                logger.warning("Malformed WebSocket payload", extra={"user_id": current_user.id, "error": str(e)})
                await websocket.send_json({"type": "ERROR", "content": "Invalid message structure."})
                continue

            # Construct Immutable Domain Payload
            payload = RoutedMessagePayload(
                user_id=current_user.id,
                connection_id=connection_id,
                email=current_user.email,
                country=getattr(current_user, 'country', 'US'),
                phone=current_user.phone_number or "",
                address=current_user.address or "",
                city=current_user.city or "",
                message=validated_msg.message,
                type=validated_msg.type.value,
                image=validated_msg.image,
                product_id=validated_msg.product_id,
                quantity=validated_msg.quantity,
                client_msg_id=validated_msg.id,
                timestamp=validated_msg.timestamp,
            )

            # Retrieve routing key via O(1) mapping
            target_queue = EventRoutingMap[validated_msg.type.name].value

            try:
                await rabbitmq.publish(
                    body=payload.model_dump(mode="json"),
                    routing_key=target_queue,
                    max_retries=2
                )
                await websocket.send_json({
                    "type": "SERVER_ACK",
                    "reply_to": validated_msg.id,
                    "status": "queued",
                    "routing_key": target_queue
                })
            except Exception as e:
                logger.error("RabbitMQ publish failure", extra={"user_id": current_user.id, "error": str(e)})
                await websocket.send_json({
                    "type": "ERROR",
                    "code": "DELIVERY_FAILED",
                    "content": "Service temporarily unavailable."
                })

    except WebSocketDisconnect:
        logger.info("Chat socket closed by client", extra={"user_id": current_user.id})
    except Exception as e:
        logger.error("Chat socket critical failure", exc_info=True, extra={"user_id": current_user.id, "error": str(e)})
        if websocket.client_state != WebSocketState.DISCONNECTED:
            try:
                await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            except: pass
    finally:
        # Deterministic Resource Teardown
        if listener_task:
            listener_task.cancel()
            try:
                await listener_task
            except asyncio.CancelledError:
                pass

        if pubsub:
            await pubsub.close()

        await connection_manager.disconnect(current_user.id, websocket)


# --- 🎤 SECTION 3: TITANIUM VOICE SOCKET ---

@router.websocket("/voice-stream")
async def handle_voice_stream(
    websocket: WebSocket,
    ticket: str = Query(...),
    session: AsyncSession = Depends(deps.get_async_session),
    commerce_engine: Any = Depends(deps.get_ai_commerce_engine),
    llm_service: Any = Depends(deps.get_llm_service),
    cache: IAsyncCacheClient = Depends(deps.get_cache_client),
) -> None:
    """
    REAL-TIME VOICE CHANNEL.
    Enforces strict concurrency invariants utilizing atomic distributed locks to prevent
    resource exhaustion across multi-tab configurations.
    """
    user_id_str = await cache.get(f"ws_ticket:{ticket}")
    if not user_id_str:
        logger.warning("Voice socket auth rejection", extra={"ticket": ticket})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = int(user_id_str)
    await cache.delete(f"ws_ticket:{ticket}") # Immediate Replay Prevention

    lock_key = f"voice_session_lock:{user_id}"

    # Attempt Atomic Lock (NX -> Set if Not eXists)
    # Assumes `cache.set` supports standard Redis NX behavior. Fallback is implicit but discouraged.
    lock_acquired = await cache.set(lock_key, "active", ttl=VOICE_SESSION_LOCK_TTL, nx=True)

    if not lock_acquired:
        logger.warning("Voice concurrency violation", extra={"user_id": user_id})
        await websocket.accept()
        await websocket.send_json({"type": "error", "content": "Voice mode is currently active in another session."})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        await websocket.accept()
        logger.info("Voice socket established", extra={"user_id": user_id})

        orchestrator = AIVoiceOrchestrator(llm_service, commerce_engine)
        await orchestrator.process_voice_session(websocket, user_id)

    except WebSocketDisconnect:
        logger.info("Voice socket closed by client", extra={"user_id": user_id})
    except Exception as e:
        logger.error("Voice socket execution failure", exc_info=True, extra={"user_id": user_id, "error": str(e)})
        if websocket.client_state != WebSocketState.DISCONNECTED:
            try:
                await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            except: pass
    finally:
        # Guaranteed strict lock release irrespective of task result
        await cache.delete(lock_key)
        logger.info("Voice session lock released", extra={"user_id": user_id})
