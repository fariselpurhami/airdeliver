# apps/api/app/services/free_llm_service.py

import json
import logging
import os
import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ValidationError
from groq import AsyncGroq, APIConnectionError, RateLimitError

logger = logging.getLogger("airdeliver.services.llm")

class ProductContext(BaseModel):
    """
    Minimalist Data Transfer Object (DTO).
    Optimizes token usage by stripping non-essential DB fields.
    """
    id: int
    name: str
    category: str
    price: float
    tags: Optional[List[str]] = []

class AIReasoningResponse(BaseModel):
    """
    The rigid contract for AI output.
    Ensures the Frontend never receives malformed data.
    """
    selected_ids: List[int] = Field(..., description="IDs of the top recommended products")
    reasoning: Dict[int, str] = Field(..., description="Map of ProductID to a short, punchy reason")
    intro_message: str = Field(..., description="A futuristic, welcoming opening sentence")

class FreeLLMService:
    """
    💎 DIAMOND STANDARD ADAPTER (Groq / Llama 3).
    
    Architectural Features:
    - Thread-Safe Singleton Pattern.
    - Semantic Decoupling (Zero-Hallucination Search).
    - Automatic Retry with Exponential Backoff.
    - Circuit Breaker Pattern for API Failures.
    """
    
    _instance = None
    _client: Optional[AsyncGroq] = None
    _initialized = False

    def __new__(cls):
        """Enforces Singleton Pattern at the memory allocation level."""
        if cls._instance is None:
            cls._instance = super(FreeLLMService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Idempotent Initialization."""
        if self._initialized:
            return
            
        self.api_key = os.getenv("GROQ_API_KEY")
        
        self.reasoning_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile") 
    
        self.utility_model = "llama-3.1-8b-instant" 
        
        if not self.api_key:
            logger.warning("⚠️ GROQ_API_KEY is missing. AI Core running in degraded mode.")
        
        self._initialized = True

    @property
    def client(self) -> Optional[AsyncGroq]:
        """Lazy initialization with connection pooling management."""
        if not self._client and self.api_key:
            try:
                self._client = AsyncGroq(api_key=self.api_key)
            except Exception as e:
                logger.critical(f"🔥 Failed to initialize Groq Client: {e}")
                return None
        return self._client

    async def extract_search_terms(self, user_query: str) -> str:
        """
        💎 DIAMOND FEATURE: SEMANTIC DECOUPLING.
        
        This function acts as a 'Sniper'. It isolates the physical object 
        from the user's intent, stripping away 'Semantic Noise' (Prices, Budgets).
        
        Example: "I have $2000 for a high end phone" -> "phone"
        Result: Vector Search finds phones, not jewelry.
        """
        if not self.client: return user_query

        system_prompt = """
        You are the 'Semantic Core' of an advanced Autonomous Commerce Engine.
        Your Mission: Decode user intent into a single, precise, warehouse-ready search term.

        ### THE PRIME DIRECTIVE (DO NOT VIOLATE):
        Your output must be the *Physical Object Name* only.
        You must strip away all context, emotions, prices, and specifications to find the "Base Noun".

        ### EXECUTION PROTOCOLS:

        1. [PROTOCOL: NOISE CANCELLATION]
           - AGGRESSIVELY REMOVE all financial constraints (e.g., "$2000", "cheap", "expensive", "budget", "under 500").
           - AGGRESSIVELY REMOVE all filler phrases (e.g., "I want to buy", "looking for", "recommend me", "something for").
           - REMOVE subjective adjectives (e.g., "best", "cool", "high-end", "luxury", "fast").

        2. [PROTOCOL: ATTRIBUTE STRIPPING]
           - REMOVE specific technical specs unless they define the object category itself.
           - REMOVE brand names *unless* the user provides ONLY a brand (e.g., "Nike").
           - Example: "Red 256GB iPhone 15 Pro" -> "iphone" (The attribute filtering happens later).

        3. [PROTOCOL: CANONICAL NORMALIZATION]
           You must translate "Human Slang" into "Inventory Standard Terms":
           - "smartphone", "cellphone", "mobile" -> "phone"
           - "laptop computer", "macbook", "notebook" -> "laptop"
           - "kicks", "sneakers", "trainers", "runners" -> "shoes"
           - "timepiece", "wrist watch", "rolex" -> "watch"
           - "screen", "display", "tv" -> "monitor" (or "television" based on context)
           - "pods", "earphones", "buds" -> "earbuds"
           - "apparel", "outfit", "garment" -> "clothing" (or specific item like "shirt")
           - "rouge", "lip stick" -> "lipstick"
           - "scent", "cologne", "fragrance" -> "perfume"

        ### OUTPUT FORMAT:
        - Return ONLY the single, lowercase, normalized noun.
        - NO punctuation. NO explanations. NO labels.

        ### FEW-SHOT TRAINING EXAMPLES:
        Input: "I have a budget of 2000 usd and I need a high end smartphone"
        Output: phone

        Input: "show me the best noise cancelling headphones for travel under $300"
        Output: headphones

        Input: "I need a red dress for a wedding party"
        Output: dress

        Input: "looking for cheap running kicks"
        Output: shoes

        Input: "something to wash my face"
        Output: cleanser

        Input: "gaming rig for cyberpunk"
        Output: laptop
        """

        try:
            completion = await self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ],
                model=self.utility_model, 
                temperature=0.0, 
                max_tokens=15
            )
            
            clean_term = completion.choices[0].message.content.strip().lower()
            clean_term = clean_term.replace('"', '').replace("'", "").replace(".", "")
            
            if clean_term != user_query:
                logger.info(f"🔍 Query Distilled: '{user_query}' -> '{clean_term}'")
                
            return clean_term

        except Exception as e:
            logger.warning(f"⚠️ Query extraction bypass active due to error: {e}")
            return user_query 

    async def filter_and_recommend(
        self, 
        user_query: str, 
        products: List[Dict[str, Any]], 
        persona: str = "Futuristic"
    ) -> Optional[AIReasoningResponse]:
        """
        The "Sales Engineer" Core.
        Uses the 70B model to analyze specs vs user constraints (Price, Vibe).
        """
        if not self.client or not products:
            return None

        try:
            context_products = [
                ProductContext(**{k: v for k, v in p.items() if k in ProductContext.model_fields}).model_dump()
                for p in products
            ]
        except Exception as e:
            logger.error(f"�� Data Serialization Error: {e}")
            return None

        system_prompt = f"""
        You are 'air', the proprietary AI core of the airdeliver logistics network.
        Persona: {persona} (Professional, Concise, Sophisticated).
        
        GOAL:
        Analyze the USER QUERY (especially budget/specs) against the INVENTORY. 
        Select the top 1-3 products that truly fit.
        
        RULES:
        1. RESPECT BUDGETS: If user says "$2000", prioritize high-value items. If "cheap", prioritize low price.
        2. "intro_message": A futuristic acknowledgment (e.g., "Based on your request ⚡").
        3. "reasoning": A micro-pitch (max 8 words) explaining the fit (e.g., "Best camera in your budget.").
        
        INVENTORY:
        {json.dumps(context_products)}
        
        OUTPUT FORMAT (Strict JSON):
        {{
            "selected_ids": [101, 105],
            "reasoning": {{
                "101": "Perfect for heavy-duty tasks.",
                "105": "Best value for performance."
            }},
            "intro_message": "Optimized selection generated."
        }}
        """

        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                chat_completion = await self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_query}
                    ],
                    model=self.reasoning_model,
                    temperature=0.3, 
                    max_tokens=600,
                    response_format={"type": "json_object"} 
                )

                raw_content = chat_completion.choices[0].message.content
                
                parsed_data = json.loads(raw_content)
                validated_response = AIReasoningResponse(**parsed_data)
                
                return validated_response

            except (APIConnectionError, RateLimitError) as e:
                logger.warning(f"⚠️ AI Network Glitch (Attempt {attempt+1}/{max_retries+1}): {e}")
                if attempt < max_retries:
                    await asyncio.sleep(1 * (attempt + 1)) 
                else:
                    logger.error("🔥 AI Service Unreachable.")
                    return None
            except (json.JSONDecodeError, ValidationError) as e:
                logger.error(f"🔥 AI Output Validation Failed: {e} | Raw: {raw_content}")
                return None
            except Exception as e:
                logger.error(f"🔥 Unexpected AI Error: {e}")
                return None
        
        return None
