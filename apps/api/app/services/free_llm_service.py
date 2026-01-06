# apps/api/app/services/free_llm_service.py

from datetime import datetime
import json
import logging
import os
import asyncio
import re
import random
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from groq import AsyncGroq
from tavily import TavilyClient

logger = logging.getLogger("airdeliver.services.cognitive_core")

class SearchStrategy(BaseModel):
    """Blueprint for the Search Engine Execution."""
    is_direct_product_request: bool = Field(..., description="True if user wants a specific item, False if browsing")
    search_queries: List[str] = Field(..., description="Optimized queries for hybrid search (Semantic + Keyword)")
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    category_filter: Optional[str] = None
    attributes: List[str] = Field(default_factory=list, description="Extracted attributes like color, size, material")
    response_tone: str = Field(..., description="suggested tone: 'enthusiastic', 'professional', 'minimalist'")
    direct_answer_prefix: str = Field(..., description="A short, human-like opening sentence")

class CognitiveResponse(BaseModel):
    """Structured output for decision making."""
    selected_ids: List[int]
    reasoning: Dict[str, str]
    intro_message: str
    confidence_score: float

class FreeLLMService:
    """
    💎 DIAMOND COGNITIVE CORE (V100.0 - UNIVERSAL MIND).

    The brain behind the operation. Not just an LLM wrapper, but a
    Personality Engine and Intent Decoder.

    ARCHITECTURAL PILLARS:
    1. 🎭 Dynamic Persona Injection: Adapts tone based on user financial DNA.
    2. 🕵️ Sherlock Extraction: Reads between lines to find implicit user facts.
    3. 👁️ Commercial Vision: Analyzes images like a senior merchandiser.
    4. 🛡️ Resilience: Automatic retries and fallback models.
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

        self.brain_model = "openai/gpt-oss-120b"
        
        self.vision_model = "meta-llama/llama-4-maverick-17b-128e-instruct"
    
        self.reflex_model = "openai/gpt-oss-20b"

        self.system_persona = """
        YOU ARE airdeliver AI. A World-Class Shopping Concierge.
        TRAITS: Charismatic, Ultra-Intelligent, Proactive, and Brief.
        GOAL: Help the user buy the PERFECT item in record time.
        TONE: Adaptive. If the user is technical, be precise. If casual, be friendly.
        NEVER start with "As an AI...". Be human-like.
        """

        if not self.api_key:
            logger.critical("⛔ GROQ_API_KEY missing. Cognitive Core is OFFLINE.")

        self._initialized = True

    @property
    def client(self) -> Optional[AsyncGroq]:
        """Lazy-loaded, fault-tolerant connection."""
        if not self._client and self.api_key:
            try:
                self._client = AsyncGroq(api_key=self.api_key)
        
            except Exception as e:
                logger.critical(f"🔥 Neural Uplink Failed: {e}")
                return None
        return self._client

    async def generate_response(
        self,
        prompt: str,
        system_role: str = "You are a helpful AI assistant.",
        context: Any = None,
        temperature: float = 0.7,
        json_mode: bool = False
    ) -> str:
        """
        🚀 Universal Generator:
        - Handles Text/JSON/List contexts automatically.
        - Supports 'JSON Mode' for structured data extraction.
        - Dynamic Creativity Control via 'temperature'.
        """
        try:
            client_instance = self.client
            context_str = ""
            if context:
                if isinstance(context, (dict, list)):
                    import json
                    context_str = json.dumps(context, indent=2, ensure_ascii=False)
                else:
                    context_str = str(context)

            full_system_content = system_role
            if context_str:
                full_system_content += f"\n\n🔍 REFERENCED CONTEXT:\n{context_str}"

            messages = [
                {"role": "system", "content": full_system_content},
                {"role": "user", "content": prompt}
            ]

            kwargs = {
                "messages": messages,
                "model": self.brain_model,  
                "temperature": temperature if temperature is not None else 0.5,
                "max_tokens": 2048,
                "top_p": 0.9,
            }

            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            chat_completion = await client_instance.chat.completions.create(**kwargs)
            return chat_completion.choices[0].message.content
        except Exception as e:
            logger.error(f"🔥 LLM Universal Error: {e}")

            return ""

    def _get_spontaneous_vibe(self) -> str:
        """
        🎲 Random Vibe Selector.
        Picks a unique 'Scene' for the AI to act upon, avoiding robotic welcomes.
        """
        vibes = [
            "User entered. IGNORE 'Hello'. Jump straight into the sleek efficiency of 'Titanium Minimalist Setups'. Be intriguing.",
            "Skip greetings. Act as if you were analyzing 'Quantum Computing' specs and want to share a secret.",
            "New session. Do not welcome. Question if they have seen the latest 'Eco-Luxury' tech. Be provocative.",
            "Connection active. Immediately propose a 'Cyberpunk Aesthetic' upgrade for their daily gear.",
            "Start immediately. Mention that 'Silence is the ultimate luxury' (Noise Cancelling context).",
            "User is online. Ask them: 'Ready to see what the future looks like today?'",
            "Direct approach. Say: 'I found something that matches your high standards.'"
        ]
        return random.choice(vibes)

    async def generate_lifestyle_matrix(self, all_products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        🚀 THE QUAD-CORE WELCOME ENGINE.
        Instead of a single "Hello", we launch a coordinated 4-pronged engagement strategy.
        It turns a bug into a Global Lifestyle Feature.
        
        💎 STRATEGY:
        1. The Trendsetter (Popular Item).
        2. The Deal Hunter (Best Value).
        3. The Connoisseur (High Rating/Price).
        4. The Wildcard (Random Discovery).
        """
        if not self.client or not all_products:
            return [{"text": "Welcome to the future of shopping.", "product": None}]

        try:
        
            trend_pool = all_products[:10]
            trend_item = random.choice(trend_pool) if trend_pool else all_products[0]

            deal_pool = random.sample(all_products, min(len(all_products), 20))
            deal_item = min(deal_pool, key=lambda x: x.get('price', 999999))

            lux_pool = random.sample(all_products, min(len(all_products), 20))
            lux_item = max(lux_pool, key=lambda x: x.get('price', 0))

            wild_item = random.choice(all_products)
            selected_items = [trend_item, deal_item, lux_item, wild_item]
            
            unique_items = []
            seen_ids = set()
            for item in selected_items:
                if item.get('id') not in seen_ids:
                    unique_items.append(item)
                    seen_ids.add(item.get('id'))
                else:
                
                    fallback = random.choice(all_products)
                    unique_items.append(fallback)

            items_context = "\n".join([
                f"1. TREND ({unique_items[0].get('name')}): Enthusiastic vibe.",
                f"2. DEAL ({unique_items[1].get('name')}): Urgent value vibe.",
                f"3. LUXURY ({unique_items[2].get('name')}): Sophisticated vibe.",
                f"4. DISCOVERY ({unique_items[3].get('name')}): Curious vibe."
            ])

            system_prompt = """
            ROLE: Global Lifestyle Curator.
            TASK: Write 4 short, punchy hooks for the provided products.
            
            RULES:
            1. Output MUST be valid JSON list of strings: ["Hook 1", "Hook 2", "Hook 3", "Hook 4"].
            2. NO MARKDOWN. NO EMOJIS (The UI handles emojis).
            3. Length: Max 10 words per hook.
            4. Tone: Match the requested vibe (Trend, Deal, Luxury, Discovery).
            """

            completion = await self._safe_execute(
                self.client.chat.completions.create,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": items_context}
                ],
                model=self.reflex_model, 
                temperature=0.7,
                response_format={"type": "json_object"}
            )

            hooks_json = json.loads(self._clean_json_response(completion.choices[0].message.content))
            hooks_list = hooks_json.get("hooks", list(hooks_json.values())[0]) 

            if not isinstance(hooks_list, list) or len(hooks_list) < 4:
                hooks_list = [
                    f"Check out the {unique_items[0].get('name')}.",
                    f"Great price on {unique_items[1].get('name')}.",
                    f"Experience the {unique_items[2].get('name')}.",
                    f"Have you seen {unique_items[3].get('name')}?"
                ]

            matrix_response = []
            for i in range(min(len(unique_items), 4)):
                matrix_response.append({
                    "text": hooks_list[i],
                    "product": unique_items[i],
                    "type": ["trend", "deal", "luxury", "discovery"][i]
                })

            return matrix_response

        except Exception as e:
            logger.error(f"Lifestyle Matrix Failed: {e}")

            return [{
                "text": "Ready to explore our global collection?", 
                "product": random.choice(all_products) if all_products else None,
                "type": "fallback"
            }]


    async def extract_memory_worthy_facts(self, user_message: str) -> Optional[str]:
        """
        🕵️ The Silent Observer.
        Analyzes user input to extract PERMANENT & IMPLICIT facts.

        Example:
        Input: "I need a cheap phone for my kid."
        Output: "User has a child, prefers budget-friendly electronics."
        """
        if not self.client or len(user_message.split()) < 3: return None

        system_prompt = """
        ROLE: Expert Profiler.
        TASK: Analyze the user's message. Extract PERMANENT preferences, Lifestyle Indicators, or Financial Context.
        OUTPUT: A single, concise 3rd-person fact string.

        RULES:
        - Ignore temporary intent (e.g., "I want a pizza" -> NULL).
        - Capture constraints (Allergies, Sizes, Brand Loyalty, Budget Tier).
        - IF NO VALUABLE FACT FOUND: Return "NULL".

        INPUT EXAMPLES:
        "I only wear Nike." -> "Brand loyalty: Nike."
        "Too expensive for me." -> "Price sensitivity: High."
        "I need this for my wedding." -> "Life Event: Wedding upcoming."
        """

        try:
            completion = await self._safe_execute(
                self.client.chat.completions.create,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                model=self.reflex_model,
                temperature=0.0,
                max_tokens=150
            )
            result = completion.choices[0].message.content.strip()
            return None if "NULL" in result or len(result) < 5 else result
        except Exception:
            return None


    async def analyze_visual_context(self, base64_image: str, user_prompt: str = "") -> str:
        """
        👁️ Multimodal Retina Scan.
        Converts raw pixels into rich Commercial Metadata.
        Acts as a Senior Merchandiser identifying style, material, and occasion.
        """
        if not self.client: return "Visual core offline."

        final_prompt = user_prompt if user_prompt else "Describe this product in detail for a search engine. Focus on: Category, Color, Material, Brand style, and Vibe."

        try:
            completion = await self._safe_execute(
                self.client.chat.completions.create,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": final_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                model=self.vision_model,
                temperature=0.1,
                max_tokens=250 
            )
            description = completion.choices[0].message.content.strip()
            logger.info(f"👁️ Visual Analysis: {description[:60]}...")
            return description
        except Exception as e:
            logger.error(f"🔥 Visual Cortex Failure: {e}")
            return "Visual signal interrupted."

    
    async def _safe_execute(self, func, *args, **kwargs):
        """
        🛡️ Resilience Wrapper.
        Retries with exponential backoff for network blips.
        """
        retries = 2
        for i in range(retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if i == retries:
                    logger.error(f"❌ LLM Execution Exhausted: {e}")
                    raise e
                await asyncio.sleep(0.3 * (2 ** i))

    def _clean_json_response(self, content: str) -> str:
        """🧹 Sanitizes LLM output to ensure valid JSON."""
        content = content.strip()
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        return json_match.group(0) if json_match else "{}"

    async def analyze_product_image(self, base64_image: str, enrich_with_search: bool = True) -> str:
        """
        👁️ OMNI-VISION ANALYZER (V5.0).
        Uses Multimodal LLM to extract 'Commercial DNA' from pixels.
        Includes a 'Flash Search Bridge' to validate visual hallucinations against real market data.
        """

        if not self.client: return "generic product"
        if not base64_image: return "generic product"

        system_prompt = """
ROLE: Silicon-Valley Grade Visual Product Identification & Retrieval Engine (Global, Multi-Vertical, Anti-Hallucination).
MISSION: Given ONE user image, identify the SINGLE DOMINANT purchasable product the user intends to buy, extract its commercial DNA, and output ONE LINE of search keywords that retrieves the exact product (or the tightest safe candidate) in a 100M+ item catalog.

========================
A) HARD OUTPUT CONTRACT
========================
OUTPUT MUST BE:
- Exactly ONE line of search keywords.
- No explanations, no JSON, no bullets, no punctuation-heavy text, no prefix/suffix.
- No uncertainty words (“maybe”, “probably”, “looks like”).
- No marketing fluff (“best”, “premium”, “authentic”, “original”, “new”).
- If not enough evidence for exact model: output a safe high-signal generic query (category + defining attributes) WITHOUT inventing details.

Language:
- Prefer Latin characters for searchability.
- Preserve exact brand/model strings as seen (even if non-Latin). If non-Latin text is clearly visible, include it as-is (do not translate claims).

========================
B) PRIME DIRECTIVE (ANTI-TRAP)
========================
You are not captioning the image.
You are solving the user’s purchase intent: “What is the main sellable product here?”
Never lock onto a prominent sub-part (keyboard, strap, cap, lid, charger, lens, remote, cable) until you verify whether it is an accessory to a larger product.

========================
C) TWO-PASS PERCEPTION (MANDATORY)
========================
PASS 1 — GLOBAL SCAN (WHOLE SCENE):
- Identify up to 5 candidate products present.
- Identify which object is centered / staged / most intentional (hand-held hero shot, retail packaging, isolated placement).
- Detect any visible text/logos/labels anywhere in the scene.

PASS 2 — FORENSIC SCAN (WHOLE OBJECT + ID SIGNALS):
- For each candidate, look for boundaries/silhouette, completeness cues, ports/hinges/closures, packaging/label text, and functional context.

Do NOT decide dominance after PASS 1 alone.

========================
D) DOMINANT PRODUCT SELECTION (DPS) — PICK ONE
========================
1) Enumerate candidates (max 5).
2) Score each candidate with DOMINANCE SCORE (0–2 each):
- Intent Signal: looks like the hero subject / framed as “the product”.
- Completeness Signal: coherent full silhouette (not a fragment).
- Scale Signal: meaningful area & depth prominence (not just a close-up of texture).
- Text/Label Signal: readable brand/model/variant on that candidate or its packaging.
- Functional Context Signal: other objects serve it (cable connected to it, case around it, hand holding it).
- Packaging Signal: retail box/tag/label indicates the sellable unit.
3) ACCESSORY OVERRIDE (BRUTAL RULE):
- If candidate is a part/accessory of another visible candidate (keyboard with laptop, strap with bag, cap with bottle),
  then the accessory CANNOT be dominant unless:
  (a) it is clearly isolated as the subject, OR
  (b) it is the only item in focus with its own retail packaging/label, OR
  (c) the “main device” is clearly background/context only.
4) MULTI-UNIT EDGE CASE:
- If the image is a deliberate bundle (e.g., boxed set) with one shared SKU, treat the bundle as the dominant product.
- Otherwise still pick one dominant product.

Hard rule: Choose exactly ONE dominant product.

========================
E) ID EVIDENCE HIERARCHY (NO HALLUCINATION)
========================
Only output tokens supported by evidence. Evidence priority:
1) Visible printed text / labels / packaging text (OCR-level truth).
2) Logos / distinctive marks (brand inference allowed, model inference NOT allowed unless uniquely identifiable).
3) Structural cues (shape/ports/closures/material).
4) Context cues (usage environment), ONLY as weak hints—never for model numbers.

Forbidden guesses (never invent):
- Exact model number, generation/year, chip/CPU, RAM/storage, material blend %, limited editions, compatibility lists, medical claims, certifications, “Pro/Max/Ultra” unless printed or unmistakably labeled.
- EXACT ALPHANUMERIC MODEL CODES (e.g., "MXE13LLA", "A2442", "SM-S918B") unless you distinctly OCR them from a label in the image.
 - Exact screen size (14" vs 16" vs 17") unless strictly inferred from visual comparison (e.g., keyboard-to-chassis ratio).
If evidence is insufficient, degrade gracefully:
Brand (if known) + generic product noun + 3–6 defining visible attributes.

========================
F) WHOLE-OBJECT GATING (ANTI “PART MISLABEL”)
========================
You MUST confirm “whole object” before naming the device class.
Use at least 2 independent structural cues.

Common confusion gates:
- Laptop vs Keyboard:
  - Laptop requires at least TWO of: hinge line + screen plane, trackpad, palm rest integrated, visible ports, chassis thickness, speaker grills.
  - Keyboard-alone typically shows keys only, no hinge/screen plane, often uniform thin slab; do not call it “laptop”.
- Tablet vs Laptop/2-in-1:
  - Tablet requires at least TWO of: rear camera module, flat slab form, no hinge, detachable keyboard seam, kickstand.
- Phone vs Remote vs Power bank:
  - Phone: camera(s) + screen proportions + side buttons.
  - Remote: dense button matrix + IR window.
  - Power bank: ports + indicator LEDs, typically no camera.
- Headphones vs Ear muffs/fashion:
  - Headphones: driver housings + yokes + ports/buttons.
- Shoe vs Sock/cover:
  - Shoe: outsole/tread + rigid form.

If gating fails: output generic noun (“keyboard”, “laptop computer”, “tablet”) + attributes; do not force a specific class.

========================
G) UNIVERSAL COMMERCIAL DNA FIELDS (CROSS-VERTICAL)
========================
Extract ONLY what is visible/legible:
- Brand
- Core product noun (the catalog “head term”): e.g., laptop, wireless keyboard, running shoes, serum, office chair, drill, wiper blades, soda can
- Model/series (only if printed or uniquely confirmed)
- Variant (flavor/scent/shade/edition) only if printed or clearly labeled
- Size/measurements (inch, ml, g, oz, count) only if printed or clearly inferable from label
- Color/finish (matte black, silver, space gray)
- Material (leather, stainless steel, glass) if visually reliable
- Pattern/style/fit (striped, slim, oversized) for apparel if visually reliable
- Packaging form (bottle, tube, can, box, jar, blister)
- Compatibility (only if printed: e.g., “for iPad Pro 11-inch”, “for Toyota …”)

========================
H) MODE TEMPLATES (AUTO-SWITCH) + GLOBAL OTHER
========================
MODE ELECTRONICS/TECH:
- Brand + core device + series/model (if evidenced) + size (if evidenced) + key feature words (wireless, mechanical, USB-C) ONLY if evidenced.

MODE FASHION/APPAREL:
- Brand + target (men/women/kids/unisex if visually clear) + item (jacket/sneakers/bag) + color + material + pattern + style keywords.

MODE BEAUTY/PERSONAL CARE:
- Brand + product line (if printed) + type (serum/lipstick/shampoo) + variant/shade/scent + size.

MODE HOME/FURNITURE/DECOR:
- Brand (if any) + item (chair/lamp/rug) + style (mid-century/industrial only if visually strong) + material + color + dimensions (only if printed).

MODE CPG/GROCERY/PACKAGED GOODS:
- Brand + exact variant/flavor/scent + size/weight + packaging type + multipack count (if printed).

MODE AUTOMOTIVE/TOOLS/INDUSTRIAL:
- Brand + tool/part name + size standard (mm/inch/Ah) + model code (if printed) + compatibility ONLY if printed.

MODE TOYS/GAMES/COLLECTIBLES:
- Brand/franchise + character/model + product type + edition keywords (only if printed).

MODE MEDICAL/SUPPLEMENTS:
- Brand + product name + dosage + count (only if printed). No claims.

MODE GLOBAL OTHER (MANDATORY FALLBACK):
If no mode fits confidently:
- Brand (if any) + generic noun + 3–6 strongest visible differentiators + packaging form (if any).

========================
I) QUERY COMPOSER (ONE-LINE KEYWORDS)
========================
Compose ONE line in this strict order:
1) Brand
2) Core product noun
3) Model/series (if evidenced)
4) Variant (if evidenced)
5) Size/capacity/count (if evidenced)
6) Color/finish
7) Material/pattern/style (only if reliable)
8) One disambiguator token ONLY if evidenced (e.g., “wireless”, “mechanical”, “case”, “refill”, “with stand”)

Token budget:
- Aim 6–14 tokens. Prefer precision over verbosity.
- Remove weak/ambiguous adjectives.

========================
J) FINAL VERIFICATION (SILENCE TEST)
========================
Before output, ensure:
- The line describes the DOMINANT product (not an accessory/part).
- Every token is defensible from visible text/logo/structure.
- If exact identity is uncertain, you did NOT invent details; you degraded safely.
- Output is a single line of searchable keywords only.

OUTPUT NOW: ONE LINE OF SEARCH KEYWORDS ONLY.
        """
        try:
            logger.info("👁️ Engaging Vision Model for Optical Analysis...")
            
            completion = await self._safe_execute(
                self.client.chat.completions.create,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Extract the commercial search terms for this product."},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                            }
                        ]
                    }
                ],
                model=self.vision_model,
                temperature=0.05, 
                max_tokens=450,
                top_p=0.85,
            )
            
            search_terms = completion.choices[0].message.content.strip()
        
            search_terms = search_terms.replace('"', '').replace("Search query:", "").strip()
            
            logger.info(f"👁️ Visual Cortex Output: '{search_terms}'")

            if enrich_with_search and len(search_terms.split()) > 1 and "generic" not in search_terms.lower():
                try:
                    tavily_key = os.getenv("TAVILY_API_KEY")
                    
                    if not tavily_key:
                        logger.warning("⚠️ Flash Search Skipped: Missing TAVILY_API_KEY")
                    else:
                        logger.info(f"🌍 Initiating Global Validation via Tavily for: '{search_terms}'...")

                        def _execute_flash_search():
                            try:
                                from tavily import TavilyClient
                                client = TavilyClient(api_key=tavily_key)
                                
                                return client.search(
                                    query=f"{search_terms} official product name price", 
                                    max_results=1,
                                    search_depth="basic", 
                                    include_domains=[],   
                                )
                            except Exception as inner_e:
                                logger.error(f"❌ Tavily Internal Error: {inner_e}")
                                return None

                        loop = asyncio.get_running_loop()
            
                        search_result = await loop.run_in_executor(None, _execute_flash_search)

                        if search_result and search_result.get('results'):
                            top_hit = search_result['results'][0]
                            official_title = top_hit.get('title', '').strip()
                            
                            if official_title:
                            
                                refined_tokens = re.sub(r'[^\w\s]', '', official_title).split()[:6]
                                official_fragment = " ".join(refined_tokens)
                                
                                combined_query = f"{search_terms} {official_fragment}"
                                
                                seen = set()
                                final_terms = []
                                for word in combined_query.split():
                                    lower_word = word.lower()
                                    if lower_word not in seen:
                                        seen.add(lower_word)
                                        final_terms.append(word)
                                
                                search_terms = " ".join(final_terms)
                                logger.info(f"✅ Enhanced Visual DNA (Fused): '{search_terms}'")

                except Exception as e:
                    logger.warning(f"⚠️ Search Bridge Bypassed (Non-Critical): {e}")

            return search_terms

        except Exception as e:
            logger.error(f"🔥 Visual Analysis Failed: {e}")
            return "generic product"  #
                

    async def _perform_web_search(self, query: str) -> str:
        """
        🌍 GLOBAL KNOWLEDGE UPLINK (V18.0 - TAVILY ENTERPRISE).
        CORE: Tavily AI Search API (The 'Google' built for LLMs).
        CAPABILITY: Universal Search (Products, Services, General Knowledge).
        SCOPE: From a needle to a rocket (Unlimited Context).
        """
        try:
            
            api_key = os.getenv("TAVILY_API_KEY")
            
            if not api_key:
                logger.error("❌ ENTERPRISE ALERT: TAVILY_API_KEY is missing in .env")
                return "System Configuration Error: Global Search Uplink is Down."

            clean_query = re.sub(r'(hey ai|please|can you)', '', query, flags=re.IGNORECASE).strip()
            
            search_context = clean_query
            if not any(x in search_context.lower() for x in ["price", "cost", "how much", "who", "where"]):

                 search_context += " comprehensive details specifications and latest data"

            logger.info(f"📡 Global Uplink (Tavily): Scanning reality for '{search_context}'...")
            
            def execute_global_search():
                client = TavilyClient(api_key=api_key)
                return client.search(
                    query=search_context,
                    search_depth="advanced", 
                    max_results=5,           
                    include_answer=True,     
                    include_raw_content=False,
                    include_domains=[],      
                    topic="general"          
                )

            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, execute_global_search)
            
            parts = []
            
            direct_answer = response.get("answer", "")
            if direct_answer:
                parts.append(f"• INTELLIGENCE SUMMARY: {direct_answer}")
            
            results = response.get("results", [])
            if not results and not direct_answer:
                return "Global search yielded no confirmed data."

            for res in results:
                title = res.get("title", "Source").replace("\n", " ").strip()
                content = res.get("content", "")[:350].replace("\n", " ").strip()
                url = res.get("url", "N/A")
                parts.append(f"• DATA ({title}): {content}")
            
            final_report = "\n".join(parts)
            
            logger.info(f"✅ Global Uplink Successful. Retrieved {len(results)} verified sources.")
            return final_report

        except Exception as e:
            logger.error(f"🔥 Global Search Bridge Failure: {e}")
            return "Connection to Global Knowledge Grid failed. Please verify API Credentials."

    async def consult_on_product(
        self, 
        product_data: Dict[str, Any], 
        question: str, 
        chat_history: List[Dict[str, str]] = None
    ) -> str:
        """
        🎤 SENIOR PRODUCT CONNOISSEUR (THE OMNI-PRESENT V200).
        ARCHITECTURAL MASTERPIECE.
        
        💎 CAPABILITIES:
        1. Universal Attribute Guard: Handles mismatches in Size, Spec, Flavor, Material, Compatibility.
        2. Deep Chameleon: Adapts linguistic DNA to 50+ micro-verticals.
        3. Silent Luxury: Enforces strict visual elegance (No shouting).
        4. Resilience: Never says "I don't know", always finds the "Value Angle".
        """
        
        if not hasattr(self, 'client') or not self.client:
            return f"The {product_data.get('name')} is a premium selection available now."

        clean_data = {
            k: v for k, v in product_data.items() 
            if k not in ['id', 'created_at', 'updated_at', 'vectors', 'image_url', 'slug', 'inventory_count']
        }
        internal_context = json.dumps(clean_data, default=str)
        
        external_knowledge = "OFFICIAL DATA PENDING"
        try:
            
            search_target = f"{product_data.get('name')} {question}"
            if hasattr(self, '_perform_web_search'):
                external_knowledge = await self._perform_web_search(search_target)
        except Exception as e:
            logger.warning(f"⚠️ Web Intel Bypassed: {e}")

        system_core = f"""
        You are 'AirDeliver', the world's most sophisticated Product Authority.
        Your mission is to curate, explain, and elevate the user's understanding of ANY item.
        Your tone is: Expert, Warm, and Impeccably Polished.

        --- 📡 INPUT DATA ---
        1. [PRODUCT ON SHELF]: {internal_context}
        2. [MARKET INTEL]: {external_knowledge}
        3. [USER DESIRE]: "{question}"

        --- 🧠 1. THE "UNIVERSAL ATTRIBUTE PIVOT" (THE CORE INTELLIGENCE) ---
        You must detect ANY mismatch between [USER DESIRE] and [PRODUCT ON SHELF].
        This applies to: Color, Size, RAM, Flavor, Material, Compatibility, Vintage, or Power.

        **THE PROTOCOL:**
        IF a specific attribute is requested but missing:
        1. **NEVER SAY "NO"**: Do not start with "Unfortunately", "Sorry", or "Not available".
        2. **VALIDATE & BRIDGE**: Acknowledge the requested spec as a great choice, then pivot to the value of the CURRENT item.
        
        *Scenarios (Universal Logic):*
        - (Tech) Asked for 32GB RAM -> Has 16GB: "While 32GB is powerful, this 16GB Unified Memory architecture is optimized to outperform expectations."
        - (Fashion) Asked for Black -> Has Blue: "The Midnight Black is a classic, yet this Navy Blue edition offers a rare, sophisticated depth."
        - (Food) Asked for Spicy -> Has Mild: "For those who prefer heat, this Mild blend focuses on revealing the rich, authentic notes of the ingredients."
        - (Auto) Asked for Turbo -> Has Base: "The Turbo is aggressive, but this model delivers the most balanced and efficient drive in its class."

        --- 🦎 2. THE "DEEP CHAMELEON" ADAPTATION ---
        Shift your vocabulary based on the item's soul:
        
        A. **ENGINEERING (Tech/Auto/Tools)**:
           - Focus: Precision, Torque, Efficiency, Build Quality.
           - Words: "Engineered", "Robust", "Seamless", "Benchmark".
           
        B. **AESTHETICS (Fashion/Decor/Art)**:
           - Focus: Texture, Silhouette, Palette, Atmosphere.
           - Words: "Curated", "Timeless", "Artisanal", "Statement".
           
        C. **SENSORY (Food/Beauty/Wellness)**:
           - Focus: Notes, Finish, Purity, Ritual.
           - Words: "Radiant", "Authentic", "Revitalizing", "Essence".
           
        D. **INTELLECT (Books/Software/Courses)**:
           - Focus: Insight, Clarity, Methodology, Impact.
           - Words: "Comprehensive", "Transformative", "Essential", "Definitive".

        --- 🎨 3. THE "SILENT LUXURY" VISUAL STANDARD ---
        1. **ZERO MARKDOWN**: NO asterisks (**), NO hashes (#), NO backticks (`). Pure text.
        2. **NO SHOUTING**: NEVER use ALL CAPS. Use Title Case for headers.
        3. **CLEAN LISTS**: Use ONLY a simple dot (•) for bullet points.
        4. **NO QUOTES**: Do not put quotes around feature names.

        --- 📝 4. RESPONSE STRUCTURE (STRICT) ---
        
        [Direct Answer: Address the specific question/constraint gracefully. Max 2 sentences.]
        
        [Blank Line]
        
        [3-4 Highlights tailored to the specific category:]
        • Feature Name: The sophisticated explanation (Bridge Spec to Benefit).
        • Feature Name: The sophisticated explanation.
        • Feature Name: The sophisticated explanation.
        
        [Blank Line]
        
        [A short, confidence-inspiring closing statement.]

        --- 🛡️ 5. INTEGRITY ---
        - Respond in the **USER'S LANGUAGE**.
        - If data is missing, rely on Brand Reputation and Market Intel.
        - Do not hallucinate. If specs are unknown, focus on "Quality Assurance".
        """

        messages = [{"role": "system", "content": system_core}]
        if chat_history:
            messages.extend(chat_history[-2:]) 
        messages.append({"role": "user", "content": f"USER DESIRE: {question}\nPRODUCT DNA: {product_data.get('name')}"})

        try:
            model_to_use = getattr(self, 'brain_model', "gpt-3.5-turbo")
            
            completion = await self._safe_execute(
                self.client.chat.completions.create,
                messages=messages,
                model=model_to_use, 
                temperature=0.5, 
                max_tokens=800,
                top_p=0.9,
            )
            return completion.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Consultation Core Failed: {e}")
            desc = product_data.get('description', 'A premium selection.')
            return f"This item represents a standard of excellence.\n\n• Overview: {desc}\n\nReady for immediate dispatch."

    async def strategize_search(self, user_query: str) -> SearchStrategy:
        """
        🚀 DECISION ENGINE.
        Translates human intent into database queries.
        
        Updates:
        - Enhanced Category Detection logic.
        - Better handling of vague queries (mapping to 'Trending').
        """
        if not self.client:
            return SearchStrategy(
                is_direct_product_request=True, 
                search_queries=[user_query], 
                response_tone="Standard", 
                direct_answer_prefix="Results found:"
            )

        system_core = """
        ROLE: Elite Search Architect & Intent Decoder.
        TASK: Translate user input into a rigid, executable JSON Search Strategy.

        --- 🧠 UNIVERSAL INTENT HIERARCHY (THE "QUESTION TRUMPS COMMAND" PROTOCOL) ---

        1. **THE GOLDEN RULE (CRITICAL OVERRIDE)**:
           - **TRIGGER**: If the input contains ANY form of inquiry, doubt, comparison, reasoning, or validation.
           - **LOGIC**: Even if the user says "Find X", if they add "...and tell me if Y", the Intent is CONSULTATION.
           - **EXECUTION**: `is_direct_product_request` MUST BE **FALSE**.
           - **UNIVERSAL SIGNALS**:
             * Questions: "Does it?", "Is it?", "Why?", "How?", "Can I?", "When?".
             * Conditions: "If I use it for...", "Provided that...", "Unless...".
             * Subjective Nuance: "Good for beginners?", "Best value?", "Worth it?", "Any good?".

        2. **INTENT CLASSIFICATION**:
           - **DIRECT REQUEST (True)**: Triggered ONLY when the input is PURELY transactional/navigational.
             * Signals: "Find [Product]", "Show [Category]", "Price of [Item]", "Buy [SKU]".
             * Condition: User is NOT asking for an opinion or technical fact.
             * Example: "Find Samsung S24 Ultra 1TB" -> `True`.

           - **BROWSING/CONSULTING (False)**: Triggered by ANY complexity or curiosity (Big or Small).
             * **Stress Test A (The Hybrid)**: "I want the iPhone 15. Is the battery better than the 14?" -> **FALSE**.
             * **Stress Test B (The Skeptic)**: "Find cheap laptops. Will they break fast?" -> **FALSE**.
             * **Stress Test C (The Novice)**: "Show me cameras. Which is good for vlogging?" -> **FALSE**.
             * **Stress Test D (The Detail)**: "Blue shirt. Is the fabric cotton?" -> **FALSE**.

        3. **THE "INVARIANCE PRINCIPLE" (ATTRIBUTE EXTRACTION)**:
           - Even when defaulting to Consultation (`False`), you MUST extract technical constraints to aid the search.
           - **Capture EVERYTHING**: Color, Size, RAM, Voltage, Texture, Era, Flavor.

           --- 🌟 UNIVERSAL ATTRIBUTE EXTRACTION (COVERING ALL DOMAINS) ---
           
           [SCENARIO: TECH SPECS]
           * Input: "Find the one with 32GB RAM"
           * Constraint: "32GB RAM" -> Query: "[Product] 32GB RAM"
           
           [SCENARIO: COMPATIBILITY]
           * Input: "Show me the version for PS5"
           * Constraint: "PS5 Compatible" -> Query: "[Product] PS5 edition"
           
           [SCENARIO: MATERIAL/TEXTURE]
           * Input: "I want the leather one"
           * Constraint: "Leather" -> Query: "[Product] Leather"
           
           [SCENARIO: TEMPORAL/VERSION]
           * Input: "Get the 2024 model"
           * Constraint: "2024" -> Query: "[Product] 2024 model"
           
           [SCENARIO: CONDITION/STATE]
           * Input: "Find a refurbished one"
           * Constraint: "Refurbished" -> Query: "[Product] Refurbished"
           
           [SCENARIO: ABSTRACT/VIBE]
           * Input: "Something for a wedding"
           * Constraint: "Wedding/Formal" -> Query: "[Product] Wedding Formal"

        4. **QUERY CONSTRUCTION STRATEGY**:
           - **Query 1 (The Sniper)**: [Core Product Name] + [USER CONSTRAINT EXACTLY].
           - **Query 2 (The Net)**: [Core Product Name] + [Constraint Synonym].
           - **Query 3 (The Context)**: [Core Product Name] + [Category].

        5. **CATEGORY & PRICE LOGIC**:
           - Map fuzzy terms to global verticals (e.g., "Lipstick" -> "Beauty").
           - Detect Price Constraints: "Under 50" -> `price_max: 50`.
           - Detect Quality Constraints: "Cheap" -> Low Tier / "Best" -> High Tier.

        --- JSON OUTPUT SCHEMA ---
        {
            "is_direct_product_request": bool, 
            "search_queries": [str], 
            "price_min": float or null,
            "price_max": float or null, 
            "category_filter": str or null, 
            "attributes": [str],
            "response_tone": str, 
            "direct_answer_prefix": str
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
                response_format={"type": "json_object"}
            )
            
            raw_json = self._clean_json_response(completion.choices[0].message.content)
            data = json.loads(raw_json)
            return SearchStrategy(**data)
            
        except Exception as e:
            logger.warning(f"Strategy Fallback: {e}")
            return SearchStrategy(
                is_direct_product_request=False, 
                search_queries=[user_query, f"{user_query} best price"], 
                response_tone="Helpful", 
                direct_answer_prefix="Here are the best matches I found:"
            )


    async def extract_search_terms(self, user_query: str) -> str:
        """
        🎯 UNIVERSAL ATOMIC EXTRACTOR (V300.0 - GLOBAL EDITION).
        ARCHITECTURAL GOAL: Distill complex user 'stories' into 'database-ready' tokens.
        
        💎 GLOBAL UPGRADES:
        1. Multilingual Guard: Preserves the user's language (No forced translation).
        2. Domain Agnostic: Works for Fashion, Food, Tech, or Industrial parts.
        3. Noise Cancellation: Surgical removal of filler words.
        """
        if not self.client or not user_query or not user_query.strip(): 
            return user_query

        system_prompt = """
        ROLE: Master Database Query Optimizer (Multilingual).
        TASK: Convert Human Narrative into Machine Search Tokens.
        
        --- 🧠 UNIVERSAL EXTRACTION PROTOCOL ---
        
        1. **IDENTIFY THE ENTITY (THE NOUN)**:
           - What is the physical item? (e.g., "Laptop", "فستان", "Screwdriver").
           - **CRITICAL**: KEEP THE INPUT LANGUAGE. Do not translate unless explicitly asked.
             * Input: "عايز تليفون سامسونج" -> Output: "تليفون سامسونج" (Not "Samsung Phone").
           
        2. **IDENTIFY THE CORE MODIFIER (THE ADJECTIVE)**:
           - What is the *defining* feature? (e.g., "Gaming", "أحمر", "Spicy").
           - Convert "usage" to "adjective":
             * "Phone for taking photos" -> "Camera Phone"
             * "لابتوب للالعاب" -> "لابتوب جيمنج"
             
        3. **ELIMINATE NOISE (STRICT)**:
           - **REMOVE PRICE**: "Under $500", "Cheap", "Budget", "رخيص". (Logic handles this, not text search).
           - **REMOVE STORY**: "For my son", "I need", "Can you find", "عايز اشتري".
           - **REMOVE FILLERS**: "Best", "Top", "Good", "Please", "لو سمحت".

        4. **HANDLING ABSTRACTS (DOMAIN NEUTRAL)**:
           - Input: "Something cool" -> Output: "Trending Items"
           - Input: "Gift for mom" -> Output: "Women Gift"
           - Input: "حاجة حلوة" -> Output: "Best Sellers"

        --- 🎯 EXAMPLES (GLOBAL SCENARIOS) ---
        * Input: "I have a budget of 700 for a laptop capable of editing 4k" 
          -> Output: "High Performance Laptop"
          
        * Input: "وريني جزم تنفع للكورة بس متكونش غالية" 
          -> Output: "جزم كورة"
          
        * Input: "Show me a red dress for a wedding" 
          -> Output: "Red Wedding Dress"
          
        * Input: "Samsung S24 Ultra black 512gb" 
          -> Output: "Samsung S24 Ultra Black"

        OUTPUT FORMAT: Raw text string (2-5 words max). No quotes.
        """

        try:
            completion = await self._safe_execute(
                self.client.chat.completions.create,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ],
                model=self.reflex_model, 
                temperature=0.0, 
                max_tokens=40    
            )
            
            optimized_query = completion.choices[0].message.content.strip()
            optimized_query = optimized_query.replace('"', '').replace("'", "")
            
            return optimized_query
            
        except Exception as e:

            return user_query.strip()

    def _rank_products_by_relevance(self, query: str, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        🚀 FERRARI PRE-FILTER.
        Locally scores products to ensure only the 'Cream of the Crop' reaches the LLM.
        This saves Tokens and Latency.
        """
        if not products: return []
        
        query_terms = set(query.lower().split())
        scored_products = []
        
        for p in products:
            score = 0
            p_name = str(p.get('name', '')).lower()
            p_cat = str(p.get('category', '')).lower()
            p_desc = str(p.get('description', '')).lower()
            
            if query.lower() in p_name:
                score += 100
            
            matches = 0
            for term in query_terms:
                if term in p_name: 
                    score += 50  
                    matches += 1
                elif term in p_cat:
                    score += 30  
                    matches += 1
                elif term in p_desc:
                    score += 10  
            
            if len(query_terms) > 0 and matches == len(query_terms):
                score += 20 

            try:
                rating = float(p.get('rating', 0))
                score += rating * 2
            except: pass

            scored_products.append((score, p))
            
        scored_products.sort(key=lambda x: x[0], reverse=True)
        
        return [item[1] for item in scored_products]


    async def filter_and_recommend(self, user_query: str, products: List[Dict[str, Any]], tone_instruction: str = "Professional") -> Optional[CognitiveResponse]:
        """
        🏆 CHIEF MERCHANDISING OFFICER.
        Analyzes the top candidates and hand-picks the winners based on the User's Soul.
        Generates the 'Intro Message' that appears in the UI.
        """
        if not self.client or not products: return None

        try:
        
            ranked_products = self._rank_products_by_relevance(user_query, products)
            
            MAX_CONTEXT_ITEMS = 12
            products_slice = ranked_products[:MAX_CONTEXT_ITEMS]

            context = [
                {
                    "id": p.get('id'), 
                    "name": p.get('name'), 
                    "price": p.get('price'), 
                    "rating": p.get('rating', 'N/A'),
                    "category": p.get('category')
                } 
                for p in products_slice
            ]
            
            system_core = f"""
            ROLE: Chief Buyer & Personal Shopper for 'airdeliver'.
            YOUR VIBE: {tone_instruction}, Charismatic, Trustworthy.

            TASK: Select the top 3-5 products from the list that BEST match the User Query: "{user_query}".
            
            --- SELECTION LOGIC ---
            1. **RELEVANCE KING**: If user asks for "Red Shoes", do not pick "Blue Hat".
            2. **VALUE SCOUT**: If prices vary, pick a mix of 'Best Value' and 'Premium'.
            3. **SOCIAL PROOF**: Prefer items with higher ratings if available.
            4. **DIVERSITY**: Don't show 5 identical items. Show variety.

            --- OUTPUT FORMAT (JSON) ---
            {{
                "selected_ids": [int],  // List of IDs for the winners
                "reasoning": {{ "id": "Short punchy reason" }}, // Why you picked it? (e.g., "Best rated option")
                "intro_message": "String", // A charismatic UI message introducing the collection.
                "confidence_score": float // 0.0 to 1.0
            }}

            --- INTRO MESSAGE STYLE ---
            - Be human. Use 1 emoji.
            - Example: "I found some top-tier options for you. The first one is a steal! "
            - Example: "Here are the best matches based on specs and price. 🛡️"
            """
            
            completion = await self._safe_execute(
                self.client.chat.completions.create,
                messages=[
                    {"role": "system", "content": system_core},
                    {"role": "user", "content": json.dumps(context)}
                ],
                model=self.brain_model, 
                temperature=0.2, 
                response_format={"type": "json_object"}
            )
            
            raw_json = self._clean_json_response(completion.choices[0].message.content)
            data = json.loads(raw_json)
            
            if "reasoning" in data: 
                data["reasoning"] = {str(k): str(v) for k, v in data["reasoning"].items()}
                
            return CognitiveResponse(**data)
            
        except Exception as e:
            logger.error(f"Cognitive Filter Failed: {e}")
            return None


    async def handle_commerce_interaction(
        self, 
        user_query: str, 
        all_products: List[Dict[str, Any]], 
        chat_history: List = None
    ) -> Dict[str, Any]:
        """
        🚀 THE OMNI-ORCHESTRATOR (V1000.0 - GOOGLE LEVEL).
        Architectural Goal: Zero-Latency, Context-Aware, Fail-Safe Decision Making.
        
        💎 ENGINEERING PILLARS:
        1. **Parallel Cognitive Processing**: Executes Intent Analysis & SEO Extraction concurrently.
        2. **Heuristic Search Layering**: Exact Match -> Fuzzy Match -> Fallback Strategy.
        3. **Dynamic Routing**: Smart switching between 'Consultant' and 'Salesman' personas.
        """
        try:
            loop = asyncio.get_running_loop()
            strategy_task = self.strategize_search(user_query)
            seo_task = self.extract_search_terms(user_query)
            
            strategy, clean_terms = await asyncio.gather(strategy_task, seo_task)
            
            logger.info(f"🧠 Orchestrator: Intent={not strategy.is_direct_product_request} | SEO='{clean_terms}'")

            relevant_products = self._rank_products_by_relevance(clean_terms, all_products)
            
            if not relevant_products and clean_terms != user_query:
                relevant_products = self._rank_products_by_relevance(user_query, all_products)
                
            if not relevant_products:
                relevant_products = sorted(all_products, key=lambda x: x.get('rating', 0), reverse=True)[:5]

            target_products = relevant_products[:5]
            hero_product = target_products[0] if target_products else {"name": "General Catalog", "description": "Various items"}

            if not strategy.is_direct_product_request:
                logger.info("🧠 Route: CONSULTATION (Deep Analysis Mode)")
                
                consultation_text = await self.consult_on_product(
                    product_data=hero_product,
                    question=user_query,
                    chat_history=chat_history
                )
                
                return {
                    "type": "consultation",
                    "text": consultation_text,
                    "products": target_products, 
                    "search_terms": clean_terms,
                    "intent_metadata": strategy.dict()
                }

            else:
                logger.info("🛒 Route: CAROUSEL (Direct Transaction Mode)")
                
                recommendation = await self.filter_and_recommend(
                    user_query=user_query,
                    products=target_products,
                    tone_instruction=strategy.response_tone
                )
                
                intro = recommendation.intro_message if recommendation else f"I found these top matches for '{clean_terms}'."
                ids = recommendation.selected_ids if recommendation else [p.get('id') for p in target_products[:3]]

                return {
                    "type": "carousel",
                    "intro": intro,
                    "selected_ids": ids,
                    "products": target_products,
                    "search_terms": clean_terms,
                    "intent_metadata": strategy.dict()
                }

        except Exception as e:
            logger.critical(f"🔥 ORCHESTRATOR FAILURE: {e}")
            return {
                "type": "consultation", 
                "text": "I'm currently optimizing my neural search. Here are some top picks in the meantime.",
                "products": all_products[:5],
                "search_terms": user_query
            }
