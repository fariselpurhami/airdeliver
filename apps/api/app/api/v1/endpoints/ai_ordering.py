# apps/api/app/api/v1/endpoints/ai_ordering.py

import uuid
import json
import time
import logging
import asyncio
import random
from typing import Optional

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.websockets import WebSocketState
from app.services.ai_voice_service import AIVoiceOrchestrator

# Internal Imports
from app import models
from app.api import deps
from app.services.rabbitmq_service import RabbitMQService, get_rabbitmq_service
from app.services.cache_service import IAsyncCacheClient, get_cache_from_request
from app.core.config import settings

logger = logging.getLogger("airdeliver.websocket")
router = APIRouter()

# 🛡️ CONFIGURATION CONSTANTS
RATE_LIMIT_WINDOW = 10  # Seconds
MAX_MESSAGES_PER_WINDOW = 20 # Slight bump for heavy users

logger.info("🚀 AI ORDERING GATEWAY LOADED: v5.0 (Titanium Shield Enabled)")

# --- 🎫 SECTION 1: SECURE AUTHENTICATION ---

@router.post("/ticket")
async def generate_websocket_ticket(
    current_user: models.User = Depends(deps.get_current_active_user),
    cache: IAsyncCacheClient = Depends(get_cache_from_request),
):
    """
    Generates a secure, short-lived, one-time-use ticket for WebSocket auth.
    Prevents passing sensitive Bearer tokens in URL query params.
    """
    ticket = str(uuid.uuid4())
    # Ticket valid for only 30 seconds (Strict Window)
    await cache.set(f"ws_ticket:{ticket}", str(current_user.id), ttl=30)
    return {"ticket": ticket}


async def check_rate_limit(user_id: int, cache: IAsyncCacheClient) -> bool:
    """
    🛡️ DIAMOND SECURITY: Rate Limiting Implementation using Redis.
    Uses sliding window or simple fixed window counter.
    Returns True if allowed, False if blocked.
    """
    key = f"ws_ratelimit:{user_id}"
    try:
        current_count = await cache.incr(key)
        if current_count == 1:
            await cache.expire(key, RATE_LIMIT_WINDOW)

        if current_count > MAX_MESSAGES_PER_WINDOW:
            logger.warning(f"🚫 Rate Limit Hit: User {user_id}")
            return False
        return True
    except Exception as e:
        logger.warning(f"Rate limit check failed (Fail-Open Policy): {e}")
        return True

# --- 🔌 SECTION 2: THE WEBSOCKET HANDLER ---

