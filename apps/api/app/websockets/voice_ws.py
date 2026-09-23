# apps/api/app/websockets/voice_ws.py

import logging
import time
from typing import Final

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.services.ai_commerce_engine import AICommerceEngine, get_ai_commerce_engine
from app.services.ai_voice_service import AIVoiceOrchestrator

logger = logging.getLogger("airdeliver.websockets.voice")

router = APIRouter()

_TICKET_VALIDATION_ERROR: Final[str] = "INVALID_TICKET"

@router.websocket("/voice-stream")
async def voice_stream_endpoint(
    websocket: WebSocket,
    ticket: str,
    commerce_engine: AICommerceEngine = Depends(get_ai_commerce_engine),
) -> None:
    """
    Establishes a bi-directional audio tunnel for the AI Voice Assistant.
    Enforces strict connection lifecycle and error boundary isolation.
    """
    # Note: In a production environment, cryptographic validation of the 'ticket'
    # must occur here before accepting the socket to prevent unauthenticated resource exhaustion.
    if not ticket or ticket.strip() == "":
        await websocket.close(code=1008, reason=_TICKET_VALIDATION_ERROR)
        logger.warning("Voice connection rejected: Missing or empty auth ticket.")
        return

    # User identity extraction should ideally be decoded from a signed JWT/ticket.
    # Hardcoded for architectural demonstration based on the provided context.
    user_id = "user_authenticated"
    session_id = f"voice_ws_{user_id}_{int(time.time())}"

    orchestrator = AIVoiceOrchestrator(commerce_engine=commerce_engine)

    try:
        logger.info("Initializing voice session.", extra={"session_id": session_id, "user_id": user_id})
        await orchestrator.process_voice_session(websocket, user_id=user_id)

    except WebSocketDisconnect as exc:
        logger.info(
            "Voice client disconnected gracefully.",
            extra={"session_id": session_id, "code": exc.code}
        )
    except Exception as exc:
        logger.error(
            "Critical failure in voice orchestrator lifecycle.",
            extra={"session_id": session_id, "error_type": type(exc).__name__, "error": str(exc)},
            exc_info=True
        )
    finally:
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.close(code=1011)
            except Exception as close_exc:
                logger.warning(
                    "Failed to close websocket deterministically.",
                    extra={"session_id": session_id, "error": str(close_exc)}
                )
