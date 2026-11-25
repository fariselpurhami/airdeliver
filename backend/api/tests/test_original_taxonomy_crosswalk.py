"""Original categories stay accounted for without inventing semantic parity."""
import json
from pathlib import Path
from typing import get_args
from app.services.ai_nlu_service import IntentCategory
from app.services.neural_core_service import RouterDecision

ROOT=Path(__file__).resolve().parents[3]

def test_every_original_category_has_a_valid_current_contract_and_explicit_limits():
    data=json.loads((ROOT/'docs/verification/original-taxonomy-crosswalk-v1.json').read_text())
    assert set(data['categories'])=={category.value for category in IntentCategory}
    intents=set(get_args(RouterDecision.model_fields['intent'].annotation))
    tasks=set(get_args(RouterDecision.model_fields['shopping_task'].annotation))
    for original,row in data['categories'].items():
        assert row['intent'] in intents,original
        assert set(row.get('alternate_intents',[]))<=intents
        assert set(row['tasks'])<=tasks
        assert row['boundary']
    assert data['whole_group_closed'] is False
    assert data['still_open'] and data['intentional_exclusions']
    assert 'Five original labels restored as tone-only metadata' in data['fields']['sentiment']
    assert 'Literal current customer name' in data['fields']['competitor_mentioned']
