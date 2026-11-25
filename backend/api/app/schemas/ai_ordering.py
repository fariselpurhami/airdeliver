# backend/api/app/schemas/ai_ordering.py

from pydantic import BaseModel
from typing import List, Dict, Any

class ChatRequest(BaseModel):
    message: str

class ResponseMessage(BaseModel):
    contentType: str
    content: Any | None = None
    options: List[str] | None = None
    products: List[Dict[str, Any]] | None = None
    reason: str | None = None

class ChatResponse(BaseModel):
    responses: List[ResponseMessage]

