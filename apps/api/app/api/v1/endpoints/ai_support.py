from fastapi import APIRouter
from app.schemas.ai_ordering import ChatRequest, ChatResponse # Re-using the same schema for simplicity
from app.services.ai_support_service import ai_support_service

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
def handle_chat_message(request: ChatRequest):
    """
    Main endpoint for the AI Support Assistant.
    """
    responses = ai_support_service.handle_message(request.message)
    return {"responses": responses}
```

### **3. تحديث `api.py` لإضافة القسم الجديد**
```python
# ... (existing imports)
from .endpoints import ..., ai_support # Add ai_support

# ... (existing router includes)
api_router.include_router(ai_support.router, prefix="/ai-support", tags=["AI Support"]) # Add this line
