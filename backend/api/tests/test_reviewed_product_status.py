"""Controlled status extraction/review/resolution, no web or real model calls."""
import json
from datetime import timedelta
from unittest.mock import AsyncMock
import pytest
from tests.test_status_claim_binding import source,registry,NOW,QUOTE
from app.services.research.reviewed_product_status import reviewed_product_status
D={'claims':[{'source':0,'model_key':'maker:x','assertion':'released','effective_iso':'2026-11-25T20:00:00+00:00','quote':QUOTE}]}
V={'exact_model':True,'quote_entails_status':True,'temporal_region_correct':True,'no_stock_inference':True}

@pytest.mark.asyncio
async def test_status_service_runs_independent_full_review_then_resolves():
 infer=AsyncMock(side_effect=[json.dumps(D),json.dumps(V)])
 result=await reviewed_product_status(infer,'maker:x',[source()],registry(),now=NOW,region='US',max_age=timedelta(hours=6),timeout=1)
 assert result.state=='released' and result.merchant_stock=='unverified'
 assert infer.await_count==2
 payload=json.loads(infer.await_args_list[1].args[0][1]['content'])
 assert payload['draft']==D and payload['sources'][0]['published_at']==source().published_at.isoformat()

@pytest.mark.asyncio
@pytest.mark.parametrize('field',list(V))
async def test_every_negative_status_review_fails_closed(field):
 infer=AsyncMock(side_effect=[json.dumps(D),json.dumps({**V,field:False})])
 with pytest.raises(ValueError,match='status_review_rejected'):
  await reviewed_product_status(infer,'maker:x',[source()],registry(),now=NOW,region='US',max_age=timedelta(hours=6),timeout=1)
 assert infer.await_count==2

@pytest.mark.asyncio
async def test_forged_quote_fails_before_review():
 d=json.loads(json.dumps(D));d['claims'][0]['quote']='Unrelated 2026-11-25T20:00:00+00:00'
 infer=AsyncMock(return_value=json.dumps(d))
 with pytest.raises(ValueError,match='unsupported_status_quote'):
  await reviewed_product_status(infer,'maker:x',[source()],registry(),now=NOW,region='US',max_age=timedelta(hours=6),timeout=1)
 assert infer.await_count==1

@pytest.mark.asyncio
async def test_empty_verified_sources_do_not_call_model_or_imply_nonexistence():
 infer=AsyncMock()
 result=await reviewed_product_status(infer,'maker:x',[],registry(),now=NOW,region='US',max_age=timedelta(hours=6),timeout=1)
 assert result.state=='unverified';infer.assert_not_awaited()

@pytest.mark.asyncio
async def test_cancellation_propagates_without_second_call():
 import asyncio
 infer=AsyncMock(side_effect=asyncio.CancelledError())
 with pytest.raises(asyncio.CancelledError):
  await reviewed_product_status(infer,'maker:x',[source()],registry(),now=NOW,region='US',max_age=timedelta(hours=6),timeout=1)
 assert infer.await_count==1
