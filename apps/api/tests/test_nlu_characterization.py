# apps/api/tests/test_nlu_characterization.py
"""
CHARACTERIZATION TESTS for app/services/ai_nlu_service.py

Purpose: pin down the CURRENT behavior of the intent-understanding layer
(parsing, constraint extraction, intent contract, sanitization, alignment)
BEFORE any behavior change. These tests describe what the code does today -
not necessarily what it should do. Where current behavior looks questionable
the test says so in a comment, but still asserts the current truth.

No network, database, Redis, RabbitMQ, or LLM access is used.
"""
import base64
import random
from decimal import Decimal

import pytest

from app.services.ai_nlu_service import (
    AINLUService,
    CartActionType,
    CommerceIntentPayload,
    ConstraintExtractor,
    DiamondInterceptor,
    IntentCategory,
    InternalCommand,
    MemoryEvent,
    MessageType,
    RedisKeys,
    SearchConstraints,
    TextSanitizer,
    UniversalProductTarget,
    UserSentiment,
    _build_broad_query,
    _deduplicate_products,
    _extract_command_argument,
    _normalize_search_text,
    _parse_internal_command,
    _safe_product_get,
    _sanitize_free_text,
    extract_capacity_specs,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service() -> AINLUService:
    """AINLUService with inert stand-ins: constructors only store references."""
    return AINLUService(
        db=object(),
        search_engine=object(),
        rabbitmq=object(),
        cache=object(),
        llm_service=object(),
        behavior_engine=None,
    )


# ===========================================================================
# Capacity spec extraction (RAM / storage regexes)
# ===========================================================================

class TestExtractCapacitySpecs:
    def test_ram_gb_pre_context(self):
        assert extract_capacity_specs("laptop with 16gb ram")["ram_gb"] == 16.0

    def test_ram_gb_post_context(self):
        assert extract_capacity_specs("ram 16 gb")["ram_gb"] == 16.0

    def test_ram_mb_normalized_to_gb(self):
        assert extract_capacity_specs("2048mb ram")["ram_gb"] == 2.0

    def test_memory_keyword_counts_as_ram(self):
        assert extract_capacity_specs("8gb memory")["ram_gb"] == 8.0

    def test_storage_gb(self):
        assert extract_capacity_specs("512gb ssd")["storage_gb"] == 512.0

    def test_storage_tb_normalized_to_gb(self):
        assert extract_capacity_specs("1tb nvme")["storage_gb"] == 1024.0

    def test_max_candidate_wins(self):
        specs = extract_capacity_specs("8gb ram or 16gb ram version")
        assert specs["ram_gb"] == 16.0

    def test_no_specs_returns_none(self):
        specs = extract_capacity_specs("wireless headphones")
        assert specs == {"ram_gb": None, "storage_gb": None}

    def test_case_insensitive(self):
        assert extract_capacity_specs("16GB RAM")["ram_gb"] == 16.0


# ===========================================================================
# ConstraintExtractor - query constraints from free text
# ===========================================================================

class TestConstraintExtractor:
    def setup_method(self):
        self.extractor = ConstraintExtractor()

    def test_price_max_from_dollar_amount(self):
        c = self.extractor.extract("I want a laptop under $1500")
        assert c.price_max == 1500.0

    def test_price_max_k_suffix_multiplies(self):
        c = self.extractor.extract("looking for a phone max 2k")
        assert c.price_max == 2000.0

    def test_vibe_word_sets_price_cap(self):
        c = self.extractor.extract("cheap headphones")
        assert c.price_max == 500.0
        assert c.intent_vibe == "cheap"

    def test_budget_vibe_cap(self):
        c = self.extractor.extract("budget laptop for school")
        assert c.price_max == 1000.0
        assert c.intent_vibe == "budget"

    def test_open_budget_clears_price(self):
        c = self.extractor.extract("budget is open, show me laptops")
        assert c.price_max is None

    def test_category_anchor_from_want_pattern(self):
        c = self.extractor.extract("I want a laptop under $1500")
        assert c.category_filter == "laptop"

    def test_ignored_anchor_words_not_category(self):
        # "best", "cheap", "product" etc. must never become the category anchor
        c = self.extractor.extract("I want the best product")
        assert c.category_filter is None

    def test_negation_excludes_keyword(self):
        c = self.extractor.extract("headphones without wires")
        assert "wires" in c.excluded_keywords

    def test_negation_skipped_when_comparison(self):
        # comparison markers disable negation handling entirely
        c = self.extractor.extract("why is x not better than y")
        assert c.excluded_keywords == ()

    def test_required_specs_ram(self):
        c = self.extractor.extract("laptop with 16gb ram")
        assert c.required_specs.get("ram") == 16

    def test_required_specs_storage_tb_as_int_gb(self):
        c = self.extractor.extract("1tb ssd laptop")
        assert c.required_specs.get("storage") == 1024

    def test_clean_query_strips_junk_words(self):
        c = self.extractor.extract("I want a laptop under $1500")
        assert "want" not in c.clean_query
        assert "1500" not in c.clean_query

    def test_empty_query_falls_back_to_original(self):
        c = self.extractor.extract("   want need  ")
        # clean_query empty -> original text returned
        assert c.clean_query == "want need"

    def test_price_min_always_none_today(self):
        # current behavior: price_min is never populated
        c = self.extractor.extract("phone between 500 and 1000")
        assert c.price_min is None

    def test_constraints_to_filters_shape(self):
        c = SearchConstraints(
            clean_query="laptop", price_max=100.0, category_filter="laptop",
            excluded_keywords=("x",),
        )
        assert c.to_filters() == {
            "price_max": 100.0, "category": "laptop", "excluded_keywords": ["x"],
        }
        assert SearchConstraints(clean_query="q").to_filters() == {}


# ===========================================================================
# CommerceIntentPayload - the LLM intent contract
# ===========================================================================

class TestCommerceIntentPayload:
    def _payload(self, **overrides):
        base = {
            "category": "SPECIFIC_SEARCH",
            "is_chitchat": False,
            "target_products": [],
        }
        base.update(overrides)
        return base

    def test_minimal_valid_payload(self):
        p = CommerceIntentPayload(**self._payload())
        assert p.category == IntentCategory.SPECIFIC_SEARCH
        assert p.sentiment == UserSentiment.NEUTRAL
        assert p.is_jailbreak_attempt is False
        assert p.target_products == []

    def test_extra_fields_rejected(self):
        with pytest.raises(Exception):
            CommerceIntentPayload(**self._payload(unknown_field="x"))

    def test_is_chitchat_required(self):
        with pytest.raises(Exception):
            CommerceIntentPayload(category="SPECIFIC_SEARCH")

    def test_blank_optional_strings_become_none(self):
        p = CommerceIntentPayload(
            **self._payload(detected_occasion="   ", suggested_pivot="", competitor_mentioned="  ")
        )
        assert p.detected_occasion is None
        assert p.suggested_pivot is None
        assert p.competitor_mentioned is None

    def test_duplicate_products_deduped_case_insensitive(self):
        p = CommerceIntentPayload(**self._payload(target_products=[
            {"product_name": "iPhone 15 Pro"},
            {"product_name": "iphone 15 pro"},
            {"product_name": "  IPHONE 15 PRO "},
        ]))
        assert len(p.target_products) == 1
        assert p.target_products[0].product_name == "iPhone 15 Pro"

    def test_same_name_different_spec_context_kept(self):
        p = CommerceIntentPayload(**self._payload(target_products=[
            {"product_name": "iPhone 15 Pro", "raw_spec_context": "128GB"},
            {"product_name": "iPhone 15 Pro", "raw_spec_context": "256GB"},
        ]))
        assert len(p.target_products) == 2

    def test_empty_product_name_entry_kept_but_rejected_by_validation(self):
        # empty product_name entries survive dedup but fail field validation
        with pytest.raises(Exception):
            CommerceIntentPayload(**self._payload(target_products=[{"product_name": "  "}]))

    def test_cart_action_type_enum(self):
        p = CommerceIntentPayload(
            **self._payload(category="CART_ACTION", cart_action_type="ADD")
        )
        assert p.cart_action_type == CartActionType.ADD

    def test_target_product_is_frozen(self):
        t = UniversalProductTarget(product_name="X")
        with pytest.raises(Exception):
            t.product_name = "Y"

    def test_target_product_extra_rejected(self):
        with pytest.raises(Exception):
            UniversalProductTarget(product_name="X", bogus=1)


# ===========================================================================
# Internal command parsing
# ===========================================================================

class TestInternalCommands:
    def test_add_by_id_with_argument(self):
        cmd = _parse_internal_command("__INTERNAL_ADD_BY_ID__:42")
        assert cmd.name == InternalCommand.ADD_BY_ID
        assert cmd.argument == "42"

    def test_remove_by_id_with_argument(self):
        cmd = _parse_internal_command("__INTERNAL_REMOVE_BY_ID__: 7 ")
        assert cmd.name == InternalCommand.REMOVE_BY_ID
        assert cmd.argument == "7"

    @pytest.mark.parametrize("text,expected", [
        ("__INTERNAL_CLEAR_CART__", InternalCommand.CLEAR_CART),
        ("__INTERNAL_CONFIRM_ORDER__", InternalCommand.CONFIRM_ORDER),
        ("__INTERNAL_SAVE_FOR_LATER__", InternalCommand.SAVE_FOR_LATER),
        ("__INTERNAL_GET_INITIAL_SUGGESTIONS__", InternalCommand.GET_INITIAL_SUGGESTIONS),
        ("__INTERNAL_RESET_SESSION__", InternalCommand.RESET_SESSION),
        ("__INTERNAL_SYNC_CART__", InternalCommand.SYNC_CART),
    ])
    def test_exact_commands(self, text, expected):
        cmd = _parse_internal_command(text)
        assert cmd.name == expected
        assert cmd.argument is None

    def test_add_by_id_without_colon_returns_none(self):
        # current behavior: the parser requires the trailing colon, so the
        # bare command text is not recognized and returns None
        assert _parse_internal_command("__INTERNAL_ADD_BY_ID__") is None

    def test_regular_text_returns_none(self):
        assert _parse_internal_command("add product 42 to my cart") is None

    def test_empty_returns_none(self):
        assert _parse_internal_command("") is None
        assert _parse_internal_command(None) is None

    def test_extract_command_argument(self):
        assert _extract_command_argument("P:abc", "P") == "abc"
        assert _extract_command_argument("P:", "P") is None
        assert _extract_command_argument("X:abc", "P") is None


# ===========================================================================
# TextSanitizer - response post-processing for the UI
# ===========================================================================

class TestTextSanitizer:
    def test_empty_input(self):
        assert TextSanitizer.sanitize_response_text("") == ""
        assert TextSanitizer.sanitize_response_text(None) == ""

    def test_phase_headers_stripped(self):
        assert TextSanitizer.sanitize_response_text("Phase 2: Hello") == "Hello"
        # current behavior: "Part 1 - X" keeps the dash (regex only strips
        # an immediately-attached ":" or "-"), leaving "- Intro"
        assert TextSanitizer.sanitize_response_text("Part 1 - Intro") == "- Intro"

    def test_bracketed_content_removed(self):
        out = TextSanitizer.sanitize_response_text("Hello [INTERNAL_NOTE] world")
        assert "INTERNAL_NOTE" not in out
        assert "Hello" in out

    def test_bullet_normalized(self):
        out = TextSanitizer.sanitize_response_text("● first item")
        assert "- first item" in out

    def test_brand_name_normalized(self):
        out = TextSanitizer.sanitize_response_text("AirDeliver is great, Airdeliver too")
        assert "AirDeliver" not in out
        assert out.count("airdeliver") == 2


# ===========================================================================
# DiamondInterceptor - query/candidate alignment scoring
# ===========================================================================

class TestDiamondInterceptor:
    def test_threshold_defaults(self):
        assert DiamondInterceptor(-1).matcher_threshold == 0.30
        assert DiamondInterceptor("abc").matcher_threshold == 0.30
        assert DiamondInterceptor(150).matcher_threshold == 0.30
        assert DiamondInterceptor(float("nan")).matcher_threshold == 0.30

    def test_threshold_percent_scaling(self):
        assert DiamondInterceptor(50).matcher_threshold == 0.5
        assert DiamondInterceptor(0.42).matcher_threshold == 0.42

    def test_empty_signal_perfect_score(self):
        d = DiamondInterceptor(0.3)
        assert d.validate_alignment("i need an a", {"name": "X", "category": "y"}) == 1.0

    def test_intent_shortcut(self):
        d = DiamondInterceptor(0.3)
        product = {"name": "Zephyr Laptop 14", "category": "laptops", "brand": "zephyr"}
        assert d.validate_alignment("show me something", product, nlu_intent="laptop") == 1.0

    def test_word_hit_scoring(self):
        d = DiamondInterceptor(0.3)
        product = {"name": "AeroPhone 12", "category": "phones", "brand": "aero"}
        # signal words: "aerophone" -> hit in name
        score = d.validate_alignment("aerophone", product)
        assert score == 1.0

    def test_plural_tolerance(self):
        d = DiamondInterceptor(0.3)
        product = {"name": "Phone X", "category": "phones", "brand": ""}
        assert d.validate_alignment("phones", product) == 1.0

    def test_zero_hit_scores_zero(self):
        d = DiamondInterceptor(0.3)
        product = {"name": "Blender", "category": "kitchen", "brand": ""}
        assert d.validate_alignment("spaceship", product) == 0.0


# ===========================================================================
# Small pure helpers
# ===========================================================================

class TestPureHelpers:
    def test_safe_product_get_mapping(self):
        assert _safe_product_get({"id": 5}, "id") == 5
        assert _safe_product_get({"id": 0}, "id", "dflt") == "dflt"  # falsy -> default
        assert _safe_product_get({}, "id", None) is None

    def test_safe_product_get_object(self):
        class P: price = "10"
        assert _safe_product_get(P(), "price") == "10"

    def test_sanitize_free_text(self):
        assert _sanitize_free_text("  Hello \n  World  ") == "hello world"
        assert _sanitize_free_text(None) == ""

    def test_normalize_search_text(self):
        assert _normalize_search_text("a\r\n\tb   c") == "a b c"

    def test_deduplicate_products_by_id(self):
        products = [{"id": 1}, {"id": 2}, {"id": 1}]
        assert _deduplicate_products(products) == [{"id": 1}, {"id": 2}]

    def test_deduplicate_products_missing_ids_collapse(self):
        # current behavior: products without an id all share id None and
        # collapse into a single entry
        products = [{"name": "a"}, {"name": "b"}]
        assert len(_deduplicate_products(products)) == 1

    def test_build_broad_query_strips_noise(self):
        assert _build_broad_query("I want to buy laptop pro max") == "laptop pro max"

    def test_build_broad_query_max_three_terms(self):
        assert _build_broad_query("alpha beta gamma delta epsilon") == "alpha beta gamma"

    def test_build_broad_query_all_noise_returns_original(self):
        assert _build_broad_query("i want need") == "i want need"

    def test_build_broad_query_empty(self):
        assert _build_broad_query("") == ""


# ===========================================================================
# MemoryEvent
# ===========================================================================

class TestMemoryEvent:
    def test_roundtrip(self):
        ev = MemoryEvent.create("user", "  hello  ", " ")
        assert ev.content == "hello"
        assert ev.intent == "general"  # blank intent -> general
        ev2 = MemoryEvent.from_raw(ev.to_json())
        assert (ev2.role, ev2.content, ev2.intent) == ("user", "hello", "general")

    def test_from_raw_bytes(self):
        ev = MemoryEvent.from_raw(b'{"r":"ai","c":"x","i":"search","t":"1"}')
        assert ev.role == "ai"

    def test_from_raw_garbage_returns_none(self):
        assert MemoryEvent.from_raw("not json") is None


# ===========================================================================
# RedisKeys - keyspace contract (consumers depend on these formats)
# ===========================================================================

class TestRedisKeys:
    def test_formats(self):
        assert RedisKeys.idempotency("abc") == "nlu:idemp:abc"
        assert RedisKeys.ui_channel(7) == "airdeliver:response:7"
        assert RedisKeys.chat_history(7) == "airdeliver:v2:session:7:chat_history"
        assert RedisKeys.seen_products(7) == "airdeliver:v2:session:7:seen_products"
        assert RedisKeys.user_dna(7) == "dna:profile:7"
        assert RedisKeys.ghost_profile(7) == "u:7:ghost_v2"
        assert RedisKeys.cart(7) == "ai_cart:7"


# ===========================================================================
# AINLUService instance-level parsing (constructed with inert stand-ins)
# ===========================================================================

class TestIncomingMessageParsing:
    def setup_method(self):
        self.svc = _make_service()

    def test_minimal_payload(self):
        msg = self.svc._parse_incoming_message({"user_id": 5, "message": "  hi "})
        assert msg.user_id == 5
        assert msg.msg_type == MessageType.CHAT_MESSAGE
        assert msg.message_text == "hi"
        assert msg.lower_text == "hi"

    def test_unknown_type_falls_back_to_chat(self):
        msg = self.svc._parse_incoming_message({"user_id": 5, "type": "WUT", "message": "x"})
        assert msg.msg_type == MessageType.CHAT_MESSAGE

    def test_dict_message_becomes_empty(self):
        msg = self.svc._parse_incoming_message({"user_id": 5, "message": {"nested": 1}})
        assert msg.message_text == ""

    def test_missing_user_id_raises(self):
        with pytest.raises(ValueError):
            self.svc._parse_incoming_message({"message": "hi"})

    def test_explicit_client_msg_id_wins(self):
        msg = self.svc._parse_incoming_message(
            {"user_id": 5, "message": "x", "client_msg_id": "given"}
        )
        assert msg.client_msg_id == "given"

    def test_derived_id_deterministic(self):
        a = self.svc._parse_incoming_message({"user_id": 5, "message": "same"})
        b = self.svc._parse_incoming_message({"user_id": 5, "message": "same"})
        c = self.svc._parse_incoming_message({"user_id": 6, "message": "same"})
        assert a.client_msg_id == b.client_msg_id
        assert a.client_msg_id != c.client_msg_id

    def test_is_internal_command(self):
        assert self.svc._is_internal_command("__anything")
        assert self.svc._is_internal_command("text with INTERNAL marker")
        assert not self.svc._is_internal_command("ordinary message")

    def test_validate_image_payload_too_large(self):
        with pytest.raises(ValueError):
            self.svc._validate_image_payload("x" * 5_000_001)

    def test_validate_image_payload_valid_base64(self):
        self.svc._validate_image_payload(base64.b64encode(b"img").decode())

    def test_validate_image_payload_invalid_base64_raises(self):
        with pytest.raises(ValueError):
            self.svc._validate_image_payload("!!!not-base64!!!")


# ===========================================================================
# Price parsing / filtering
# ===========================================================================

class TestPriceHandling:
    def setup_method(self):
        self.svc = _make_service()

    def test_parse_price_value(self):
        assert self.svc._parse_price_value("$1,299.00") == Decimal("1299.00")
        assert self.svc._parse_price_value("abc") is None
        assert self.svc._parse_price_value("") is None
        assert self.svc._parse_price_value(None) is None
        assert self.svc._parse_price_value("1.2.3") is None

    def test_filter_candidates_by_price(self):
        candidates = [
            {"id": 1, "price": "100.00"},
            {"id": 2, "price": "200.00"},
            {"id": 3, "price": "garbage"},
        ]
        kept = self.svc._filter_candidates_by_price(candidates, 150)
        # in-budget kept; over-budget dropped; unparseable price dropped
        assert [p["id"] for p in kept] == [1]

    def test_filter_invalid_max_returns_all(self):
        candidates = [{"id": 1, "price": "100.00"}]
        assert self.svc._filter_candidates_by_price(candidates, "junk") == candidates


# ===========================================================================
# Diversity enforcement (deterministic under seed)
# ===========================================================================

class TestEnforceDiversity:
    def setup_method(self):
        self.svc = _make_service()

    def test_brand_and_category_caps(self):
        random.seed(7)
        pool = (
            [{"id": i, "brand": "apple", "category": "phones"} for i in range(5)]
            + [{"id": 10 + i, "brand": "samsung", "category": "phones"} for i in range(5)]
        )
        selected = self.svc._enforce_diversity(pool, limit=10, max_per_brand=2, max_per_category=3)
        brands = [p["brand"] for p in selected]
        assert brands.count("apple") <= 2
        assert brands.count("samsung") <= 2
        assert len(selected) <= 3  # category cap 3 for "phones"

    def test_empty_pool(self):
        assert self.svc._enforce_diversity([], limit=5) == []
