# backend/api/app/websockets/voice_ws.py

import logging
import time
from typing import Final

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query, status
from starlette.websockets import WebSocketState
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api import deps
from app.services.ai_commerce_engine import AICommerceEngine, get_ai_commerce_engine
from app.services.ai_voice_service import AIVoiceOrchestrator
from app.services.cache_service import IAsyncCacheClient
from app.services.free_llm_service import FreeLLMService
from app.services.rabbitmq_service import RabbitMQService
from app import models

logger = logging.getLogger("airdeliver.websockets.voice")

router = APIRouter()

_TICKET_VALIDATION_ERROR: Final[str] = "INVALID_TICKET"

@router.websocket("/voice-stream")
async def voice_stream_endpoint(
    websocket: WebSocket,
    ticket: str = Query(default=None),
    session: AsyncSession = Depends(deps.get_async_session),
    cache: IAsyncCacheClient = Depends(deps.get_cache_client),
    commerce_engine: AICommerceEngine = Depends(get_ai_commerce_engine),
    llm_service: FreeLLMService = Depends(deps.get_llm_service),
    rabbitmq: RabbitMQService = Depends(deps.get_rabbitmq_service),
) -> None:
    """
    Establishes a bi-directional audio tunnel for the AI Voice Assistant.
    Enforces the same one-time ticket auth as the /chat socket
    (POST /api/v1/ordering/ticket issues it; tickets live 30s, single use).
    """
    # 1. AUTHENTICATION PHASE (one-time ticket, real user identity)
    try:
        current_user: models.User = await deps.get_current_active_user_ws_ticket(
            websocket=websocket,
            ticket=ticket,
            session=session,
            cache=cache,
        )
    except Exception:
        logger.warning("Voice connection rejected: missing/invalid/expired ticket.")
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=_TICKET_VALIDATION_ERROR)
        return

    user_id = str(current_user.id)
    session_id = f"voice_ws_{user_id}_{int(time.time())}"

    orchestrator = AIVoiceOrchestrator(
        commerce_engine=commerce_engine,
        llm_service=llm_service,
        rabbitmq=rabbitmq,
        cache=cache,
        db_session=session,
    )

    try:
        logger.info('Initializing voice session.', extra={'user_id': user_id})
        await orchestrator.process_voice_session(websocket, user_id=user_id)

    except WebSocketDisconnect as exc:
        logger.info('Voice client disconnected gracefully.', extra={'code': exc.code})
    except Exception as exc:
        logger.error('Critical failure in voice orchestrator lifecycle.', extra={'error_type': type(exc).__name__})
    finally:
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.close(code=1011)
            except Exception as close_exc:
                logger.warning('Failed to close websocket deterministically.', extra={})
