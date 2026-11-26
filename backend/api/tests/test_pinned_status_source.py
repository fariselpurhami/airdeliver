"""Integrity binding for separately reviewed source snapshots, synthetic only."""
from dataclasses import replace
from datetime import timedelta
import hashlib,json
from unittest.mock import AsyncMock
import pytest
from tests.test_status_claim_binding import NOW,QUOTE,registry
from tests.test_reviewed_product_status import D,V
from app.services.research.pinned_status_source import StatusSourcePin,bind_pinned_status_source
from app.services.research.reviewed_product_status import reviewed_product_status
URL='https://news.maker.example/x'

def pin(**changes):
 data=dict(final_url=URL,publisher_key='maker',content_sha256=hashlib.sha256(QUOTE.encode()).hexdigest(),published_at=NOW-timedelta(hours=2),region='US',exact_models=('maker:x',))
 data.update(changes);return StatusSourcePin(**data)

def test_exact_reviewed_snapshot_pin_maps_only_application_owned_metadata():
 row=bind_pinned_status_source(final_url=URL,text=QUOTE,observed_at=NOW,pin=pin(),registry=registry())
 assert row.text==QUOTE and row.final_url==URL
 assert row.exact_models==('maker:x',) and row.region=='US'
 assert row.published_at==NOW-timedelta(hours=2)

@pytest.mark.parametrize('change',[
 {'text':QUOTE+' changed'}, {'final_url':URL+'?changed=1'},
 {'pin':pin(publisher_key='another')},{'pin':pin(content_sha256='0'*64)},
 {'pin':pin(published_at=NOW+timedelta(hours=1))},
 {'pin':pin(published_at=NOW.replace(tzinfo=None))},
 {'pin':pin(exact_models=())},{'pin':pin(region='')},
 {'pin':pin(content_sha256='invalid')},{'observed_at':NOW.replace(tzinfo=None)},
])
def test_mutated_unbound_or_malformed_snapshot_never_returns_verified_input(change):
 args=dict(final_url=URL,text=QUOTE,observed_at=NOW,pin=pin(),registry=registry());args.update(change)
 with pytest.raises(ValueError):bind_pinned_status_source(**args)

@pytest.mark.asyncio
async def test_exact_snapshot_adapter_to_full_review_and_temporal_resolution():
 source=bind_pinned_status_source(final_url=URL,text=QUOTE,observed_at=NOW,pin=pin(),registry=registry())
 infer=AsyncMock(side_effect=[json.dumps(D),json.dumps(V)])
 result=await reviewed_product_status(infer,'maker:x',[source],registry(),now=NOW,region='US',max_age=timedelta(hours=6),timeout=1)
 assert result.state=='released' and result.merchant_stock=='unverified'
 assert infer.await_count==2

@pytest.mark.asyncio
async def test_changed_snapshot_cannot_reach_status_model():
 infer=AsyncMock()
 with pytest.raises(ValueError):
  source=bind_pinned_status_source(final_url=URL,text=QUOTE+' extra',observed_at=NOW,pin=pin(),registry=registry())
  await reviewed_product_status(infer,'maker:x',[source],registry(),now=NOW,region='US',max_age=timedelta(hours=6),timeout=1)
 infer.assert_not_awaited()
