"""Replay final captured wire objects through real orchestration, no network."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.sales_response_service import SalesResponseService
from app.services.shopping_discovery import ShoppingBrief,catalog_result
from tests.test_sales_response_service import request

ROWS=json.loads((Path(__file__).resolve().parents[1]/'fixtures/shopping_heldout_v2.json').read_text())['cases']

@pytest.mark.asyncio
@pytest.mark.parametrize('case',list(ROWS))
async def test_captured_active_writer_and_review_preserve_exact_boundary(case,caplog):
 row=ROWS[case]
 infer=AsyncMock(side_effect=[json.dumps(c) for c in row['completions']])
 cards=tuple(catalog_result(SimpleNamespace(**p)) for p in row['products'])
 result=await SalesResponseService(infer,provider_ready=True,timeout=1).respond(request(message=row['question'],products=cards,brief=ShoppingBrief(),evidence={'shopping_task':'comparison' if case=='008' else 'consultation'}))
 assert result.response_kind==row['expected_response_kind']
 assert infer.await_count==len(row['completions'])
 if 'first_gate' in row:
  assert row['first_gate'] in caplog.text
  assert result.products==[]
 else:
  assert result.text==row['completions'][0]['text']
  assert len(result.products)==2
 assert row['synthetic'] and len(row['source_sha'])==40
