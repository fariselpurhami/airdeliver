import json
from types import SimpleNamespace
import httpx
import pytest
from groq import AsyncGroq
from app.services.provider_response_observation import numeric_headers,observed_create,observe_headers
from app.services.shared_provider_admission import Reservation,shared_provider_slot,SharedProviderBudgetError
from tests.test_cart_persistence_outcomes import real_cache

def test_header_units_and_untrusted_values_are_bounded():
 assert numeric_headers({'x-ratelimit-limit-requests':'1000','x-ratelimit-remaining-tokens':'300','x-ratelimit-reset-tokens':'1m2s','authorization':'secret'})=={'remaining-tokens':300,'reset-tokens':62}
 assert numeric_headers({'x-ratelimit-remaining-tokens':'-1','x-ratelimit-reset-tokens':'PRIVATE'})=={}
@pytest.mark.asyncio
async def test_real_sdk_raw_headers_over_offline_http_transport():
 async def handler(request):
  return httpx.Response(200,headers={'x-ratelimit-remaining-tokens':'100','x-ratelimit-reset-tokens':'60s'},json={'id':'offline','object':'chat.completion','created':1,'model':'offline','choices':[{'index':0,'message':{'role':'assistant','content':'{}'},'finish_reason':'stop'}],'usage':{'prompt_tokens':4,'completion_tokens':2,'total_tokens':6}})
 async with AsyncGroq(api_key='offline-no-credential',max_retries=0,http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler))) as client:
  r=Reservation(None,[],None,None)
  response=await observed_create(client.chat.completions.create,r,model='offline',messages=[])
  r.observe(response)
  assert r.actual==6 and numeric_headers(r.headers)['remaining-tokens']==100
@pytest.mark.asyncio
async def test_out_of_order_headers_only_reduce_and_real_redis_guard_obeys(real_cache):
 cache,_=real_cache;prefix='airdeliver:provider:v1:{offline-observed}'
 r=Reservation(cache.client,[prefix+':lock',prefix+':usage',prefix+':cooldown'],'owner','owner:200')
 for remaining in ('1000','300','900'):
  r.headers={'x-ratelimit-remaining-tokens':remaining,'x-ratelimit-reset-tokens':'60s'};await observe_headers(r)
 assert await cache.client.get(prefix+':observed_tokens')=='300'
 # Actual model ledger key, not a separate unused test guard.
 async with shared_provider_slot('offline-observed-model',[],{},1,client=cache.client,limit=5000) as actual:
  actual.headers={'x-ratelimit-remaining-tokens':'0','x-ratelimit-reset-tokens':'60s'}
 with pytest.raises(SharedProviderBudgetError):
  async with shared_provider_slot('offline-observed-model',[],{},1,client=cache.client,limit=5000):pytest.fail('header bound')
@pytest.mark.asyncio
async def test_daily_request_zero_imposes_shared_cooldown_not_rpm_guess(real_cache):
 cache,_=real_cache;prefix='airdeliver:provider:v1:{offline-daily}'
 r=Reservation(cache.client,[prefix+':lock',prefix+':usage',prefix+':cooldown'],'owner','owner:200')
 r.headers={'x-ratelimit-remaining-requests':'0','x-ratelimit-reset-requests':'1h'};await observe_headers(r)
 assert await cache.client.pttl(prefix+':cooldown')>3500000
