# apps/api/app/services/free_llm_service.py

from datetime import datetime
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
        self.vision_model = "llama-3.2-90b-vision-preview"

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

    async def extract_memory_worthy_facts(self, user_message: str) -> Optional[str]:
        """
        Silent Observer: Checks if the user stated a permanent preference or fact.
        Returns the fact string or None.
        """
        if not self.client or len(user_message.split()) < 3: return None

        system_prompt = """
        TASK: Analyze user input. Extract PERMANENT preferences/facts (Diet, Size, Brand Loyalty, Allergies, Location context).
        OUTPUT: The fact as a concise statement (e.g., "User is vegan", "User wears size 42").
        IF NO FACT: Return "NULL".
        """

        try:
            # We use the smaller/faster model (Reflex Model) for this to save latency
            completion = await self._safe_execute(
                self.client.chat.completions.create,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                model=self.reflex_model,
                temperature=0.0,
                max_tokens=50
            )
            result = completion.choices[0].message.content.strip()
            return None if "NULL" in result else result
        except:
            return None

    async def analyze_visual_context(self, base64_image: str, user_prompt: str = "Describe this product for a shopping search.") -> str:
        """
        Multimodal Uplink: Converts raw pixel data into semantic search vectors.
        Uses Llama-3.2-Vision (or equivalent) to 'see' the product.
        """
        if not self.client:
            return "Visual core offline."

        # Vision-optimized model
        vision_model = "llama-3.2-11b-vision-preview"

        try:
            completion = await self._safe_execute(
                self.client.chat.completions.create,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                model=vision_model,
                temperature=0.1,
                max_tokens=300
            )
            description = completion.choices[0].message.content.strip()
            logger.info(f"👁️ Visual Analysis Complete: {description[:50]}...")
            return description
        except Exception as e:
            logger.error(f"Visual Cortex Failure: {e}")
            return "Unable to analyze image due to signal interference."

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

    async def analyze_product_image(self, base64_image: str) -> str:
        """
        Uses a Multimodal LLM to translate an image into optimal search queries.
        """
        if not self.client or not base64_image: return "generic product"

        system_prompt = """
        ROLE: Senior Global Multi-Vertical Visual Merchant (Fashion, Beauty, Tech, Home).
        TASK: Analyze the image to extract the precise commercial DNA of the DOMINANT product for a high-end search engine.

        --- 🧠 DYNAMIC ANALYSIS PROTOCOLS (AUTO-SWITCHING) ---

        [MODE A: FASHION & APPAREL]
        IF the image contains clothing/shoes/bags:
        1. IDENTITY: Brand + Item Name + Gender (Men/Women/Unisex).
        2. VISUAL DNA: Identify Fabric (e.g., Silk, Denim, Leather), Pattern (e.g., Floral, Striped), and Fit (e.g., Oversized, Slim).
        3. ACCESSORY CHECK: If focusing on a Belt/Scarf/Jewelry worn by a model, output the ACCESSORY, not the outfit.
        -> Example: "Zara Women Maxi Dress Floral Silk Green" OR "Gucci Leather Belt Black Gold Buckle"

        [MODE B: BEAUTY & MAKEUP]
        IF the image contains cosmetics/skincare:
        1. IDENTITY: Brand + Product Line + Item Type (Lipstick, Serum, Palette).
        2. NUANCE: Identify Shade (e.g., Ruby Woo, Nude), Finish (Matte, Glossy, Satin), or Skin Concern (Anti-aging, Hydrating).
        3. PACKAGING vs PRODUCT: Distinguish between the Box (Packaging) and the Bottle/Tube.
        -> Example: "Fenty Beauty Gloss Bomb Universal Lip Luminizer Fenty Glow" OR "The Ordinary Niacinamide 10% + Zinc 1% Serum"

        [MODE C: ELECTRONICS & TECH]
        IF the image contains gadgets/appliances:
        1. IDENTITY: Brand + Model Number/Series + Core Device Name.
        2. SPECS: Capture visible specs (Storage, Size, 5G, 4K) and Color/Finish (Space Grey, Silver).
        3. PART vs WHOLE: Distinguish "Phone Case" from "Phone", "Strap" from "Watch".
        -> Example: "Apple MacBook Pro 14 M3 Chip Space Black" OR "Samsung Galaxy S24 Ultra Titanium Yellow"

        [MODE D: HOME & LIFESTYLE]
        IF the image contains furniture/decor/tools:
        1. IDENTITY: Style (Modern, Rustic, Industrial) + Item Name + Material.
        -> Example: "IKEA Strandmon Wing Chair Nordvalla Dark Grey"

        --- 🛡️ UNIVERSAL RULES (ALWAYS ACTIVE) ---
        1. EXACT MATCH PRIORITY: If text/logo is visible, it overrides visual guessing.
        2. NO FILLER: Output strict keywords only. No "I think...", "It looks like...".
        3. FORMAT: "{Brand} {Sub-Brand/Model} {Key Attribute/Color} {Category}"
        """

        try:
            logger.info("👁️ Sending image to Vision Model for analysis...")
            completion = await self._safe_execute(
                self.client.chat.completions.create,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Analyze this product for search."},
                            {
                                "type": "image_url",
                                # Assumes JPEG for standard API compatibility, Groq handles base64 directly
                                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                            }
                        ]
                    }
                ],
                model=self.vision_model,
                temperature=0.0, # Low temperature for factual accuracy
                max_tokens=100
            )
            search_terms = completion.choices[0].message.content.strip()
            logger.info(f"👁️ Vision Analysis Result: '{search_terms}'")
            return search_terms
        except Exception as e:
            logger.error(f"❌ Vision analysis failed: {e}")
            return "generic product"


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
            return f"The {product_data.get('name')} is a premium selection with excellent specifications."

        internal_context = json.dumps(product_data, default=str)
        
        # Determine Search Strategy
        # If user names a specific product (e.g. iPhone 17), use that as the search anchor.
        # Otherwise use the DB product name.
        search_target = f"{product_data.get('name')} {user_question}"
        external_knowledge = await self._perform_web_search(search_target)

        if product_data.get('name') and product_data.get('name').lower() in user_question.lower():
             search_target = user_question # Use full question if it contains product name
        elif product_data.get('name'):
             search_target = f"{product_data.get('name')} {user_question}"

        current_date = datetime.now().strftime("%B %Y")

        # 🔥 THE AGGRESSIVE PROMPT 🔥
        system_core = f"""
        You are the Senior Chief Tech Analyst for 'order with air'.
        
        --- INPUT DATA ---
        1. [INTERNAL DB]: {internal_context}
        2. [WEB SEARCH]: {external_knowledge}

        --- 🛡️ INTELLIGENCE PROTOCOLS ---
        1. **HYBRID KNOWLEDGE**: If [WEB SEARCH] is empty or fails, YOU MUST USE YOUR OWN INTERNAL TRAINING DATA to provide detailed specs for this product. Do NOT say "I don't know".
        2. **ANTI-ROBOT FILTER**: NEVER output technical database fields like 'ID', 'slug', 'image_url', 'inventory', 'created_at', or 'category_id'. These are forbidden.
        3. **VALUE ADD**: Only show specs that matter to a human buyer (Battery, Screen, Material, Chipset, Scent notes, Fabric).

        --- STRICT OUTPUT RULES (ZERO MARKDOWN) ---
        1. **NO MARKDOWN SYMBOLS**: Do NOT use asterisks (**), hashes (#), underscores (_), or quotes ('') for formatting.
        2. **CLEAN LIST STYLE**: Use a real bullet point (•) for specifications.
        3. **VISUAL HIERARCHY**: Since you cannot use bold, use CAPITAL LETTERS for the feature name to make it stand out.
           - Example:
             • BATTERY: Up to 18 hours
             • PROCESSOR: Apple S8 chip
        4. **LAYOUT**: 
           - Start with a polite, direct answer sentence.
           - Leave one empty line.
           - List the specs/features.
        5. **NO EMOJIS**: Keep it strictly professional and clean.
        6. **LANGUAGE**: Respond in the USER'S LANGUAGE.

        Your goal is to provide a response that looks like a perfectly formatted official document without using any code symbols.
        """

        try:
            completion = await self._safe_execute(
                self.client.chat.completions.create,
                messages=[
                    {"role": "system", "content": system_core},
                    {"role": "user", "content": user_question}
                ],
                model=self.brain_model,
                temperature=0.3, # Slightly higher temp to allow "knowledge retrieval" from model memory
                max_tokens=500
            )
            return completion.choices[0].message.content.strip()
        except Exception:
            return "Based on industry trends, this device is expected to feature top-tier specs, though my live feed is currently interrupted."

    # --- STRATEGY & FILTERING (UNCHANGED) ---
    async def strategize_search(self, user_query: str) -> SearchStrategy:
        if not self.client:
            return SearchStrategy(is_direct_product_request=True, search_queries=[user_query], response_tone="Standard", direct_answer_prefix="Found these:")

        system_core = """
        ROLE: Search Strategist. 
        TASK: Analyze the user's intent and extract search parameters.
        
        CRITICAL: Identify the 'category_filter' precisely.
        - If user says "Tablet", category_filter is "Electronics" or "Tablet".
        - If user says "Lipstick", category_filter is "Beauty".
        
        JSON SCHEMA:
        {
            "is_direct_product_request": bool, 
            "search_queries": [str], 
            "price_min": float/null,
            "price_max": float/null, 
            "category_filter": str/null, 
            "attributes": [str],
            "response_tone": str, 
            "direct_answer_prefix": str
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