@router.websocket("/chat")
async def handle_chat_websocket(
    websocket: WebSocket,
    ticket: str = Query(None),
    session: AsyncSession = Depends(deps.get_async_session),
    rabbitmq: RabbitMQService = Depends(get_rabbitmq_service),
    cache: IAsyncCacheClient = Depends(get_cache_from_request),
):
    """
    💎 THE UNIVERSAL SOCKET HANDLER.
    Orchestrates the Real-Time connection between User <-> AI.
    Features: Auth, Rate Limiting, Pub/Sub Listening, and Message Routing.
    """

    # 1. AUTHENTICATION PHASE
    current_user = None
    try:
        current_user = await deps.get_current_active_user_ws_ticket(
            websocket=websocket,
            ticket=ticket,
            session=session,
            cache=cache
        )
    except Exception as e:
        logger.error(f"❌ WebSocket Auth Failed: {e}")
        if websocket.client_state != WebSocketState.DISCONNECTED:
             await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 2. CONNECTION ESTABLISHMENT
    await websocket.accept()

    # Unique Connection ID (Traceability)
    connection_id = str(uuid.uuid4())
    connection_manager = deps.get_websocket_manager()

    # Register connection
    await connection_manager.connect(current_user.id, websocket)
    logger.info(f"✅ User {current_user.id} connected via Socket {connection_id[:8]}...")


    lifestyle_matrix = [
        {
            "id": str(uuid.uuid4()),
            "title": "Titanium Minimalist",
            "description": "For the focus-obsessed. Pure efficiency.",
            "theme": "titanium",
            "icon": "focus_mode", 
            "priority": 1
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Eco-Luxury",
            "description": "Sustainable high-end tech logic.",
            "theme": "eco",
            "icon": "leaf_sparkle",
            "priority": 2
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Cyberpunk Aesthetic",
            "description": "Neon, performance, and speed.",
            "theme": "cyberpunk", 
            "icon": "lightning",
            "priority": 3
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Silence & Audio",
            "description": "The ultimate acoustic experience.",
            "theme": "acoustic",
            "icon": "sound_wave",
            "priority": 4
        }
    ]

    try:
        # 2. بناء الـ Payload بهيكلية بيانات موحدة (Strict Schema)
        welcome_payload = {
            "user_id": current_user.id,
            "connection_id": connection_id,
            "email": current_user.email,
            "type": "WELCOME_INTENT",
            "data": {
                "mode": "selection_required",
                "header_text": "Select your lifestyle archetype:",
                "matrix_cards": lifestyle_matrix
            },
            "message": "User Initiated Matrix Selection",
            "client_msg_id": str(uuid.uuid4()),
            "timestamp": time.time(),
        }

        # 3. الحقن المباشر في الـ Queue (Direct Injection)
        await rabbitmq.publish(
            body=welcome_payload,
            routing_key="airdeliver.ai.chat.in",
            max_retries=2
        )
        logger.info(f"✅ Lifestyle Matrix Injected for User {current_user.id} (Local Context)")

    except Exception as e:
        logger.warning(f"⚠️ Failed to Inject Matrix: {e}")

    # Redis Channel for AI Responses
    redis_channel_name = f"airdeliver:response:{current_user.id}"
    pubsub = None
    listener_task = None

    # --- 🎧 BACKGROUND LISTENER SETUP ---
    try:
        if hasattr(cache, 'subscribe'):
            pubsub = await cache.subscribe(redis_channel_name)

            async def listen_for_ai_responses():
                """Background task to push AI responses to the websocket."""
                try:
                    async for message in pubsub.listen():
                        if message["type"] == "message":
                            raw_data = message["data"]
                            # Push directly to frontend
                            await websocket.send_text(raw_data)
                except asyncio.CancelledError:
                    pass # Task cancelled gracefully
                except Exception as e:
                    logger.error(f"Redis Listener Error for User {current_user.id}: {e}")

            # Start Listener
            listener_task = asyncio.create_task(listen_for_ai_responses())
            logger.info(f"🎧 Redis Listener Active for Channel: {redis_channel_name}")
        else:
            logger.warning("⚠️ Cache client does not support subscription. Real-time responses may fail.")

    except Exception as e:
        logger.error(f"Failed to setup Redis Listener: {e}")

    # --- 📨 3. MESSAGE RECEIVE LOOP ---
    try:
        while True:
            data = await websocket.receive_text()

            # A. Rate Limiting Check
            is_allowed = await check_rate_limit(current_user.id, cache)
            if not is_allowed:
                await websocket.send_json({
                    "type": "ERROR",
                    "code": "RATE_LIMIT_EXCEEDED",
                    "content": "You are sending messages too fast. Please wait a moment."
                })
                continue

            # B. Parse Message
            try:
                message_data = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "ERROR", "content": "Invalid JSON format."})
                continue

            # C. Construct Robust Payload (The Universal Packet)
            client_msg_id = message_data.get("id") or str(uuid.uuid4())

            user_phone = current_user.phone_number or ""
            user_address = current_user.address or ""
            user_city = current_user.city or ""

            message_payload = {
                "user_id": current_user.id,
                "connection_id": connection_id,
                "email": current_user.email,
                "country": getattr(current_user, 'country', 'US'),
                "phone": user_phone,
                "address": user_address,
                "city": user_city,
                "message": message_data.get("message"),
                "type": message_data.get("type", "CHAT_MESSAGE"),
                "image": message_data.get("image"),
                "product_id": message_data.get("product_id"),
                "quantity": message_data.get("quantity", 1),
                "client_msg_id": client_msg_id,
                "timestamp": message_data.get("timestamp") or time.time(),
            }

            # D. Smart Routing Logic
            routing_key = "airdeliver.ai.chat.in"
            msg_type = message_payload["type"]

            if msg_type == "ADD_TO_CART":
                 routing_key = "airdeliver.ai.cart.add"
            elif msg_type == "REMOVE_FROM_CART":
                 routing_key = "airdeliver.ai.cart.remove"
            elif msg_type == "CLEAR_CART":
                 routing_key = "airdeliver.ai.cart.clear"
            elif msg_type == "CONFIRM_ORDER":
                 routing_key = "airdeliver.ai.order.confirm"
            elif msg_type == "CANCEL_INTENT":
                 routing_key = "airdeliver.ai.intent.cancel_order"

            # E. Publish to RabbitMQ (Black Hole Prevention)
            try:
                await rabbitmq.publish(
                    body=message_payload,
                    routing_key=routing_key,
                    max_retries=2
                )

                # F. Instant Server ACK (UI Feedback)
                await websocket.send_json({
                    "type": "SERVER_ACK",
                    "reply_to": client_msg_id,
                    "status": "queued",
                    "routing_key": routing_key
                })

            except Exception as e:
                logger.error(f"🔥 RabbitMQ Publish Failed User {current_user.id}: {e}")
                await websocket.send_json({
                    "type": "ERROR",
                    "code": "DELIVERY_FAILED",
                    "content": "Service temporarily unavailable. Please try again."
                })

    # --- 🧹 CLEANUP ---
    except WebSocketDisconnect:
        logger.info(f"User {current_user.id} disconnected (Socket {connection_id[:8]}).")

        if listener_task: listener_task.cancel()
        if pubsub: await pubsub.close()

        await connection_manager.disconnect(current_user.id, websocket)

    except Exception as e:
        logger.error(f"🔥 Critical WebSocket Crash User {current_user.id}: {e}", exc_info=True)

        if listener_task: listener_task.cancel()
        if pubsub: await pubsub.close()

        try:
            await connection_manager.disconnect(current_user.id, websocket)
            if websocket.client_state != WebSocketState.DISCONNECTED:
                await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except: pass


