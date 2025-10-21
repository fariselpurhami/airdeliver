# file: apps/api/app/schemas/ai_ordering.py
from pydantic import BaseModel
from typing import List, Dict, Any

# This is your existing schema for incoming messages
class ChatRequest(BaseModel):
    message: str

# --- ADD THESE NEW CLASSES ---

# This defines the structure for a single part of the AI's response
class ResponseMessage(BaseModel):
    contentType: str
    content: Any | None = None
    options: List[str] | None = None
    products: List[Dict[str, Any]] | None = None
    reason: str | None = None

# This defines the overall shape of the final JSON response from the /chat endpoint
class ChatResponse(BaseModel):
    responses: List[ResponseMessage]

# --------------------------
