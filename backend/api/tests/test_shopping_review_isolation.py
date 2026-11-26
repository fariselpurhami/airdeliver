"""Exact captured review decisions replay without provider calls."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.sales_response_service import SalesResponseService
from app.services.shopping_discovery import ShoppingBrief,catalog_result
from app.services.shopping_copy import ShoppingDraft,validate_draft
from tests.test_sales_response_service import request

ROWS=json.loads((Path(__file__).resolve().parents[1]/'fixtures/shopping_review_isolation_v1.json').read_text())['cases']

@pytest.mark.asyncio
@pytest.mark.parametrize('row',ROWS,ids=[r['case'] for r in ROWS])
async def test_evidence_valid_semantic_contrasts_reach_real_review_boundary(row):
 cards=tuple(catalog_result(SimpleNamespace(**p)) for p in row['products'])
 draft=ShoppingDraft.model_validate(row['controlled_writer'])
 # These deliberate semantic errors pass structural equality, proving why the
 # independent reviewer remains mandatory rather than calling shape grounding.
 validate_draft(draft,list(cards))
 infer=AsyncMock(side_effect=[json.dumps(row['controlled_writer']),json.dumps(row['actual_review'])])
 result=await SalesResponseService(infer,provider_ready=True,timeout=1).respond(request(message=row['question'],products=cards,brief=ShoppingBrief(),evidence={'shopping_task':'consultation'}))
 assert infer.await_count==2
 assert result.response_kind==row['expected_kind']
 payload=json.loads(infer.await_args.args[0][1]['content'])
 assert payload['input']['customer_message']==row['question']
 assert payload['draft']==draft.model_dump()
 if row['case']=='019':
  assert all(row['actual_review'].values()) and result.text==draft.text
 else:
  assert not all(row['actual_review'].values()) and result.products==[]
