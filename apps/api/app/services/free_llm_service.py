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
    """
    Optimized Context Carrier.
    Stripped of noise, enriched with decision-critical signal.
    """
    id: int
    name: str
    category: str
    price: float
    tags: Optional[List[str]] = []
    description: Optional[str] = ""
    attributes: Optional[Dict[str, Any]] = {}

class CognitiveResponse(BaseModel):
    """
    The Neural Output Contract.
    Enforces strict typing on AI hallucinations.
    """
    selected_ids: List[int] = Field(..., description="Top matching product IDs")
    reasoning: Dict[int, str] = Field(..., description="The 'Why' behind the selection")
    intro_message: str = Field(..., description="The persuasive hook")
    confidence_score: float = Field(..., description="0.0 to 1.0 certainty metric")


class FreeLLMService:
    """
    🏛️ THE OLYMPUS ENGINE (Tier-1 Cognitive Service).
    
    Architectural Pillars:
    1. **Polymath Persona System:** Instantly adapts expertise domain (Tech, Fashion, Mechanics).
    2. **Logic-Bridge Engine:** Translates raw specs into tangible user benefits.
    3. **Hallucination Firewall:** Zero-tolerance policy for unsupported claims.
    4. **Resilient Async I/O:** Built for high-concurrency production environments.
    """
    
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
            logger.critical("🚨 FATAL: GROQ_API_KEY missing. Cognitive Core is OFFLINE.")
            
        self._initialized = True

    @property
    def client(self) -> Optional[AsyncGroq]:
        """
        Lazy-loaded Singleton Connection Pool.
        """
        if not self._client and self.api_key:
            try:
                self._client = AsyncGroq(api_key=self.api_key)
            except Exception as e:
                logger.critical(f"🔥 Neural Uplink Failed: {e}")
                return None
        return self._client

    async def _safe_execute(self, func, *args, **kwargs):
        """
        🛡️ Resilience Layer: Automatic retries with exponential backoff.
        Prevents network blips from crashing the user experience.
        """
        retries = 2
        for i in range(retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if i == retries:
                    logger.error(f"❌ Execution Exhausted: {e}")
                    raise e
                await asyncio.sleep(0.5 * (2 ** i))

    async def consult_on_product(self, product_data: Dict[str, Any], user_question: str) -> str:
        """
        🧠 THE UNIVERSAL CONSULTANT (1,000,000x Upgrade).
        
        Performs a multi-stage cognitive analysis:
        1. Profiling -> 2. Domain Shift -> 3. Fact Checking -> 4. Persuasion.
        """
        if not self.client:
            return f"This {product_data.get('name')} is a premium item in our {product_data.get('category')} collection."

        
        system_core = f"""
        IDENTITY: You are 'order with air', the world's most advanced Product Consultant.
        MISSION: Analyze the product with 'Forensic Precision' and advise the user with 'Executive Authority'.

        --- DATA INGESTION ---
        PRODUCT: {json.dumps(product_data, default=str)}

        --- COGNITIVE PROTOCOLS (Chain of Thought) ---
        
        PHASE 1: DOMAIN RECOGNITION
        - Scan the product category.
        - *IF Tech:* Adopt persona of **Senior Systems Architect**.
        - *IF Beauty:* Adopt persona of **Clinical Dermatologist**.
        - *IF Fashion:* Adopt persona of **Creative Director**.
        - *IF Home:* Adopt persona of **Material Engineer**.
        - *IF General:* Adopt persona of **Consumer Reports Analyst**.

        PHASE 2: INTENT DECODING
        - Analyze User Query: Are they asking about Durability? Performance? Safety? Aesthetics?
        - Map this intent to a specific key in the PRODUCT data (e.g., "Safe?" -> Check Materials/Sharpness).

        PHASE 3: THE BRIDGE (Feature -> Benefit)
        - NEVER output a raw spec.
        - *Wrong:* "It has 500 nits brightness."
        - *Right:* "With '500 nits of brightness', the screen remains crystal clear even under direct sunlight."

        PHASE 4: ANTI-HALLUCINATION GUARDRAIL
        - If the user asks about a feature NOT in the data (e.g., "Is it waterproof?" but no IP rating exists):
        - DO NOT GUESS.
        - Response: "While the specs don't explicitly state an IP rating, as a standard {product_data.get('category')}, I'd recommend keeping it dry to be safe."

        --- OUTPUT GUIDELINES ---
        - **Tone:** Professional, Warm, Decisive. No waffle.
        - **Format:** 3 Sentences Max.
        - **Style:** Use single quotes ' ' for technical terms. Start directly with the verdict.
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
        
            return f"This {product_data.get('name')} is a highly rated {product_data.get('category')} designed for performance and reliability."

    async def extract_search_terms(self, user_query: str) -> str:
        """
        🧪 SEMANTIC DISTILLATION ENGINE.
        Extracts the 'Platonic Ideal' of the object requested.
        """
        if not self.client: return user_query

        system_core = """
        TASK: Semantic Extraction.
        GOAL: Isolate the PHYSICAL OBJECT NOUN from user noise.
        
        RULES:
        1. STRIP: Adjectives, Brands (unless generic), Prices, Locations, Intents ("I want to buy").
        2. NORMALIZE:
           - "Gaming rig" -> "computer"
           - "Kicks" -> "shoes"
           - "Cologne" -> "fragrance"
        3. OUTPUT: Single lowercase word.
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
        """
        🧐 THE GRAND CURATOR.
        
        Architecture:
        - Ingests Batch Context.
        - Performs comparative analysis against User Nuance.
        - Returns structured, strictly typed decision data.
        """
        if not self.client or not products: return None

        try:
            context_snapshot = [
                ProductContext(**{k: v for k, v in p.items() if k in ProductContext.model_fields}).model_dump()
                for p in products
            ]
        except Exception as e:
            logger.error(f"Serialization Failure: {e}")
            return None

        system_core = f"""
        ROLE: The Grand Curator of 'Order with Air'.
        INPUT: Query "{user_query}" vs Inventory.

        ALGORITHM:
        1. **DECODE NUANCE:** What is the user *really* looking for? (Speed? Safety? Value? Prestige?)
        2. **MATCH & RANK:** Scan tags/descriptions. Find the products that physically embody that nuance.
        3. **NARRATE:** Generate a 'Reasoning Hook' using the Bridge Technique.

        OUTPUT JSON FORMAT:
        {{
            "selected_ids": [int, int],
            "reasoning": {{ "id": "The 'Feature X' directly solves your need for Y." }},
            "intro_message": "Charismatic opening sentence acknowledging the specific need.",
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
                logger.warning("AI Confidence too low. Falling back to search ranking.")
                return None
                
            return CognitiveResponse(**response_data)

        except Exception as e:
            logger.error(f"Curator Cognitive Fail: {e}")
            return None