@router.websocket("/voice-stream")
async def handle_voice_stream(
    websocket: WebSocket,
    ticket: str = Query(None),
    session: AsyncSession = Depends(deps.get_async_session),
    commerce_engine = Depends(deps.get_ai_commerce_engine),
    llm_service = Depends(deps.get_llm_service),
    rabbitmq: RabbitMQService = Depends(get_rabbitmq_service),
    cache: IAsyncCacheClient = Depends(get_cache_from_request),
):
    """
    🎤 REAL-TIME VOICE CHANNEL (TITANIUM GUARDED).
    Dedicated WebSocket for Audio/Video streaming with Concurrency Locking.
    Dependency Injection upgraded to support the Active Middleware Voice Orchestrator.
    """
    # 1. 🎫 FAST AUTH & TICKET VALIDATION
    user_id_str = await cache.get(f"ws_ticket:{ticket}")
    if not user_id_str:
        logger.warning(f"⛔ Voice Access Denied: Invalid Ticket {ticket}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = int(user_id_str)

    # 2. 🔒 CONCURRENCY GUARD (The Titanium Shield)
    lock_key = f"voice_session_lock:{user_id}"
    is_locked = await cache.get(lock_key)

    if is_locked:
        logger.warning(f"🚫 Voice Session Rejected: User {user_id} already speaking in another tab.")
        await websocket.accept()
        await websocket.send_json({"type": "error", "content": "Voice mode is active in another tab."})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 3. 🏁 INITIALIZE ORCHESTRATOR
    # DI updated: orchestrator is now context-aware and event-driven.
    orchestrator = AIVoiceOrchestrator(
        commerce_engine=commerce_engine,
        llm_service=llm_service,
        rabbitmq=rabbitmq,
        cache=cache,
        db_session=session
    )

    # 4. 🛡️ SAFE EXECUTION BLOCK (Try/Finally)
    try:
        # Set Lock (Expire in 5 mins to prevent deadlocks if server crashes)
        await cache.set(lock_key, "active", ttl=300)

        # Handover control to the Brain
        await orchestrator.process_voice_session(websocket, str(user_id))

    except Exception as e:
        logger.error(f"🔥 Critical Voice Crash User {user_id}: {e}", exc_info=True)
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except: pass

    finally:
        # 5. 🧹 CLEANUP PROTOCOL
        await cache.delete(lock_key)
        await cache.delete(f"ws_ticket:{ticket}")
        logger.info(f"🔌 Voice Session Cleaned User {user_id}")
