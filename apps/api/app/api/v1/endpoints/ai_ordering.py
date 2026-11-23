# apps/api/app/api/v1/endpoints/ai_ordering.py

import uuid
import json
import logging
import asyncio
import time
from decimal import Decimal
from typing import Optional, Literal

from typing import AsyncGenerator, List
import httpx
from fastapi import APIRouter, Body, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query, status, Request, Response, Header
from pydantic import BaseModel, Field
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.websockets import WebSocketState
from app.services.ai_voice_service import AIVoiceOrchestrator

# Internal Imports
from app import models
from app.api import deps
from app.core.limiter import limiter
from app.services.rabbitmq_service import RabbitMQService, get_rabbitmq_service
from app.services.cache_service import IAsyncCacheClient, get_cache_from_request
from app.services.ai_behavior_engine import BehaviorEngine
from app.services.ai_cart_service import AICartService
from app.services.ai_checkout_service import AICheckoutService
from app.schemas.shipping import ShippingAddress
from app.services.ai_nlu_service import AINLUService
from pydantic import BaseModel as _PayPalBaseModel
from app.services.payment_completion_service import PaymentCompletionService
from app.services.payment_orchestrator import (
    IPaymentGateway,
    MpesaGateway,
    PaymentOrchestrator,
    PaymentStatus,
    PayPalGateway,
    StripeGateway,
)
from app.core.config import (
    settings,
    get_mpesa_settings,
    get_paypal_settings,
    get_stripe_settings,
)

class PayPalCaptureRequest(_PayPalBaseModel):
    order_id: str = Field(pattern=r"^[1-9][0-9]{0,18}$")
    paypal_order_id: str = Field(pattern=r"^[A-Z0-9]{1,36}$")


logger = logging.getLogger("airdeliver.websocket")
router = APIRouter()

# 🛡️ CONFIGURATION CONSTANTS
RATE_LIMIT_WINDOW = 10  # Seconds
MAX_MESSAGES_PER_WINDOW = 20 # Slight bump for heavy users

logger.info("🚀 AI ORDERING GATEWAY LOADED: v5.0 (Titanium Shield Enabled)")

# --- 🎫 SECTION 1: SECURE AUTHENTICATION ---

@router.post("/ticket")
@limiter.limit("20/minute")
async def generate_websocket_ticket(
    request: Request,
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

# --- 🛒 SECTION 1B: HTTP CART & CHECKOUT COMMANDS ---
# Single consumer path for cart/checkout commands. These endpoints call the
# same AICartService / AICheckoutService handlers the RabbitMQ workers were
# meant to run; no worker exists in this stack, so the socket queues were a
# black hole. UI updates still reach the client over the /chat websocket via
# the Redis `airdeliver:response:{user_id}` relay, unchanged.


class AddToCartRequest(BaseModel):
    product_id: int = Field(ge=1, le=9223372036854775807, strict=True)
    quantity: int = Field(default=1, ge=1, le=99, strict=True)


class RemoveFromCartRequest(BaseModel):
    product_id: int = Field(ge=1, le=9223372036854775807, strict=True)


class ConfirmOrderRequest(BaseModel):
    shipping_address: ShippingAddress
    payment_provider: Optional[Literal["stripe", "paypal"]] = None


class CancelOrderRequest(BaseModel):
    order_id: Optional[int] = Field(default=None,gt=0,le=2147483647,strict=True)


async def get_ai_cart_service(
    db: AsyncSession = Depends(deps.get_async_session),
    cache: IAsyncCacheClient = Depends(get_cache_from_request),
    rabbitmq: RabbitMQService = Depends(get_rabbitmq_service),
) -> AICartService:
    # commerce_engine / llm_service stay None: they only power optional
    # vector-bundling and recovery copy, and depending on OpenSearch/Milvus
    # here would take the whole cart down when that infra is offline.
    return AICartService(db=db, cache=cache, rabbitmq=rabbitmq)


async def get_ai_checkout_service(
    db: AsyncSession = Depends(deps.get_async_session),
    cache: IAsyncCacheClient = Depends(get_cache_from_request),
    rabbitmq: RabbitMQService = Depends(get_rabbitmq_service),
) -> AsyncGenerator[AICheckoutService, None]:
    gateways: List[IPaymentGateway] = []
    http_clients: List[httpx.AsyncClient] = []

    try:
        gateways.append(StripeGateway(get_stripe_settings()))
    except Exception as exc:
        logger.warning("Stripe gateway unavailable for checkout", extra={"error_type": type(exc).__name__})

    for label, get_settings, gateway_cls in (
        ("PayPal", get_paypal_settings, PayPalGateway),
        ("Mpesa", get_mpesa_settings, MpesaGateway),
    ):
        try:
            gateway_settings = get_settings()
        except Exception as exc:
            logger.warning("Payment gateway unavailable for checkout", extra={"provider": label, "error_type": type(exc).__name__})
            continue
        try:
            client = httpx.AsyncClient(timeout=httpx.Timeout(5.0))
            http_clients.append(client)
            gateway = gateway_cls(gateway_settings, cache, client)
            if isinstance(gateway, MpesaGateway) and not gateway.available_for_checkout:
                logger.warning("M-Pesa live adapter unavailable for checkout")
                continue
            gateways.append(gateway)
        except Exception as exc:
            logger.warning("Payment gateway initialization failed", extra={"provider": label, "error_type": type(exc).__name__})

    if not gateways:
        for client in http_clients:
            await client.aclose()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No payment gateway is configured.",
        )

    try:
        yield AICheckoutService(
            db=db,
            cache=cache,
            rabbitmq=rabbitmq,
            orchestrator=PaymentOrchestrator(gateways),
        )
    finally:
        for client in http_clients:
            await client.aclose()


