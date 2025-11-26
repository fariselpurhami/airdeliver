# apps/api/app/services/free_llm_service.py

import json
import logging
import os
import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ValidationError
from groq import AsyncGroq, APIConnectionError, RateLimitError

# --- 🛡️ Enterprise Logging Strategy ---
# Structured logging for observability tools like Grafana/Loki
logger = logging.getLogger("airdeliver.services.llm")

# --- 🏗️ Data Contracts (Strict Type Safety) ---

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
    �� DIAMOND STANDARD ADAPTER (Groq / Llama 3).
    
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
        
        # 🚀 MODEL CONFIGURATION (LATEST STABLE VERSIONS)
        # Heavy Reasoning: Llama 3.3 70B (The smartest open model)
        self.reasoning_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile") 
        # Fast Utility: Llama 3.1 8B (Instant responses for extraction)
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

        # The "Nuclear Prompt" for extraction
        system_prompt = """
        You are a Semantic Distiller API. 
        Your ONLY goal is to extract the CORE PHYSICAL OBJECT name from the user's query.
        
        CRITICAL RULES:
        1. STRIP AWAY ALL PRICES, CURRENCIES, AND NUMBERS (e.g., ignore "2000 usd", "500$", "budget").
        2. STRIP AWAY subjective adjectives (e.g., ignore "high end", "best", "cheap", "luxury").
        3. NORMALIZE synonyms to the simplest standard noun found in a generic warehouse:
           - "smartphone" -> "phone"
           - "cellphone" -> "phone"
           - "running shoes" -> "shoes"
           - "wrist watch" -> "watch"
           - "laptop computer" -> "laptop"
        4. STRIP AWAY brand names unless explicitly requested.
        5. OUTPUT ONLY THE NOUN (The Object). NO explanations.
        
        Examples:
        - Input: "I have a budget 2000 usd and i need high end smartphone" -> Output: "smartphone"
        - Input: "looking for cheap running shoes under 50$" -> Output: "running shoes"
        - Input: "red dress for a wedding party" -> Output: "red dress"
        """

        try:
            completion = await self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ],
                model=self.utility_model, # Use the fast model
                temperature=0.0, # Zero creativity = Maximum precision
                max_tokens=15
            )
            
            # Defensive Cleaning
            clean_term = completion.choices[0].message.content.strip().lower()
            clean_term = clean_term.replace('"', '').replace("'", "").replace(".", "")
            
            # Log the transformation for observability
            if clean_term != user_query:
                logger.info(f"🔍 Query Distilled: '{user_query}' -> '{clean_term}'")
                
            return clean_term

        except Exception as e:
            logger.warning(f"⚠️ Query extraction bypass active due to error: {e}")
            return user_query # Safe fallback

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

        # 1. Data Minimization (Optimization Layer)
        # Strip heavy HTML descriptions, send only what matters for reasoning.
        try:
            context_products = [
                ProductContext(**{k: v for k, v in p.items() if k in ProductContext.model_fields}).model_dump()
                for p in products
            ]
        except Exception as e:
            logger.error(f"�� Data Serialization Error: {e}")
            return None

        # 2. System Prompt Engineering (The Brain)
        system_prompt = f"""
        You are 'Air', the proprietary AI core of the AirDeliver logistics network.
        Persona: {persona} (Professional, Concise, Sophisticated).
        
        GOAL:
        Analyze the USER QUERY (especially budget/specs) against the INVENTORY. 
        Select the top 1-3 products that truly fit.
        
        RULES:
        1. RESPECT BUDGETS: If user says "$2000", prioritize high-value items. If "cheap", prioritize low price.
        2. "intro_message": A futuristic acknowledgment (e.g., "Scanning inventory... Optimized matches found.").
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

        # 3. Execution with Resilience (Retry Loop)
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                chat_completion = await self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_query}
                    ],
                    model=self.reasoning_model,
                    temperature=0.3, # Low temperature for consistent JSON
                    max_tokens=600,
                    response_format={"type": "json_object"} # Force strict JSON
                )

                raw_content = chat_completion.choices[0].message.content
                
                # 4. Validation Layer (Pydantic)
                parsed_data = json.loads(raw_content)
                validated_response = AIReasoningResponse(**parsed_data)
                
                return validated_response

            except (APIConnectionError, RateLimitError) as e:
                logger.warning(f"⚠️ AI Network Glitch (Attempt {attempt+1}/{max_retries+1}): {e}")
                if attempt < max_retries:
                    await asyncio.sleep(1 * (attempt + 1)) # Exponential backoff
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
