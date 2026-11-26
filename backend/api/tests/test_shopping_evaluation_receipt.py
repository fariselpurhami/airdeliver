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