@router.get("/cart")
async def read_current_cart(
    response: Response,
    current_user: models.User = Depends(deps.get_current_active_user),
    cart_service: AICartService = Depends(get_ai_cart_service),
):
    response.headers["Cache-Control"] = "no-store"
    cart = await cart_service._get_cart_from_redis(current_user.id)
    return cart.model_dump(mode="json")


@router.post("/cart/sync", status_code=status.HTTP_202_ACCEPTED)
async def sync_cart(
    current_user: models.User = Depends(deps.get_current_active_user),
    cart_service: AICartService = Depends(get_ai_cart_service),
):
    """Push the authoritative cart state to the client (connection hydration)."""
    await cart_service.handle_sync_cart({"user_id": current_user.id})
    return {"status": "accepted"}


@router.post("/cart/add", status_code=status.HTTP_202_ACCEPTED)
async def add_to_cart(
    payload: AddToCartRequest,
    request: Request,
    mutation_id: Optional[uuid.UUID] = Header(None, alias="Idempotency-Key"),
    current_user: models.User = Depends(deps.get_current_active_user),
    cart_service: AICartService = Depends(get_ai_cart_service),
):
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    started = time.monotonic()
    logger.info("cart_add_request_started", extra={"correlation_id": correlation_id})
    try:
        await cart_service.handle_add_to_cart({
            "user_id": current_user.id,
            "product_id": payload.product_id,
            "quantity": payload.quantity,
            **({"mutation_id": str(mutation_id)} if mutation_id else {}),
        })
    except BaseException as exc:
        logger.warning("cart_add_request_failed error_type=%s elapsed_ms=%s", type(exc).__name__,
                       round((time.monotonic()-started)*1000), extra={"correlation_id": correlation_id})
        raise
    logger.info("cart_add_request_completed elapsed_ms=%s", round((time.monotonic()-started)*1000),
                extra={"correlation_id": correlation_id})
    return {"status": "accepted"}


@router.post("/cart/remove", status_code=status.HTTP_202_ACCEPTED)
async def remove_from_cart(
    payload: RemoveFromCartRequest,
    mutation_id: Optional[uuid.UUID] = Header(None, alias="Idempotency-Key"),
    current_user: models.User = Depends(deps.get_current_active_user),
    cart_service: AICartService = Depends(get_ai_cart_service),
):
    await cart_service.handle_remove_from_cart({
        "user_id": current_user.id,
        "product_id": payload.product_id,
        **({"mutation_id": str(mutation_id)} if mutation_id else {}),
    })
    return {"status": "accepted"}


