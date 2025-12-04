# apps/api/app/services/free_llm_service.py

import json
import logging
import os
import asyncio
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from groq import AsyncGroq
from duckduckgo_search import DDGS

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

    # --- 🌍 EXTERNAL RESEARCH ENGINE (SMART QUERY) ---
    async def _perform_web_search(self, query: str) -> str:
        """
        Executes a live web search. 
        Auto-cleans the query to ensure best results.
        """
        try:
            # 1. Clean the query (Remove "what is", "tell me", etc)
            clean_query = re.sub(r'(what is|tell me about|describe|show me|find|search for)', '', query, flags=re.IGNORECASE).strip()
            
            # 2. Append strategic keywords if missing
            if "specs" not in clean_query and "review" not in clean_query:
                clean_query += " specs rumors news"
                
            logger.info(f"🌍 Deep Research Query: '{clean_query}'")
            
            loop = asyncio.get_running_loop()
            results = await loop.run_in_executor(None, lambda: DDGS().text(clean_query, max_results=4))
            
            if not results: 
                # Retry with simpler query
                logger.warning("⚠️ Zero results. Retrying with simpler query...")
                simple_query = clean_query.split()[0] + " " + clean_query.split()[1] # First 2 words
                results = await loop.run_in_executor(None, lambda: DDGS().text(simple_query, max_results=3))

            if not results:
                return "No external data found."
            
            summary = "\n".join([f"Source: {r['title']} - {r['body']}" for r in results])
            
            # 🔥 Log the success to the terminal so the user SEES it working
            logger.info(f"✅ Research Success! Found {len(results)} sources.")
            return summary

        except Exception as e:
            logger.warning(f"⚠️ Research failed: {e}")
            return "External research unavailable."

    # --- 🧠 HYBRID CONSULTANT (UNLEASHED) ---
    async def consult_on_product(self, product_data: Dict[str, Any], user_question: str) -> str:
        if not self.client:
            return f"The {product_data.get('name')} is a premium selection."

        internal_context = json.dumps(product_data, default=str)
        
        # Determine Search Strategy
        # If user names a specific product (e.g. iPhone 17), use that as the search anchor.
        # Otherwise use the DB product name.
        search_target = user_question
        if product_data.get('name') and product_data.get('name').lower() in user_question.lower():
             search_target = user_question # Use full question if it contains product name
        elif product_data.get('name'):
             search_target = f"{product_data.get('name')} {user_question}"

        external_knowledge = await self._perform_web_search(search_target)

        # 🔥 THE AGGRESSIVE PROMPT 🔥
        system_core = f"""
        You are the Chief Tech Analyst for 'Order With Air'.
        
        --- INPUT DATA ---
        1. [INTERNAL DB] (Might be outdated/irrelevant): {internal_context}
        2. [WEB SEARCH] (Fresh Data): {external_knowledge}

        --- YOUR ORDERS ---
        1. **IGNORE INTERNAL DB** if the user asks about a product (e.g. iPhone 17) that is NOT in the Internal DB.
        2. **USE WEB SEARCH** as your primary source of truth for new tech.
        3. **FALLBACK MODE (CRITICAL):** If Web Search is empty or fails, **USE YOUR OWN TRAINING DATA** to discuss rumors, expectations, or leaks about this product. 
        4. **NEVER SAY "I cannot provide".** Always give the best available info, even if it's based on "expected" specs or rumors.
        5. **FORMAT:** Direct answer. Professional tone. No fluff. Respond in the USER'S LANGUAGE.
        """

        try:
            completion = await self._safe_execute(
                self.client.chat.completions.create,
                messages=[
                    {"role": "system", "content": system_core},
                    {"role": "user", "content": user_question}
                ],
                model=self.brain_model,
                temperature=0.4, # Slightly higher temp to allow "knowledge retrieval" from model memory
                max_tokens=600
            )
            return completion.choices[0].message.content.strip()
        except Exception:
            return "Based on industry trends, this device is expected to feature top-tier specs, though my live feed is currently interrupted."

    # --- STRATEGY & FILTERING (UNCHANGED) ---
    async def strategize_search(self, user_query: str) -> SearchStrategy:
        if not self.client:
            return SearchStrategy(is_direct_product_request=True, search_queries=[user_query], response_tone="Standard", direct_answer_prefix="Found these:")

        system_core = """
        ROLE: Search Strategist. INPUT: User query. OUTPUT: JSON only.
        TASK: Extract search terms. JSON SCHEMA:
        {
            "is_direct_product_request": bool, "search_queries": [str], "price_min": float/null,
            "price_max": float/null, "category_filter": str/null, "attributes": [str],
            "response_tone": str, "direct_answer_prefix": str
        }
        """
        try:
            completion = await self._safe_execute(
                self.client.chat.completions.create,
                messages=[{"role": "system", "content": system_core}, {"role": "user", "content": user_query}],
                model=self.brain_model, temperature=0.1, response_format={"type": "json_object"}
            )
            data = json.loads(self._clean_json_response(completion.choices[0].message.content))
            return SearchStrategy(**data)
        except:
            return SearchStrategy(is_direct_product_request=True, search_queries=[user_query], response_tone="Standard", direct_answer_prefix="Here are the results:")

    async def extract_search_terms(self, user_query: str) -> str:
        if not self.client: return user_query
        try:
            completion = await self._safe_execute(
                self.client.chat.completions.create,
                messages=[{"role": "system", "content": "Extract core noun."}, {"role": "user", "content": user_query}],
                model=self.reflex_model, temperature=0.0, max_tokens=20
            )
            return completion.choices[0].message.content.strip().lower()
        except: return user_query

    async def filter_and_recommend(self, user_query: str, products: List[Dict[str, Any]], tone_instruction: str = "Professional") -> Optional[CognitiveResponse]:
        if not self.client or not products: return None
        try:
            context = [{k: v for k, v in p.items() if k in ['id', 'name', 'price', 'category']} for p in products]
            system_core = f"Select top matches. Tone: {tone_instruction}. Output JSON: {{'selected_ids': [], 'reasoning': {{}}, 'intro_message': '', 'confidence_score': 0.0}}"
            completion = await self._safe_execute(
                self.client.chat.completions.create,
                messages=[{"role": "system", "content": system_core}, {"role": "user", "content": json.dumps(context)}],
                model=self.brain_model, temperature=0.2, response_format={"type": "json_object"}
            )
            data = json.loads(self._clean_json_response(completion.choices[0].message.content))
            if "reasoning" in data: data["reasoning"] = {str(k): v for k, v in data["reasoning"].items()}
            return CognitiveResponse(**data)
        except: return None
