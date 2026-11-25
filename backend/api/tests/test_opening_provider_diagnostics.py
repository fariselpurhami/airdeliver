import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import logging
import httpx
import pytest
from groq import RateLimitError, BadRequestError
from app.services.free_llm_service import FreeLLMService
from app.services.provider_budget import ProviderCooldownError
from app.services.shopping_copy import write_shopping_copy, ShoppingCopyError
from app.services.shopping_discovery import catalog_result
from tests.test_shopping_discovery_contract import row


def service():
    result=object.__new__(FreeLLMService);result.__init__();return result

@pytest.mark.asyncio
async def test_free_llm_cooldown_shared_across_instances_no_second_provider_call(caplog):
    response=httpx.Response(429,headers={'retry-after':'120'},request=httpx.Request('POST','http://offline.invalid'))
    create=AsyncMock(side_effect=RateLimitError('private secret source',response=response,body={'error':{'message':'private (TPM)'}}))
    first,second=service(),service()
    for instance in (first,second):
        instance._get_client=AsyncMock(return_value=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    with caplog.at_level(logging.WARNING):
        with pytest.raises(RateLimitError):await first._chat_completion(model='offline-opening-cooldown',messages=[{'content':'private'}],timeout_seconds=.03)
        with pytest.raises(ProviderCooldownError):await second._chat_completion(model='offline-opening-cooldown',messages=[{'content':'q'}],timeout_seconds=.03)
    assert create.await_count==1 and 'private' not in caplog.text and 'TPM' in caplog.text

@pytest.mark.asyncio
async def test_provider400_subcode_survives_actual_json_formatter_without_body(caplog):
    from app.core.logging_config import JsonFormatter
    response=httpx.Response(400,request=httpx.Request('POST','http://offline.invalid'))
    svc=service();create=AsyncMock(side_effect=BadRequestError('private schema output',response=response,body={'error':{'code':'json_validate_failed','message':'private failed generation'}}))
    svc._get_client=AsyncMock(return_value=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    with caplog.at_level(logging.WARNING):
        with pytest.raises(BadRequestError):await svc._chat_completion(model='offline-bad-schema',messages=[{'content':'q'}],timeout_seconds=.1)
    rendered='\n'.join(JsonFormatter().format(r) for r in caplog.records)
    assert 'json_validate_failed' in rendered and 'BadRequestError' in rendered
    assert 'private' not in rendered and create.await_count==1

@pytest.mark.asyncio
@pytest.mark.parametrize('repair_ok',[True,False])
async def test_one_field_claim_repair_never_bypasses_same_validator_or_review(repair_ok):
    card=catalog_result(row())
    bad=json.dumps({'text':'Compare the cards.','product_ids':[card.id],'claims':[{'product_id':card.id,'field':'name','value':'invented'}]})
    good=json.dumps({'text':'Compare the supplied catalog cards.','product_ids':[],'claims':[]})
    verdict=json.dumps(dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))
    infer=AsyncMock(side_effect=[bad,good if repair_ok else bad,verdict])
    if repair_ok:
        assert await write_shopping_copy(infer,'compare',[card],{},'catalog_results',1,{'sales_intent':'OPENING_INSIGHT'})=='Compare the supplied catalog cards.'
        assert infer.await_count==3
    else:
        with pytest.raises(ShoppingCopyError) as exc:await write_shopping_copy(infer,'compare',[card],{},'catalog_results',1,{'sales_intent':'OPENING_INSIGHT'})
        assert exc.value.stage=='writer_evidence' and infer.await_count==2

@pytest.mark.asyncio
async def test_actual_lifestyle_adapter_supplies_every_ten_card_to_reviewed_writer():
    svc=service();seen=[]
    async def infer(messages):
        payload=json.loads(messages[1]['content']);seen.append(payload)
        if 'catalog_evidence' in payload:return json.dumps({'text':'Explore the catalog.\n\nReview the supplied details before choosing.','product_ids':[],'claims':[]})
        return json.dumps(dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))
    svc.infer_sales_json=infer
    products=[]
    for i in range(10):
        p=row();p.id=i+1;products.append(p)
    result=await svc.generate_lifestyle_matrix(products,row_type='Personalized')
    assert len(result[0]['products'])==10 and len(seen[0]['catalog_evidence'])==10
    assert len(seen[1]['input']['catalog_evidence'])==10

@pytest.mark.asyncio
@pytest.mark.parametrize('review_supported',[True,False])
async def test_real_sdk_opening_repair_and_independent_review_over_local_http(review_supported):
    from groq import AsyncGroq
    requests=[]
    bodies=[
        {'text':'Inspect these cards.','product_ids':[1],'claims':[{'product_id':1,'field':'price','value':'invented'}]},
        {'text':'Explore the catalog selection.\n\nReview listed details before choosing.','product_ids':[],'claims':[]},
        dict(supported=review_supported,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True),
    ]
    async def handle(reader,writer):
        try:
            headers=await reader.readuntil(b'\r\n\r\n')
            size=int(next(line.split(b':',1)[1] for line in headers.split(b'\r\n') if line.lower().startswith(b'content-length:')))
            requests.append(json.loads(await reader.readexactly(size)))
            body=json.dumps({'id':'offline','object':'chat.completion','created':1,'model':'openai/gpt-oss-120b','choices':[{'index':0,'message':{'role':'assistant','content':json.dumps(bodies[len(requests)-1])},'finish_reason':'stop'}]}).encode()
            writer.write(f'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n'.encode()+body)
            await writer.drain()
        finally:
            writer.close();await writer.wait_closed()
    server=await asyncio.start_server(handle,'127.0.0.1',0)
    async with server:
        async with AsyncGroq(api_key='offline-no-credentials',max_retries=0,base_url=f'http://127.0.0.1:{server.sockets[0].getsockname()[1]}') as client:
            svc=service();svc._client=client;svc.models=SimpleNamespace(brain_model='openai/gpt-oss-120b')
            products=[]
            for identity in range(1,11):
                p=row();p.id=identity;products.append(p)
            if review_supported:
                assert len((await svc.generate_lifestyle_matrix(products))[0]['products'])==10
            else:
                with pytest.raises(ValueError,match='Opening copy withheld'):await svc.generate_lifestyle_matrix(products)
    assert len(requests)==3
    assert [r['response_format']['json_schema']['name'] for r in requests]==['ShoppingDraft','ShoppingDraft','GroundingReview']
    assert all(r['response_format']['json_schema']['strict'] is True for r in requests)
    assert len(json.loads(requests[2]['messages'][1]['content'])['input']['catalog_evidence'])==10
