# apps/api/app/services/ai_voice_service.py

import asyncio
import json
import logging
import re
import struct
import math
import time
from typing import AsyncGenerator, Dict, Any, List, Optional
from fastapi import WebSocket, WebSocketDisconnect

# Internal Services
from app.services.ai_commerce_engine import AICommerceEngine, get_ai_commerce_engine
# 💎 SOTA LOGGING WITH TELEMETRY (Hybrid Mode)
logger = logging.getLogger("airdeliver.voice_core")

def force_log(message: str, level: str = "INFO"):
    """
    🚀 NUCLEAR LOGGING: Bypasses standard logger buffering.
    Ensures logs appear in Docker instantly.
    """
    if level == "ERROR":
        logger.error(message)
    else:
        logger.info(message)
class AIVoiceOrchestrator:
    """
    🎤 TITANIUM VOICE ORCHESTRATOR (V5.1 - DEBUG & WARFARE EDITION).
    
    Architectural Pattern: Full-Duplex Async Pipeline with Backpressure Management.
    Model: nvidia/personaplex-7b-v1 (Native Audio-to-Audio).
    """

    # --- ⚙️ PHYSICS CONSTANTS ---
    # 🛑 FORCE OPEN GATE: 0 means "Process Everything" (Even Silence)
    SILENCE_THRESHOLD = 500 
    
    # Max buffer size (approx 1-2 seconds of audio)
    MAX_QUEUE_SIZE = 50 

    def __init__(self, llm_service=None, commerce_engine: AICommerceEngine = None):
        self.commerce = commerce_engine
        
        # 🎭 SYSTEM CONDITIONING
        self.system_condition = """
        You are AirDeliver.
        ROLE: High-end Shopping Assistant.
        TONE: Warm, Professional, Concise.
        INSTRUCTION: When mentioning a product, output the token [SHOW: query].
        """

    async def process_voice_session(self, websocket: WebSocket, user_id: int):
        """
        🚀 The Main Loop: Orchestrates the secure bi-directional tunnel.
        """
        # 1. Handshake & Lock
        await websocket.accept()
        start_time = time.perf_counter()
        force_log(f"🎙️ Voice Tunnel Opened: User {user_id}")
        
        model_session = None

        try:
            # 2. Initialize Model Session
            force_log("⏳ [1/4] Requesting Session from AI Manager...")
            
            # 🛡️ PROTECTED CALL: Wraps external dependency
            try:
                model_session = await ai_manager.create_voice_session(
                    user_id=user_id,
                    system_prompt=self.system_condition
                )
                force_log(f"✅ [2/4] Session Created ID: {id(model_session)}")
            except Exception as session_err:
                force_log(f"🔥 FATAL: AI Manager failed to create session: {session_err}", "ERROR")
                raise session_err

            # 3. Task Management (The Engine Room)
            input_queue = asyncio.Queue(maxsize=self.MAX_QUEUE_SIZE)
            
            # 4. Launch Micro-Services (Concurrent Coroutines)
            force_log("🚀 [3/4] Launching Async Micro-Kernels...")
            
            reader_task = asyncio.create_task(self._network_reader(websocket, input_queue))
            feeder_task = asyncio.create_task(self._model_feeder(model_session, input_queue)) # Fixed Args
            speaker_task = asyncio.create_task(self._output_loop(websocket, model_session))
            
            force_log("💎 [4/4] ALL SYSTEMS GO. Waiting for Audio Packets...")

            # 5. Watchdog (Wait for any failure or closure)
            done, pending = await asyncio.wait(
                [reader_task, feeder_task, speaker_task], 
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # 6. Cleanup Protocol
            force_log(f"🛑 Voice Session Closing... (Duration: {time.perf_counter() - start_time:.2f}s)")
            for task in pending: 
                task.cancel()
                try: 
                    await task 
                except: 
                    pass

        except WebSocketDisconnect:
            force_log(f"👋 User Disconnected: {user_id}")
        except Exception as e:
            force_log(f"🔥 Critical Voice Failure: {e}", "ERROR")
            try:
                await websocket.send_text(json.dumps({"type": "error", "message": "Voice Core Restarting..."}))
            except: pass
        finally:
            if model_session:
                force_log("🧹 Cleaning up Model Session...")
                await model_session.close()

    async def _network_reader(self, websocket: WebSocket, queue: asyncio.Queue):
        """
        📡 NETWORK INGRESS (Layer 1).
        Reads bytes from socket fast. Pushes to buffer.
        """
        force_log("📡 Network Reader: ACTIVE")
        try:
            while True:
                message = await websocket.receive()
                
                if "bytes" in message:
                    # 🌊 Backpressure Handling: Drop-Tail Strategy
                    if queue.full():
                        try: queue.get_nowait()
                        except: pass
                    
                    await queue.put(message["bytes"])

                elif "text" in message:
                    # Handle Control Signals
                    data = json.loads(message["text"])
                    if data.get("type") == "INTERRUPT":
                        force_log("⚡ INTERRUPT RECEIVED")
                        pass 

        except Exception as e:
            force_log(f"❌ Network Reader Stopped: {e}")

    async def _model_feeder(self, session, queue: asyncio.Queue):
        """
        🧠 INTELLIGENT ROUTER (Layer 2 - DEBUG MODE).
        Feeds Model directly without VAD filtering.
        """
        force_log("🟢 Model Feeder: ACTIVE")
        chunk_count = 0

        try:
            while True:
                # 1. Pull Audio
                audio_chunk = await queue.get()
                chunk_count += 1
                
                # 2. Debug Logging (Every 20 chunks ~ 1 sec)
                if chunk_count % 20 == 0:
                     force_log(f"🎤 [Feeding GPU] Chunk #{chunk_count} | Size: {len(audio_chunk)} bytes")

                # 3. Direct Push (No Logic, No Delay)
                try:
                    await session.push_audio(audio_chunk)
                except Exception as e:
                    force_log(f"🔥 Model Push Error: {e}", "ERROR")
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            force_log(f"❌ Model Feeder Died: {e}", "ERROR")

    async def _output_loop(self, websocket: WebSocket, session):
        """
        🗣️ EGRESS & UI CONTROLLER (Layer 3).
        Streams audio back. Detects UI commands.
        """
        force_log("🔊 Speaker Loop: ACTIVE (Listening to Brain...)")
        text_buffer = "" 

        try:
            async for output in session.stream_output():
                
                # A. Debug Trace
                if output.text_token:
                    force_log(f"🗣️ [AI SAID]: {output.text_token}")

                # B. Fast Audio Path
                if output.audio_bytes:
                    await websocket.send_bytes(output.audio_bytes)
                
                # C. Logic Path (UI Triggers)
                if output.text_token:
                    text_buffer += output.text_token
                    
                    # Optimization: Keep buffer small
                    if len(text_buffer) > 100: 
                        text_buffer = text_buffer[-50:] 

                    # Check Trigger
                    await self._check_ui_triggers(text_buffer, websocket)
                    
                    # Stream Subtitles
                    await websocket.send_text(json.dumps({
                        "type": "text_stream",
                        "text": output.text_token
                    }))
                    
        except Exception as e:
            force_log(f"❌ Output Loop Stopped: {e}")

    async def _check_ui_triggers(self, text_buffer: str, websocket: WebSocket):
        """
        🕵️ Pattern Matching Engine.
        """
        try:
            match = re.search(r'\[SHOW:\s*(.*?)\]', text_buffer)
            if match:
                query = match.group(1).strip()
                force_log(f"⚡ UI TRIGGER DETECTED: {query}")
                
                await websocket.send_text(json.dumps({
                    "type": "control",
                    "payload": {
                        "action": "VOICE_SEARCH",
                        "query": query
                    }
                }))
        except Exception as e:
            force_log(f"⚠️ Trigger Error: {e}")
