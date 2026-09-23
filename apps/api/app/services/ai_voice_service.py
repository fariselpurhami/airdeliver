# apps/api/app/services/ai_voice_service.py

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Final, List, Optional, Set

import websockets
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ValidationError
from sqlmodel.ext.asyncio.session import AsyncSession
from websockets.exceptions import ConnectionClosed

from app.services.ai_commerce_engine import AICommerceEngine
from app.services.free_llm_service import FreeLLMService
from app.services.rabbitmq_service import RabbitMQService
from app.services.cache_service import IAsyncCacheClient
from app.services.ai_nlu_service import ProductAccess, RedisKeys, UserDnaStore, MatrixConfig

# ---------------------------------------------------------------------------
# CORE CONFIGURATION & SCHEMAS
# ---------------------------------------------------------------------------

class VoiceConfig:
    ELEVENLABS_API_KEY: Final[str | None] = os.getenv("ELEVENLABS_API_KEY")
    ELEVENLABS_AGENT_ID: Final[str | None] = os.getenv("ELEVENLABS_AGENT_ID")
    ELEVENLABS_WS_URL_TEMPLATE: Final[str] = "wss://api.elevenlabs.io/v1/convai/conversation?agent_id={agent_id}"
    
    MAX_AUDIO_QUEUE_SIZE: Final[int] = 60 
    MAX_TEXT_BUFFER_SIZE: Final[int] = 512
    TOOL_EXECUTION_TIMEOUT_SEC: Final[float] = 12.0
    WS_PING_INTERVAL: Final[int] = 20
    WS_PING_TIMEOUT: Final[int] = 20

    @classmethod
    def get_ws_url(cls) -> str:
        if not cls.ELEVENLABS_AGENT_ID:
            raise ValueError("CRITICAL_CONFIGURATION_ERROR: ELEVENLABS_AGENT_ID is not set.")
        return cls.ELEVENLABS_WS_URL_TEMPLATE.format(agent_id=cls.ELEVENLABS_AGENT_ID)

    @classmethod
    def get_auth_headers(cls) -> dict[str, str]:
        if not cls.ELEVENLABS_API_KEY:
            raise ValueError("CRITICAL_CONFIGURATION_ERROR: ELEVENLABS_API_KEY is not set.")
        return {"xi-api-key": cls.ELEVENLABS_API_KEY}


class ClientMessageType(str, Enum):
    INTERRUPT = "INTERRUPT"
    ERROR = "error"
    TEXT_STREAM = "text_stream"
    CONTROL = "control"
    PRODUCT_CAROUSEL = "product_carousel"
    SYSTEM_ACK = "system_ack"


class CartAction(str, Enum):
    ADD = "ADD"
    REMOVE = "REMOVE"
    CLEAR = "CLEAR"
    CHECKOUT = "CHECKOUT"


# ---------------------------------------------------------------------------
# OBSERVABILITY
# ---------------------------------------------------------------------------

logger = logging.getLogger("airdeliver.voice_core")
logger.setLevel(logging.INFO)

def _structured_log(event: str, level: int = logging.INFO, **context: Any) -> None:
    log_record = {
        "event": event,
        "timestamp": time.time(),
        "component": "AIVoiceOrchestrator",
        **{k: v for k, v in context.items() if v is not None}
    }
    logger.log(level, json.dumps(log_record, default=str))

# ---------------------------------------------------------------------------
# DOMAIN LOGIC: TOOL EXECUTION ENGINE
# ---------------------------------------------------------------------------

