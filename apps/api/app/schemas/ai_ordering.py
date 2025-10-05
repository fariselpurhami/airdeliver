# file: apps/api/app/schemas/ai_ordering.py
# version: 1.0.0
# date: 2025-09-27
# author: Gemini

from pydantic import BaseModel
from typing import List, Any

class ChatRequest(BaseModel):
    message: str
    # In a stateful version, you would also pass conversation_id or history
    # history: List[dict] = []

class ChatResponse(BaseModel):
    responses: List[dict] # A list of response objects to be rendered
