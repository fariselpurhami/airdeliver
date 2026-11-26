"""Bounded synthetic evidence preserves failures and never self-accepts quality."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]

def test_synthetic_receipt_preserves_bounded_failures_and_scope():
 receipt=json.loads((ROOT/'docs/verification/shopping-evaluation-receipt-v1.json').read_text())
 assert receipt['synthetic_only'] is True
 assert receipt['owner_quality_accepted'] is False
 assert receipt['active_experimental_caller'] is False
 assert receipt['attempts_used']==48<receipt['attempt_limit']==50
 assert receipt['unused_attempts']==2 and receipt['evaluation_stopped'] is True
 rows={row['case']:row for row in receipt['cases']}
 assert rows['037']['brief_verified_in_receipt'] is True
 assert rows['037']['grounded_brief']['budget_max']=='80'
 assert rows['037']['grounded_brief']['budget_currency']=='USD'
 assert rows['037']['result']['response_kind']=='catalog_results'
 assert rows['038']['result']['response_kind']=='system_notice'
 assert rows['038']['result']['selected_ids']==[]
 assert rows['035']['result']['response_kind']=='system_notice'
 assert all(len(row['source_sha'])==40 and row['dirty_source'] is False for row in rows.values())
 assert all('Not full HTTP' in row['scope'] for row in rows.values())


def test_new_free_development_receipt_preserves_historical_run_and_unknown_usage():
 r=json.loads((ROOT/'docs/verification/shopping-development-receipt-v2.json').read_text())
 assert r['historical_receipt_unchanged'] is True and r['synthetic_only'] is True
 assert not r['owner_quality_accepted'] and not r['active_experimental_caller']
 assert r['requests']==6 and r['measured_tokens']==14255
 assert r['requests_with_unknown_usage']==1
 assert r['conservative_total_tokens']==r['measured_tokens']+r['conservative_unknown_token_reserve']
 assert all(c['result']['response_kind']=='system_notice' for c in r['cases'])
 assert all(len(c['source_sha'])==40 for c in r['cases'])
 assert [c['case'] for c in r['cases'] if c['dirty_source']]==['007']
 assert 'Only006receipt' in r['cases'][-1]['dirty_scope']
 assert r['account_plan_verified'] is False
