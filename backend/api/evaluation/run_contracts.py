"""Offline contract runner, never calls a model, provider, browser or live store.

Reports only the boundary it actually executes: catalog card eligibility and
budget filtering. Natural-language intent, semantic usefulness, persuasion,
language quality, end-to-end latency and modality recognition stay unmeasured.
"""
import argparse
import json
import math
import time
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from app.services.shopping_discovery import ShoppingBrief, catalog_result

ROOT=Path(__file__).parent


def run(cases):
    results=[]
    durations=[]
    for case in cases:
        if case['modality']!='text':
            results.append(dict(id=case['id'],status='blocked_modality',reason=case['modality_status']))
            continue
        started=time.perf_counter()
        maximum=case['contract_budget_max_usd']
        brief=ShoppingBrief(budget_max=maximum,budget_currency='USD' if maximum else None)
        cards=[catalog_result(SimpleNamespace(**row)) for row in case['fixture_products']]
        actual=[c.id for c in cards if c is not None and c.evidence_kind=='local_catalog' and c.stock_status=='local_in_stock' and c.price is not None and brief.permits(c)]
        elapsed=(time.perf_counter()-started)*1000;durations.append(elapsed)
        passed=actual==case['expected_eligible_ids']
        results.append(dict(id=case['id'],status='passed' if passed else 'failed',actual_ids=actual,expected_ids=case['expected_eligible_ids'],contract_latency_ms=elapsed,
            measured=['catalog_card_eligibility','explicit_preparsed_budget_filter'],
            unmeasured=['router','search_recall','model_grounding','transaction_safety','usefulness','persuasion','language','end_to_end_latency']))
    ordered=sorted(durations)
    def percentile(p):return ordered[max(0,math.ceil(len(ordered)*p)-1)] if ordered else None
    return dict(schema_version=1,scope='offline_card_contract_only',provider_calls=0,
        case_count=len(cases),status_counts=dict(Counter(r['status'] for r in results)),
        contract_latency_ms=dict(p50=percentile(.5),p95=percentile(.95)),
        quality_scores={key:None for key in ['grounding','transaction_safety','usefulness','persuasion','language','end_to_end_latency','image_recognition','audio_recognition']},
        warning='Contract passes do not measure real model quality, routing, retrieval or modality execution. Repeated template variants are not independent samples.',results=results)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    result=run(json.loads((ROOT/'commerce_cases_v1.json').read_text()))
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='results'},indent=2))
    raise SystemExit(1 if result['status_counts'].get('failed') else 0)