class VoiceToolExecutor:
    """
    Isolates external tool execution from the WebSocket transport layer.
    Executes operations against the core OS and formats results for the Voice AI.
    """
    def __init__(
        self,
        commerce_engine: AICommerceEngine,
        llm_service: FreeLLMService,
        rabbitmq: RabbitMQService,
        cache: IAsyncCacheClient,
        db_session: AsyncSession
    ) -> None:
        self.commerce = commerce_engine
        self.llm = llm_service
        self.rabbitmq = rabbitmq
        self.cache = cache
        self.db = db_session

    async def search_global_inventory(self, params: Dict[str, Any], user_id: str, client_ws: WebSocket) -> str:
        """Executes hybrid search, pushes UI update to client, returns context to Voice AI."""
        query = params.get("query", "")
        category = params.get("category")
        price_max = params.get("price_max")
        
        filters = {}
        if category: filters["category"] = category
        if price_max: filters["price_max"] = float(price_max)

        products = await self.commerce.perform_hybrid_search_pure(
            self.db, 
            query=query, 
            limit=5, 
            filters=filters
        )

        if not products:
            return json.dumps({"status": "NO_MATCHES", "message": "No verified products found matching criteria."})

        # 1. Broadcast Visual State to UI synchronously
        safe_products = [ProductAccess.dump(p) for p in products]
        ui_payload = {
            "type": ClientMessageType.PRODUCT_CAROUSEL.value,
            "products": safe_products,
            "reason": f"Visual retrieval for: {query}"
        }
        try:
            await client_ws.send_text(json.dumps(ui_payload))
        except Exception as e:
            _structured_log("ui_sync_failed", logging.WARNING, error=str(e), user_id=user_id)

        # 2. Return compact intelligence to the Voice Agent
        ai_context = [
            {
                "id": p["id"],
                "name": p["name"],
                "price": p["price"],
                "key_specs": str(p["description"])[:100]
            }
            for p in safe_products[:3]
        ]
        return json.dumps({"status": "SUCCESS", "inventory": ai_context})

    async def execute_cart_action(self, params: Dict[str, Any], user_id: str, client_ws: WebSocket) -> str:
        """Dispatches event-driven cart actions via RabbitMQ."""
        try:
            action = CartAction(params.get("action", "").upper())
        except ValueError:
            return json.dumps({"status": "FAILED", "error": "Invalid action. Allowed: ADD, REMOVE, CLEAR, CHECKOUT"})

        product_id = params.get("product_id")
        
        routing_key = ""
        payload = {"user_id": int(user_id), "source": "voice_ai_os"}

        if action == CartAction.ADD:
            if not product_id: return json.dumps({"error": "product_id required for ADD"})
            routing_key = "airdeliver.ai.cart.add"
            payload.update({"product_id": int(product_id), "quantity": 1, "notify_user": False})
        elif action == CartAction.REMOVE:
            if not product_id: return json.dumps({"error": "product_id required for REMOVE"})
            routing_key = "airdeliver.ai.cart.remove"
            payload.update({"product_id": int(product_id), "action": "remove_by_id", "notify_user": False})
        elif action == CartAction.CLEAR:
            routing_key = "airdeliver.ai.cart.clear"
            payload.update({"notify_user": True})
        elif action == CartAction.CHECKOUT:
            routing_key = "airdeliver.ai.order.confirm"
            payload.update({"type": "payment_intent", "timestamp": time.time()})

        try:
            await self.rabbitmq.publish(payload, routing_key)
            return json.dumps({"status": "SUCCESS", "action_executed": action.value})
        except Exception as e:
            _structured_log("cart_action_dispatch_failed", logging.ERROR, error=str(e), user_id=user_id)
            return json.dumps({"status": "FAILED", "error": "Internal broker failure."})

    async def verify_phantom_product(self, params: Dict[str, Any], user_id: str) -> str:
        """The Phantom Protocol: Triggers deep web search for unreleased/rumored items."""
        query = params.get("query", "")
        if not query:
            return json.dumps({"error": "Empty query"})
            
        intel = await self.llm._perform_web_search(query)
        return json.dumps({
            "status": "WEB_INTEL_RETRIEVED", 
            "advisory": "Use this strictly to debunk or confirm unreleased items. NEVER invent specs.",
            "data": intel[:1000] 
        })

# ---------------------------------------------------------------------------
# CORE SYSTEM: THE VOICE ORCHESTRATOR
# ---------------------------------------------------------------------------

