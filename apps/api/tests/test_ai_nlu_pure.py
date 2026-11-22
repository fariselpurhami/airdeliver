# apps/api/tests/test_ai_nlu_pure.py
"""Tests for ai_nlu_service pure logic: query building, capacity extraction,
intent payload dedup, retention policy, memory events, text sanitizers."""
import json

import pytest

from app.services.ai_nlu_service import (
    CommerceIntentPayload,
    IntentCategory,
    MemoryEvent,
    RetentionMode,
    SearchConstraints,
    _build_broad_query,
    _deduplicate_products,
    _is_closer_intent,
    _normalize_search_text,
    _parse_internal_command,
    _resolve_retention_mode,
    _sanitize_free_text,
    build_clean_web_query,
    choose_domain_keywords,
    extract_capacity_specs,
)
from app.services.ai_nlu_service import InternalCommand


# --- broad query builder ---

def test_broad_query_strips_noise_and_limits_terms():
    q = _build_broad_query("I want to buy the best gaming laptop please")
    assert len(q.split()) <= 3
    assert "gaming" in q


def test_broad_query_empty_input():
    assert _build_broad_query("") == ""


# --- capacity spec extraction (Arabic/English mixed text) ---

def test_extract_ram_gb():
    specs = extract_capacity_specs("laptop with 16gb ram and 512gb ssd")
    assert specs["ram_gb"] == 16.0


def test_extract_ram_mb_normalized_to_gb():
    specs = extract_capacity_specs("phone with 8192mb ram")
    assert specs["ram_gb"] == 8.0


def test_extract_storage_tb_to_gb():
    specs = extract_capacity_specs("macbook 1tb storage")
    assert specs["storage_gb"] == 1024.0


def test_extract_picks_max_candidate():
    specs = extract_capacity_specs("available in 8gb or 16gb ram versions")
    assert specs["ram_gb"] == 16.0


def test_extract_no_specs_returns_none():
    specs = extract_capacity_specs("just a mouse")
    assert specs["ram_gb"] is None and specs["storage_gb"] is None


# --- domain keywords ---

def test_domain_keywords_detects_phone():
    assert choose_domain_keywords("iphone 15") != choose_domain_keywords("rolex watch")


def test_domain_keywords_fallback_generic():
    assert choose_domain_keywords("xyzzy unknown thing") != ""


def test_build_clean_web_query_appends_keywords():
    q = build_clean_web_query("iphone 15")
    assert q.startswith("iphone 15 ")


# --- intent payload dedup (anti-hallucination guard) ---

def test_intent_payload_deduplicates_products_case_insensitive():
    payload = CommerceIntentPayload(
        category=IntentCategory.SPECIFIC_SEARCH,
        is_chitchat=False,
        target_products=[
            {"product_name": "iPhone 15"},
            {"product_name": "iphone 15"},
            {"product_name": "Galaxy S24"},
        ],
    )
    names = [p.product_name for p in payload.target_products]
    assert len(names) == 2
    assert "Galaxy S24" in names


def test_intent_payload_rejects_nameless_entries():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        CommerceIntentPayload(
            category=IntentCategory.SPECIFIC_SEARCH,
            is_chitchat=False,
            target_products=[{"product_name": ""}, {"product_name": "Real"}],
        )


# --- retention policy ---

class _FakeIntent:
    def __init__(self, category):
        self.category = category


def test_closer_intent_detection():
    assert _is_closer_intent(_FakeIntent(IntentCategory.NEGOTIATION))
    assert _is_closer_intent(_FakeIntent(IntentCategory.OBJECTION))
    assert not _is_closer_intent(_FakeIntent(IntentCategory.SPECIFIC_SEARCH))
    assert not _is_closer_intent(None)


def test_retention_mode_resolution():
    assert _resolve_retention_mode(is_closer_intent=False, has_products=True) == RetentionMode.STANDARD_ADVISORY
    assert _resolve_retention_mode(is_closer_intent=True, has_products=False) == RetentionMode.FRAUD_PROTECT
    assert _resolve_retention_mode(is_closer_intent=True, has_products=True) == RetentionMode.VERIFIED_CLOSER


# --- memory events ---

def test_memory_event_roundtrip():
    ev = MemoryEvent.create("user", "  عايز لابتوب  ", "  ")
    assert ev.intent == "general"  # blank intent defaults
    raw = ev.to_json()
    restored = MemoryEvent.from_raw(raw)
    assert restored.content == "عايز لابتوب"  # stripped, Arabic preserved
    assert restored.role == "user"


def test_memory_event_from_bytes_and_garbage():
    assert MemoryEvent.from_raw(b"not json") is None
    ev = MemoryEvent.create("assistant", "hi", "search")
    assert MemoryEvent.from_raw(ev.to_json().encode("utf-8")).content == "hi"


# --- search constraints ---

def test_search_constraints_to_filters_omits_empty():
    c = SearchConstraints(clean_query="laptop")
    assert c.to_filters() == {}
    c2 = SearchConstraints(clean_query="laptop", price_max=1000.0, excluded_keywords=("used",))
    f = c2.to_filters()
    assert f["price_max"] == 1000.0 and f["excluded_keywords"] == ["used"]
    assert "price_min" not in f and "category" not in f


# --- sanitizers ---

def test_sanitize_free_text_normalizes():
    assert _sanitize_free_text("  Hello   WORLD \n") == "hello world"


def test_normalize_search_text_flattens_lines():
    assert _normalize_search_text("a\nb\tc") == "a b c"
    assert _normalize_search_text(None) == ""


# --- product dedup ---

def test_deduplicate_products_by_id():
    products = [{"id": 1, "name": "a"}, {"id": 1, "name": "a-dup"}, {"id": 2, "name": "b"}]
    unique = _deduplicate_products(products)
    assert len(unique) == 2


# --- internal commands ---

def test_parse_internal_command_add_by_id():
    cmd = _parse_internal_command(f"{InternalCommand.ADD_BY_ID.value}: 42")
    assert cmd is not None and cmd.argument == "42"


def test_parse_internal_command_rejects_garbage():
    assert _parse_internal_command("random text") is None
    assert _parse_internal_command(f"{InternalCommand.ADD_BY_ID.value}:") is not None
    # prefix without argument yields argument None but still parses
    cmd = _parse_internal_command(f"{InternalCommand.ADD_BY_ID.value}:")
    assert cmd.argument is None
