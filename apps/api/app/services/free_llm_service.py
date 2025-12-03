# apps/api/app/services/free_llm_service.py

import json
import logging
import os
import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from groq import AsyncGroq

logger = logging.getLogger("airdeliver.services.cognitive_core")

class ProductContext(BaseModel):
    id: int
    name: str
    category: str
    price: float
    tags: Optional[List[str]] = []
    description: Optional[str] = ""
    attributes: Optional[Dict[str, Any]] = {}

class CognitiveResponse(BaseModel):
    selected_ids: List[int] = Field(..., description="Top matching product IDs")
    reasoning: Dict[int, str] = Field(..., description="The 'Why' behind the selection")
    intro_message: str = Field(..., description="The persuasive hook")
    confidence_score: float = Field(..., description="0.0 to 1.0 certainty metric")

class FreeLLMService:
    _instance = None
    _client: Optional[AsyncGroq] = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FreeLLMService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized: return
        self.api_key = os.getenv("GROQ_API_KEY")
        self.brain_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.reflex_model = "llama-3.1-8b-instant"
        
        if not self.api_key:
            logger.critical("GROQ_API_KEY missing. Cognitive Core is OFFLINE.")
            
        self._initialized = True

    @property
    def client(self) -> Optional[AsyncGroq]:
        if not self._client and self.api_key:
            try:
                self._client = AsyncGroq(api_key=self.api_key)
            except Exception as e:
                logger.critical(f"Neural Uplink Failed: {e}")
                return None
        return self._client

    async def _safe_execute(self, func, *args, **kwargs):
        retries = 2
        for i in range(retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if i == retries:
                    logger.error(f"Execution Exhausted: {e}")
                    raise e
                await asyncio.sleep(0.5 * (2 ** i))

    async def consult_on_product(self, product_data: Dict[str, Any], user_question: str) -> str:
        if not self.client:
            return f"This {product_data.get('name')} is a premium item."

        system_core = f"""
        IDENTITY: You are 'order with air', a Hyper-Intelligent Global Commerce Architect.
        MISSION: Analyze the product with 'Forensic Precision' and advise the user with 'Executive Authority'.

        --- DATA INGESTION ---
        PRODUCT: {json.dumps(product_data, default=str)}

        --- POLYGLOT PROTOCOL (CRITICAL) ---
        1. DETECT LANGUAGE: Identify the language of the User's Question (e.g., Arabic, French, Spanish).
        2. MIRROR: Respond STRICTLY in that same language and dialect.
        3. ADAPT: If speaking Arabic, use professional yet warm Arabic (Modern Standard or polite dialect).

        --- COGNITIVE PROTOCOLS ---
        
        PHASE 1: DOMAIN RECOGNITION
        - Scan the product category.
        - *IF Tech:* Adopt persona of **Senior Systems Architect**.
        - *IF Beauty:* Adopt persona of **Clinical Dermatologist**.
        - *IF Fashion:* Adopt persona of **Creative Director**.
        - *IF Home:* Adopt persona of **Material Engineer**.

        PHASE 2: THE BRIDGE (Feature -> Benefit)
        - NEVER output a raw spec.
        - *Arabic Example:* Instead of "فيه بطارية 5000"، Say: "بطارية الـ 5000 ملي أمبير تضمن لك يوماً كاملاً من العمل الشاق دون الحاجة للشاحن."
        - *English Example:* "The '5000mAh battery' ensures all-day endurance..."

        PHASE 3: TRUTH ANCHORING
        - If features are missing, do not hallucinate. Use deductive reasoning based on category.

        --- OUTPUT GUIDELINES ---
        - Format: 3 Sentences Max.
        - Style: Start directly with the verdict. Use single quotes for specs.
        """

        try:
            completion = await self._safe_execute(
                self.client.chat.completions.create,
                messages=[
                    {"role": "system", "content": system_core},
                    {"role": "user", "content": user_question}
                ],
                model=self.brain_model,
                temperature=0.35, 
                max_tokens=400
            )
            return completion.choices[0].message.content.strip().replace("**", "").replace("__", "")
        except Exception:
            return f"This {product_data.get('name')} is designed for performance and reliability."

    async def extract_search_terms(self, user_query: str) -> str:
        if not self.client: return user_query

        system_core = """
        TASK: Multilingual Semantic Extraction.
        GOAL: Isolate the PHYSICAL OBJECT NOUN from user noise, translate concept to English for search matching if needed, OR keep as native if it's a proper noun.
        
        RULES:
        1. STRIP: Adjectives, Emotions, Prices.
        2. TRANSLATION LOGIC:
           - If user asks in Arabic "عايز موبايل سامسونج", output "mobile" or "samsung".
           - "حذاء رياضي" -> "shoes"
        3. OUTPUT: Single English lowercase word preferred for Database Indexing.
        """

        try:
            completion = await self._safe_execute(
                self.client.chat.completions.create,
                messages=[
                    {"role": "system", "content": system_core},
                    {"role": "user", "content": user_query}
                ],
                model=self.reflex_model,
                temperature=0.0, 
                max_tokens=20
            )
            clean_term = completion.choices[0].message.content.strip().lower()
            return "".join(ch for ch in clean_term if ch.isalnum() or ch.isspace()).strip()
        except Exception:
            return user_query

    async def filter_and_recommend(
        self, 
        user_query: str, 
        products: List[Dict[str, Any]]
    ) -> Optional[CognitiveResponse]:
        if not self.client or not products: return None

        try:
            context_snapshot = [
                ProductContext(**{k: v for k, v in p.items() if k in ProductContext.model_fields}).model_dump()
                for p in products
            ]
        except Exception: return None

        system_core = f"""
        ROLE: The Grand Curator of 'order with air'.
        INPUT: Query "{user_query}" vs Inventory.

        PROTOCOL:
        1. DETECT LANGUAGE: Identify user's language.
        2. MATCH: Find products matching the nuance.
        3. NARRATE: Generate reasoning/intro in the **USER'S DETECTED LANGUAGE**.
        
        OUTPUT JSON FORMAT:
        {{
            "selected_ids": [int, int],
            "reasoning": {{ "id": "Reasoning in User's Language." }},
            "intro_message": "Opening hook in User's Language.",
            "confidence_score": 0.95
        }}
        """

        try:
            completion = await self._safe_execute(
                self.client.chat.completions.create,
                messages=[
                    {"role": "system", "content": system_core},
                    {"role": "user", "content": json.dumps(context_snapshot)}
                ],
                model=self.brain_model,
                temperature=0.25,
                max_tokens=700,
                response_format={"type": "json_object"}
            )
            
            response_data = json.loads(completion.choices[0].message.content)
            
            if response_data.get("confidence_score", 0) < 0.6:
                return None
                
            return CognitiveResponse(**response_data)

        except Exception:
            return None