class AIVoiceOrchestrator:
    """
    Enterprise-Grade Conversational Voice Bridge (ElevenLabs v3).
    
    Architecture:
      - Full-Duplex asynchronous streams bridging Client WS and ElevenLabs WS.
      - Intercepts Server-Sent Client Tool Calls, executes them via internal OS, 
        and synchronizes Frontend State natively.
      - Backpressure dropping mechanisms to prevent memory leaks on high latency.
    """

    def __init__(
        self, 
        commerce_engine: AICommerceEngine,
        llm_service: FreeLLMService,
        rabbitmq: RabbitMQService,
        cache: IAsyncCacheClient,
        db_session: AsyncSession
    ) -> None:
        self.cache = cache
        self.db = db_session
        self.tool_executor = VoiceToolExecutor(commerce_engine, llm_service, rabbitmq, cache, db_session)

    async def process_voice_session(self, client_ws: WebSocket, user_id: str) -> None:
        """Bootstraps the secure bi-directional tunnel and injects user DNA."""
        await client_ws.accept()
        session_id = f"v_sess_{user_id}_{uuid.uuid4().hex[:6]}"
        start_time = time.perf_counter()
        
        _structured_log("voice_session_initiated", user_id=user_id, session_id=session_id)
        
        eleven_ws: Optional[websockets.WebSocketClientProtocol] = None
        tasks: Set[asyncio.Task] = set()

        try:
            # 1. Establish Upstream Connection
            try:
                eleven_ws = await websockets.connect(
                    VoiceConfig.get_ws_url(),
                    extra_headers=VoiceConfig.get_auth_headers(),
                    ping_interval=VoiceConfig.WS_PING_INTERVAL,
                    ping_timeout=VoiceConfig.WS_PING_TIMEOUT
                )
            except Exception as e:
                _structured_log("upstream_connection_failed", logging.ERROR, error=str(e), session_id=session_id)
                await self._send_client_error(client_ws, "Voice Neural Net temporarily offline.")
                return

            # 2. Inject Dynamic Context (User DNA & Memory)
            await self._inject_session_context(eleven_ws, user_id)

            # 3. Concurrency Primitives
            audio_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=VoiceConfig.MAX_AUDIO_QUEUE_SIZE)
            
            # 4. Spawn Duplex Micro-Tasks
            reader_task = asyncio.create_task(self._ingress_reader(client_ws, audio_queue, session_id))
            feeder_task = asyncio.create_task(self._upstream_feeder(eleven_ws, audio_queue, session_id))
            speaker_task = asyncio.create_task(self._egress_speaker(client_ws, eleven_ws, session_id, user_id))
            
            tasks.update({reader_task, feeder_task, speaker_task})

            # 5. Circuit Breaker Wait Loop
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

            for task in done:
                try:
                    task.result()
                except (WebSocketDisconnect, ConnectionClosed):
                    pass 
                except Exception as e:
                    _structured_log("task_abnormal_termination", logging.ERROR, error=str(e), session_id=session_id)

        finally:
            # 6. Deterministic Resource Teardown
            _structured_log("session_teardown", duration_sec=round(time.perf_counter() - start_time, 2), session_id=session_id)
            
            for task in tasks:
                if not task.done(): task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            if eleven_ws and not eleven_ws.closed:
                with contextlib.suppress(Exception):
                    await eleven_ws.close()

    async def _inject_session_context(self, eleven_ws: websockets.WebSocketClientProtocol, user_id: str) -> None:
        """Injects User DNA to align the ElevenLabs Agent persona natively."""
        try:
            # Extract user DNA from central cache store (fallback safely)
            dna_store = UserDnaStore(self.cache, None, MatrixConfig())
            user_dna = await dna_store.get(int(user_id))
            
            init_payload = {
                "type": "conversation_initiation_client_data",
                "dynamic_variables": {
                    "user_tier": user_dna.tier,
                    "user_persona": user_dna.persona
                }
            }
            await eleven_ws.send(json.dumps(init_payload))
        except Exception as e:
            _structured_log("context_injection_skipped", logging.WARNING, error=str(e), user_id=user_id)

    async def _ingress_reader(self, client_ws: WebSocket, queue: asyncio.Queue[bytes], session_id: str) -> None:
        """Reads raw PCM from client, implements Drop-Oldest backpressure."""
        while True:
            message = await client_ws.receive()
            
            if "bytes" in message:
                if queue.full():
                    try:
                        queue.get_nowait()
                        _structured_log("audio_queue_overflow", logging.WARNING, session_id=session_id)
                    except asyncio.QueueEmpty: pass
                await queue.put(message["bytes"])

            elif "text" in message:
                try:
                    data = json.loads(message["text"])
                    if data.get("type") == ClientMessageType.INTERRUPT.value:
                        # Clear buffer on interruption to immediately halt processing
                        while not queue.empty(): queue.get_nowait()
                except json.JSONDecodeError: pass

    async def _upstream_feeder(self, eleven_ws: websockets.WebSocketClientProtocol, queue: asyncio.Queue[bytes], session_id: str) -> None:
        """Pushes Base64 encoded audio to ElevenLabs."""
        while True:
            audio_chunk = await queue.get()
            payload = {"user_audio_chunk": base64.b64encode(audio_chunk).decode("utf-8")}
            await eleven_ws.send(json.dumps(payload))

    async def _egress_speaker(self, client_ws: WebSocket, eleven_ws: websockets.WebSocketClientProtocol, session_id: str, user_id: str) -> None:
        """Parses upstream events: Routes Audio, Subtitles, and Client Tool Calls."""
        async for message in eleven_ws:
            try:
                data = json.loads(message)
            except json.JSONDecodeError: continue

            msg_type = data.get("type")

            # 1. Ultra-Low Latency Audio Path
            if msg_type == "audio":
                b64_audio = data.get("audio_base64")
                if b64_audio:
                    with contextlib.suppress(Exception):
                        await client_ws.send_bytes(base64.b64decode(b64_audio))

            # 2. Text/Subtitle Path
            elif msg_type == "agent_response":
                text_token = data.get("agent_response_event", {}).get("agent_response")
                if text_token:
                    with contextlib.suppress(Exception):
                        await client_ws.send_text(json.dumps({"type": ClientMessageType.TEXT_STREAM.value, "text": text_token}))

            # 3. INTERCEPTOR: Client Tool Calls (The Bridge to Commerce OS)
            elif msg_type == "client_tool_call":
                tool_call_id = data.get("tool_call_id")
                tool_name = data.get("tool_name")
                params = data.get("parameters", {})
                
                _structured_log("tool_call_intercepted", tool=tool_name, session_id=session_id)
                
                # Spawn non-blocking task so audio ingestion continues
                asyncio.create_task(
                    self._handle_client_tool_call(eleven_ws, client_ws, tool_call_id, tool_name, params, user_id, session_id)
                )

    async def _handle_client_tool_call(
        self, 
        eleven_ws: websockets.WebSocketClientProtocol, 
        client_ws: WebSocket, 
        tool_call_id: str, 
        tool_name: str, 
        params: Dict[str, Any], 
        user_id: str,
        session_id: str
    ) -> None:
        """Routes the tool call to the Domain Executor and returns the payload to ElevenLabs."""
        try:
            # Enforce strict execution timeout
            async with asyncio.timeout(VoiceConfig.TOOL_EXECUTION_TIMEOUT_SEC):
                
                if tool_name == "search_global_inventory":
                    result = await self.tool_executor.search_global_inventory(params, user_id, client_ws)
                
                elif tool_name == "execute_cart_action":
                    result = await self.tool_executor.execute_cart_action(params, user_id, client_ws)
                
                elif tool_name == "verify_phantom_product":
                    result = await self.tool_executor.verify_phantom_product(params, user_id)
                
                else:
                    result = json.dumps({"error": f"Unknown tool: {tool_name}"})

        except asyncio.TimeoutError:
            _structured_log("tool_execution_timeout", logging.ERROR, tool=tool_name, session_id=session_id)
            result = json.dumps({"error": "Internal database timeout. Inform user gracefully."})
        except Exception as e:
            _structured_log("tool_execution_crash", logging.ERROR, error=str(e), tool=tool_name, session_id=session_id)
            result = json.dumps({"error": "System failure during execution."})

        # Return execution result back to ElevenLabs
        try:
            response_payload = {
                "type": "client_tool_result",
                "tool_call_id": tool_call_id,
                "result": result,
                "is_error": "error" in result.lower()
            }
            await eleven_ws.send(json.dumps(response_payload))
        except Exception as e:
            _structured_log("tool_result_dispatch_failed", logging.ERROR, error=str(e), session_id=session_id)

    async def _send_client_error(self, client_ws: WebSocket, message: str) -> None:
        """Graceful degradation signaling."""
        with contextlib.suppress(Exception):
            await client_ws.send_text(json.dumps({"type": ClientMessageType.ERROR.value, "message": message}))
