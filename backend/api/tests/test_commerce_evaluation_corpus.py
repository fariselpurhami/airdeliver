import json
from pathlib import Path
from collections import Counter
from evaluation.build_cases import build
from evaluation.run_contracts import run


def test_versioned_corpus_is_reproducible_and_coverage_honest():
    cases=build()
    assert json.loads((Path(__file__).parents[1]/'evaluation/commerce_cases_v1.json').read_text())==cases
    assert len(cases)==len({c['id'] for c in cases})==360
    assert len({c['category'] for c in cases})==7
    assert Counter(c['language'] for c in cases)=={'en':120,'ar':120,'mixed':120}
    assert len({c['template_family'] for c in cases})==20
    assert any(len(c['turns'])>1 for c in cases)
    assert all(c['quality_status']=='unmeasured' for c in cases)
    report=run(cases)
    assert report['status_counts']=={'passed':324,'blocked_modality':36}
    assert report['provider_calls']==0
    assert all(v is None for v in report['quality_scores'].values())
    assert report['scope']=='offline_card_contract_only'


def test_contract_runner_detects_eligibility_regression_without_inflating_quality():
    case=build()[0]
    case['expected_eligible_ids']=[999]
    result=run([case])
    assert result['status_counts']=={'failed':1}
    assert result['quality_scores']['grounding'] is None
