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

@pytest.mark.asyncio
async def test_preflight_never_uses_reviewed_binder(monkeypatch):
 # Import the module explicitly because the function shares its name.
 import importlib
 service=importlib.import_module('app.services.research.reviewed_product_status')
 original=service.bind_status_claim
 calls=[]
 def checked(*args,**kwargs):
  calls.append(infer.await_count)
  return original(*args,**kwargs)
 monkeypatch.setattr(service,'bind_status_claim',checked)
 infer=AsyncMock(side_effect=[json.dumps(D),json.dumps(V)])
 await service.reviewed_product_status(infer,'maker:x',[source()],registry(),now=NOW,region='US',max_age=timedelta(hours=6),timeout=1)
 assert calls==[2], 'reviewed binding is allowed only after independent review'

@pytest.mark.asyncio
@pytest.mark.parametrize('bad_clock',['naive','age'])
async def test_invalid_clock_rejected_before_any_model_call(bad_clock):
 infer=AsyncMock(side_effect=[json.dumps(D),json.dumps(V)])
 now=NOW.replace(tzinfo=None) if bad_clock=='naive' else NOW
 age=timedelta(0) if bad_clock=='age' else timedelta(hours=6)
 with pytest.raises(ValueError,match='invalid_status_clock'):
  await reviewed_product_status(infer,'maker:x',[source()],registry(),now=now,region='US',max_age=age,timeout=1)
 infer.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize('stage',[0,1])
async def test_status_provider_outage_never_returns_partial_evidence(stage):
 failures=[RuntimeError('synthetic outage')] if stage==0 else [json.dumps(D),RuntimeError('synthetic outage')]
 infer=AsyncMock(side_effect=failures)
 with pytest.raises(RuntimeError,match='synthetic outage'):
  await reviewed_product_status(infer,'maker:x',[source()],registry(),now=NOW,region='US',max_age=timedelta(hours=6),timeout=1)
 assert infer.await_count==stage+1

@pytest.mark.asyncio
@pytest.mark.parametrize('stage',[0,1])
async def test_shared_status_deadline_cancels_stage_without_returning_draft(stage):
 import anyio
 calls=[]
 async def infer(*args,**kwargs):
  calls.append(args)
  if len(calls)<=stage:return json.dumps(D)
  await anyio.sleep(1)
 with pytest.raises(TimeoutError):
  await reviewed_product_status(infer,'maker:x',[source()],registry(),now=NOW,region='US',max_age=timedelta(hours=6),timeout=0.01)
 assert len(calls)==stage+1

@pytest.mark.asyncio
@pytest.mark.parametrize('changes',[
 {'observed_at':NOW.replace(tzinfo=None)},
 {'published_at':NOW.replace(tzinfo=None)},
 {'region':''},
 {'exact_models':()},
 {'exact_models':('maker:x','maker:x')},
 {'exact_models':['maker:x']},
 {'text':None},
])
async def test_malformed_verified_adapter_metadata_rejected_before_inference(changes):
 from dataclasses import replace
 infer=AsyncMock(side_effect=[json.dumps(D),json.dumps(V)])
 with pytest.raises(ValueError,match='verified_metadata_required'):
  await reviewed_product_status(infer,'maker:x',[replace(source(),**changes)],registry(),now=NOW,region='US',max_age=timedelta(hours=6),timeout=1)
 infer.assert_not_awaited()
