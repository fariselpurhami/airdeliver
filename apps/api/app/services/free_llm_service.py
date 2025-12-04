# apps/api/app/services/free_llm_service.py

import json
import logging
import os
import asyncio
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from groq import AsyncGroq
from duckduckgo_search import DDGS  # 🛠️ New Research Tool Integration

logger = logging.getLogger("airdeliver.services.cognitive_core")

class SearchStrategy(BaseModel):
    is_direct_product_request: bool
    search_queries: List[str]
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    category_filter: Optional[str] = None
    attributes: List[str] = []
    response_tone: str
    direct_answer_prefix: str

class CognitiveResponse(BaseModel):
    selected_ids: List[int]
    reasoning: Dict[str, str]
    intro_message: str
    confidence_score: float

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
                await asyncio.sleep(0.3 * (2 ** i))

    def _clean_json_response(self, content: str) -> str:
        content = content.strip()
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        return json_match.group(0) if json_match else content

    # --- 🌍 EXTERNAL RESEARCH ENGINE (The New Power) ---
    async def _perform_web_search(self, query: str) -> str:
        """
        Executes a live web search to find missing specs using DuckDuckGo.
        Runs in a separate thread to ensure non-blocking async execution.
        """
        try:
            logger.info(f"🌍 Initiating Deep Research for: {query}")
            loop = asyncio.get_running_loop()
            # DuckDuckGo is blocking, so we offload it to an executor
            results = await loop.run_in_executor(None, lambda: DDGS().text(query, max_results=3))
            
            if not results: return "No external data found."
            
            summary = "\n".join([f"- {r['title']}: {r['body']}" for r in results])
            return summary
        except Exception as e:
            logger.warning(f"⚠️ Research failed: {e}")
            return "External research unavailable."

    # --- 🧠 HYBRID CONSULTANT (Updated Logic) ---
    async def consult_on_product(self, product_data: Dict[str, Any], user_question: str) -> str:
        """
        Answers product questions using a Hybrid RAG approach:
        1. Internal DB Data (Primary).
        2. External Web Search (Secondary - if needed).
        """
        if not self.client:
            return f"The {product_data.get('name')} is a premium selection from our {product_data.get('category')} collection."

        # 1. Analyze Context & Need for Research
        internal_context = json.dumps(product_data, default=str)
        
        # Heuristic: If description is short OR question asks for complex details, trigger search
        needs_research = len(str(product_data.get('description', ''))) < 50 or \
                         any(x in user_question.lower() for x in ['review', 'vs', 'compare', 'ingredients', 'specs', 'battery', 'released', 'warranty'])

        external_knowledge = ""
        if needs_research:
            # Smart Query Generation
            search_query = f"{product_data.get('name')} {product_data.get('category')} specs details reviews"
            external_knowledge = await self._perform_web_search(search_query)

        # 2. The Grand Synthesis Prompt
        system_core = f"""
        IDENTITY: 'order with air' Chief Product Expert.
        MISSION: Provide an authoritative, factual answer to the user's question about the product.

        --- DATA SOURCES ---
        [INTERNAL DATABASE]: {internal_context}
        [EXTERNAL WEB RESEARCH]: {external_knowledge}

        --- PROTOCOL ---
        1. PRIORITY: Rely on Internal Database first.
        2. AUGMENT: Use External Research to fill missing technical specs or reviews.
        3. FACTUALITY: Do NOT hallucinate. If specs are missing in both, admit it gracefully.
        4. TONE: Professional, concise, and helpful. 
        5. LANGUAGE: Respond in the EXACT language/dialect of the User Question.

        Output only the answer. Max 3 sentences.
        """

        try:
            completion = await self._safe_execute(
                self.client.chat.completions.create,
                messages=[
                    {"role": "system", "content": system_core},
                    {"role": "user", "content": user_question}
                ],
                model=self.brain_model,
                temperature=0.3, # Low temperature for factual accuracy
                max_tokens=400
            )
            return completion.choices[0].message.content.strip()
        except Exception:
            return f"This {product_data.get('name')} is highly rated. Please check the product details for more info."

    # --- ORIGINAL METHODS (PRESERVED) ---

    async def strategize_search(self, user_query: str) -> SearchStrategy:
        if not self.client:
            return SearchStrategy(
                is_direct_product_request=True, 
                search_queries=[user_query], 
                response_tone="Standard", 
                direct_answer_prefix="Here is what I found:"
            )

        system_core = """
        ROLE: Elite Commerce Intelligence Architect for 'order with air'.
        MISSION: Decode user intent with forensic precision into a structured search strategy.
        
        INPUT: User natural language query (any language).
        OUTPUT: JSON Object ONLY.

        LOGIC GATES:
        1. DETECT INTENT: Is it a specific item ("Red Nike Shoes") or a vibe ("Gift for girlfriend")?
        2. EXTRACT CONSTRAINTS: 
           - Price ranges (e.g., "under $1000" -> price_max: 1000).
           - Sizes, Colors, Attributes (e.g., "dry hair" -> attribute: "moisturizing").
        3. GENERATE QUERIES: Convert "gift for girlfriend" into tangible search terms like ["perfume", "handbag", "jewelry"].
        4. TONE SETTING: 
           - "Birthday/Gift" -> "Celebratory & Helpful"
           - "Specs/Tech" -> "Technical & Precise"
           - "Problem/Solution" (e.g. dry hair) -> "Empathetic Expert"
        5. LANGUAGE: The 'direct_answer_prefix' MUST be in the User's Language.

        JSON STRUCTURE:
        {
            "is_direct_product_request": boolean,
            "search_queries": [string, string],
            "price_min": float or null,
            "price_max": float or null,
            "category_filter": string or null,
            "attributes": [string],
            "response_tone": string,
            "direct_answer_prefix": string (In User Language)
        }
        """

        try:
            completion = await self._safe_execute(
                self.client.chat.completions.create,
                messages=[
                    {"role": "system", "content": system_core},
                    {"role": "user", "content": user_query}
                ],
                model=self.brain_model,
                temperature=0.1,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            raw_content = completion.choices[0].message.content
            data = json.loads(self._clean_json_response(raw_content))
            return SearchStrategy(**data)

        except Exception as e:
            logger.error(f"Strategy Generation Failed: {e}")
            return SearchStrategy(
                is_direct_product_request=True, 
                search_queries=[user_query], 
                response_tone="Fallback", 
                direct_answer_prefix="Found these matches:"
            )

    async def extract_search_terms(self, user_query: str) -> str:
        # Kept for legacy fallback, but strategize_search is now primary
        if not self.client: return user_query
        try:
            completion = await self._safe_execute(
                self.client.chat.completions.create,
                messages=[
                    {"role": "system", "content": "Extract core product noun only. English output. No chat."},
                    {"role": "user", "content": user_query}
                ],
                model=self.reflex_model,
                temperature=0.0,
                max_tokens=20
            )
            return completion.choices[0].message.content.strip().lower()
        except Exception:
            return user_query

    async def filter_and_recommend(
        self, 
        user_query: str, 
        products: List[Dict[str, Any]],
        tone_instruction: str = "Professional"
    ) -> Optional[CognitiveResponse]:
        if not self.client or not products: return None

        try:
            context_snapshot = [
                {k: v for k, v in p.items() if k in ['id', 'name', 'price', 'category', 'description', 'rating']}
                for p in products
            ]
        except Exception: return None

        system_core = f"""
        ROLE: 'order with air' Chief Curator.
        CONTEXT: User asked "{user_query}".
        TONE DIRECTIVE: {tone_instruction}.
        
        TASK:
        1. Select the top 3-5 absolute best matches from the list.
        2. If User asked for "Black Pants", exclude anything not black/pants.
        3. If User asked "Under $1000", exclude anything over $1000.
        4. LANGUAGE: Output MUST be in the User's Language.
        
        OUTPUT JSON:
        {{
            "selected_ids": [int],
            "reasoning": {{ "product_id_str": "Short punchy reason matching tone." }},
            "intro_message": "A personalized opening hook (max 15 words).",
            "confidence_score": 0.0 to 1.0
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
                temperature=0.2,
                max_tokens=800,
                response_format={"type": "json_object"}
            )
            
            response_data = json.loads(self._clean_json_response(completion.choices[0].message.content))
            if response_data.get("confidence_score", 0) < 0.5: return None
            
            # Sanitize ID keys
            reasoning = {str(k): v for k, v in response_data.get("reasoning", {}).items()}
            response_data["reasoning"] = reasoning
            
            return CognitiveResponse(**response_data)

        except Exception as e:
            logger.error(f"Filtering Failed: {e}")
            return None
