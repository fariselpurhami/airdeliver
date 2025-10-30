# apps/api/tests/test_ai_ordering.py

from app.services.ai_ordering_service import ai_ordering_service

def test_parse_intent_add_to_cart_with_quantity():
    message = "I want to buy 2 iphone cases"
    result = ai_ordering_service._parse_intent(message)
    assert result["intent"] == "ADD_TO_CART"
    assert result["quantity"] == 2
    assert result["product_name"] == "iphone case"

def test_parse_intent_add_to_cart_no_quantity():
    message = "add a cable to my order"
    result = ai_ordering_service._parse_intent(message)
    assert result["intent"] == "ADD_TO_CART"
    assert result["quantity"] == 1
    assert result["product_name"] == "cable"

def test_parse_intent_unknown():
    message = "what is the weather today"
    result = ai_ordering_service._parse_intent(message)
    assert result["intent"] == "UNKNOWN"