@router.post("/cart/clear", status_code=status.HTTP_202_ACCEPTED)
async def clear_cart(
    current_user: models.User = Depends(deps.get_current_active_user),
    cart_service: AICartService = Depends(get_ai_cart_service),
):
    await cart_service.handle_clear_cart({"user_id": current_user.id})
    return {"status": "accepted"}


@router.post("/cart/save", status_code=status.HTTP_202_ACCEPTED)
async def save_cart(
    response: Response,
    current_user: models.User = Depends(deps.get_current_active_user),
    cart_service: AICartService = Depends(get_ai_cart_service),
):
    result = await cart_service.handle_save_cart({"user_id": current_user.id})
    result = result or {"status": "accepted"}  # Preserve older service adapters.
    response.headers["Cache-Control"] = "no-store"
    response.status_code = {"saved": 200, "accepted": 202, "empty": 409,
                            "rejected": 400, "cleanup_unconfirmed": 409,
                            "save_unconfirmed": 503}.get(result["status"], 503)
    return result


async def get_ai_nlu_service(
    request: Request,
    db: AsyncSession = Depends(deps.get_async_session),
    cache: IAsyncCacheClient = Depends(get_cache_from_request),
    rabbitmq: RabbitMQService = Depends(get_rabbitmq_service),
    commerce_engine=Depends(deps.get_ai_commerce_engine),
    llm_service=Depends(deps.get_llm_service),
) -> AINLUService:
    # Raises RuntimeError("AI infrastructure is offline") via the commerce
    # engine dependency when OpenSearch/Milvus are down; FastAPI surfaces
    # that as an honest 500 rather than a fake success.
    return AINLUService(
        db=db,
        search_engine=commerce_engine,
        rabbitmq=rabbitmq,
        cache=cache,
        llm_service=llm_service,
        behavior_engine=request.app.state.behavior,
    )


@router.post("/session/suggestions", status_code=status.HTTP_202_ACCEPTED)
async def initial_suggestions(
    current_user: models.User = Depends(deps.get_current_active_user),
    nlu_service: AINLUService = Depends(get_ai_nlu_service),
):
    """Personalized opening suggestions - the live path the chat worker ran."""
    await nlu_service.process_message({
        "user_id": current_user.id,
        "email": current_user.email,
        "message": "__INTERNAL_GET_INITIAL_SUGGESTIONS__",
        "type": "CHAT_MESSAGE",
        "client_msg_id": str(uuid.uuid4()),
    })
    return {"status": "accepted"}


@router.post("/session/reset", status_code=status.HTTP_202_ACCEPTED)
async def reset_session(
    current_user: models.User = Depends(deps.get_current_active_user),
    nlu_service: AINLUService = Depends(get_ai_nlu_service),
):
    """Reset recent chat context and request cart clear; saved preferences remain."""
    await nlu_service.process_message({
        "user_id": current_user.id,
        "email": current_user.email,
        "message": "__INTERNAL_RESET_SESSION__",
        "type": "CHAT_MESSAGE",
        "client_msg_id": str(uuid.uuid4()),
    })
    return {"status": "accepted"}


@router.get("/checkout/options")
async def checkout_options(
    current_user: models.User = Depends(deps.get_current_active_user),
    checkout_service: AICheckoutService = Depends(get_ai_checkout_service),
):
    return {"providers": checkout_service.orchestrator.available_providers,
            "currencies": [AICheckoutService.DEFAULT_CURRENCY.upper()], "countries": ["US"], "locale": "en-US"}


