"""The slot writer call must run at low reasoning like the other writer calls.
Real Groq (n=1, hard-01, 5:50 AM): the slot call used default reasoning and failed with "max completion tokens reached before generating a valid document"."""
import inspect
from pathlib import Path


def test_slot_draft_gets_low_reasoning_in_both_provider_paths():
    root = Path(__file__).resolve().parents[1] / 'app' / 'services'
    llm = (root / 'conversation' / 'free_llm_service.py').read_text()
    budget = (root / 'provider_capacity' / 'provider_budget.py').read_text()
    assert "'ShoppingDraft','SlotDraft'}" in llm
    assert "'SlotDraft':640" in budget and "'ShoppingDraft','SlotDraft','GroundingReview" in budget


def test_slot_draft_schema_is_named_slotdraft():
    from app.services.conversation.slot_copy import SlotDraft
    assert SlotDraft.__name__ == 'SlotDraft'
