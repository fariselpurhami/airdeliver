"""The writer voice contract asks for a person, not a form (user voice note, 8:37 PM: rebuild the reply so it
sounds like a sharp, tactful friend, not an AI). Contract text only; the real effect needs real drafts (n labeled in the PR).
"""
from app.services.conversation.compact_copy_contracts import TASK

def test_voice_is_a_person_in_first_person_with_plain_sentences():
    low=TASK.casefold()
    for phrase in ('first person','short plain sentences','one flowing reply'):
        assert phrase in low,phrase

def test_robotic_tells_are_named_so_the_model_avoids_them():
    low=TASK.casefold()
    for tell in ("catalog","specifications","we can't confirm","the information provided"):
        assert tell in low,tell
    assert 'bullet' in low and 'label: value' in low

def test_one_question_at_most_and_the_absence_is_said_in_own_words():
    low=TASK.casefold()
    assert 'at most one question' in low
    assert "i don't have" in low

def test_existing_guards_are_kept():
    for phrase in ('specific unknown','never offer holds','Text never shows product IDs','in-stock wording needs a stock_status claim','four_phase','allow decline'):
        assert phrase in TASK,phrase