@router.post("/checkout/confirm", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("10/minute")
async def confirm_order(
    request: Request,
    response: Response,
    idempotency_key: uuid.UUID = Header(..., alias="Idempotency-Key"),
    payload: ConfirmOrderRequest = Body(...),
    current_user: models.User = Depends(deps.get_current_active_user),
    checkout_service: AICheckoutService = Depends(get_ai_checkout_service),
):
    result = await checkout_service.handle_confirm_order({
        "checkout_request_id": str(idempotency_key),
        "user_id": current_user.id,
        "email": current_user.email,
        "shipping_address": payload.shipping_address.model_dump(),
        "payment_provider": payload.payment_provider,
    })
    response.headers["Cache-Control"] = "no-store"
    result = result or {"status": "rejected"}
    response.status_code = {"ready": 200, "paid": 200, "pending": 202,
                            "conflict": 409, "review_required": 409, "reconciliation_required": 409,
                            "refresh_required": 409, "unconfirmed": 503}.get(result["status"], 400)
    return result


@router.post("/checkout/paypal/capture", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def capture_paypal_order(
    request: Request,
    payload: PayPalCaptureRequest = Body(...),
    current_user: models.User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(deps.get_async_session),
    rabbitmq: RabbitMQService = Depends(get_rabbitmq_service),
    cache: IAsyncCacheClient = Depends(get_cache_from_request),
):
    """Capture a buyer-approved PayPal order and finalize the local order.

    Called by the frontend when PayPal redirects the buyer back. Verifies the
    local order belongs to the caller before touching PayPal.
    """
    order = await db.get(models.Order, int(payload.order_id))
    if not order or order.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if order.payment_transaction_id != payload.paypal_order_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment does not match this order")
    if order.status not in {models.OrderStatus.PENDING, models.OrderStatus.FAILED} and not order.is_paid:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Order cannot accept payment")
    try:
        gateway = PayPalGateway(get_paypal_settings(), cache, httpx.AsyncClient(timeout=httpx.Timeout(5.0)))
    except Exception as exc:
        logger.error("PayPal gateway unavailable for capture: %s", exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="PayPal unavailable")

    try:
        result = await gateway.capture_order(
            payload.paypal_order_id, expected_order_id=order.id, expected_user_id=current_user.id,
            expected_amount=Decimal(str(order.total_price)), expected_currency=order.currency,
        )
    finally:
        await gateway._http_client.aclose()

    if result.status != PaymentStatus.SUCCESS:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=result.error_message or "Capture failed")

    completion = PaymentCompletionService(db, rabbitmq, cache)
    await completion.finalize_successful_payment(
        order_id=int(payload.order_id),
        user_id=current_user.id,
        transaction_id=payload.paypal_order_id,
    )
    return {"status": "captured", "order_id": payload.order_id}


@router.post("/checkout/cancel", status_code=status.HTTP_202_ACCEPTED)
async def cancel_order(
    payload: CancelOrderRequest = Body(default_factory=CancelOrderRequest),
    current_user: models.User = Depends(deps.get_current_active_user),
    checkout_service: AICheckoutService = Depends(get_ai_checkout_service),
):
    result = await checkout_service.handle_cancel_order({
        "user_id": current_user.id,
        "order_id": payload.order_id,
    })
    # Preserve202 compatibility for older service adapters, never label a
    # known refusal as accepted. All current service outcomes are explicit.
    if result is None:
        return {"status":"accepted"}
    code={"cancelled":200,"not_found":404,"order_required":400,"invalid_request":422,
          "requires_review":409,"provider_reconciliation_required":409,"unconfirmed":503}[result["status"]]
    return Response(content=json.dumps(result),status_code=code,media_type="application/json",headers={"Cache-Control":"no-store"})


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

            # C. This socket is receive-only for AI/cart responses (Redis
            # relay below). Chat text, images and cart/checkout commands are
            # served by the HTTP endpoints (ai-support, ai-ordering). The old
            # behavior published these frames to RabbitMQ queues that no
            # worker in this stack consumes and then ACKed them as "queued",
            # which silently dropped every command. Fail honestly instead.
            logger.warning(
                "Inbound command on receive-only socket rejected",
                extra={"user_id": current_user.id, "type": message_data.get("type")},
            )
            await websocket.send_json({
                "type": "ERROR",
                "code": "UNSUPPORTED_CHANNEL",
                "content": "This channel no longer accepts commands. Please use the chat interface, which calls the HTTP API directly.",
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
