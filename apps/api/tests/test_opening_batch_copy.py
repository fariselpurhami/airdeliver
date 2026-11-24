import json,asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.opening_batch_copy import write_batch,RULES,REVIEW
from app.services.shopping_copy import ShoppingCopyError
from tests.test_shopping_discovery_contract import row


def body(groups):
    return {label:{'introduction':'Explore these catalog designs.','insight':'Compare the listed material before choosing.','product_ids':[],'claims':[]} for label,_ in groups}

@pytest.mark.asyncio
@pytest.mark.parametrize('failure',[None,'ids','numeric','undeclared','review','paragraph','provider'])
async def test_batch_actual_writer_validator_and_independent_reviewer(failure):
    groups=[(name,[row()]) for name in ('Personalized','Bestsellers','Trending','Deals')]
    draft=body(groups)
    if failure=='ids':draft['other']=draft.pop('Bestsellers')
    if failure=='numeric':draft['Personalized']['introduction']='Explore999designs.'
    if failure=='undeclared':draft['Personalized'].update(product_ids=[1])
    if failure=='paragraph':draft['Personalized']['insight']='Two\n\nparagraphs'
    verdict={k:True for k in ('supported','all_product_mentions_declared','no_unsupported_commercial_claims','fulfills_discovery_task')}
    if failure=='review':verdict['supported']=False
    infer=AsyncMock(side_effect=[json.dumps(draft),json.dumps(verdict)])
    if failure=='provider':infer.side_effect=TimeoutError()
    llm=SimpleNamespace(infer_sales_json=infer)
    if failure:
        with pytest.raises(ShoppingCopyError) as caught:await write_batch(llm,groups)
        expected={'ids':'writer_schema','numeric':'writer_evidence','undeclared':'writer_evidence','review':'review_verdict','paragraph':'writer_format','provider':'writer_provider'}
        assert caught.value.stage==expected[failure]
        assert 'catalog designs' not in caught.value.reason
        assert infer.await_count==2 if failure=='review' else infer.await_count==1
    else:
        result=await write_batch(llm,groups)
        assert len(result)==4 and infer.await_count==2
        payload=json.loads(infer.await_args_list[0].args[0][1]['content'])
        assert len(payload['rows'])==4 and all(len(x['cards'])==1 for x in payload['rows'])
        assert len(RULES)<2000 and len(REVIEW)<1200

@pytest.mark.asyncio
async def test_four_ten_card_rows_all_reach_writer_and_review_once():
    groups=[]
    for label in ('Personalized','Bestsellers','Trending','Deals'):
        products=[]
        for identity in range(1,11):
            p=row();p.id=identity;products.append(p)
        groups.append((label,products))
    drafts=body(groups);seen=[]
    async def infer(messages):
        payload=json.loads(messages[1]['content']);seen.append(payload)
        if 'rows' in payload:return json.dumps(drafts)
        return json.dumps(dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True))
    await write_batch(SimpleNamespace(infer_sales_json=infer),groups)
    assert len(seen)==2 and all(len(r['cards'])==10 for r in seen[0]['rows'])
    assert seen[1]['input']==seen[0]

@pytest.mark.asyncio
async def test_batch_shares_admission_with_chat_and_logs_only_numeric_usage(caplog):
    import logging
    from app.services.free_llm_service import FreeLLMService
    from app.services.provider_budget import complete
    from app.core.logging_config import JsonFormatter
    svc=object.__new__(FreeLLMService);svc.__init__();active=peak=0
    async def create(**kwargs):
        nonlocal active,peak
        active+=1;peak=max(peak,active)
        try:
            await asyncio.sleep(.01)
            return SimpleNamespace(usage=SimpleNamespace(prompt_tokens=123,completion_tokens=12,total_tokens=135),choices=[SimpleNamespace(message=SimpleNamespace(content='{}'))])
        finally:active-=1
    svc._get_client=AsyncMock(return_value=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    with caplog.at_level(logging.INFO):
        await asyncio.gather(svc._chat_completion(model='offline-shared-budget',messages=[{'role':'user','content':'private-input'}],timeout_seconds=1),
            complete(create,model='offline-shared-budget',messages=[{'role':'user','content':'private-other'}],response_format={},timeout=1,stage='GroundingReview'))
    assert peak==1
    rendered='\n'.join(JsonFormatter().format(r) for r in caplog.records)
    assert 'prompt_tokens' in rendered and '123' in rendered and '135' in rendered
    assert 'private-input' not in rendered and 'private-other' not in rendered

@pytest.mark.asyncio
async def test_native_batch_adapter_uses_bounded_output_and_strict_schemas():
    from app.services.free_llm_service import FreeLLMService
    svc=object.__new__(FreeLLMService);svc.__init__();svc.models=SimpleNamespace(brain_model='openai/gpt-oss-120b')
    groups=[('Personalized',[row()])];draft=body(groups);calls=[]
    async def create(**kwargs):
        calls.append(kwargs)
        content=draft if len(calls)==1 else dict(supported=True,all_product_mentions_declared=True,no_unsupported_commercial_claims=True,fulfills_discovery_task=True)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(content)))])
    svc._get_client=AsyncMock(return_value=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    await svc.generate_opening_batch(groups)
    assert [c['max_tokens'] for c in calls]==[1800,256]
    assert [c['response_format']['json_schema']['name'] for c in calls]==['OpeningBatch','GroundingReview']
    assert all(c['response_format']['json_schema']['strict'] and c['reasoning_effort']=='low' for c in calls)

@pytest.mark.asyncio
async def test_opening_safe_reason_is_visible_without_model_text(caplog):
    from app.services.ai_nlu_service import StructuredLog
    import logging
    with caplog.at_level(logging.WARNING):
        StructuredLog.warning('opening_batch_withheld',stage='writer_format',reason='opening_paragraph_contract',raw_model_text='private-model-text')
    assert 'opening_paragraph_contract' in caplog.text and 'private-model-text' not in caplog.text

@pytest.mark.asyncio
@pytest.mark.parametrize('labels',[('Personalized',),('Personalized','Deals'),('Personalized','Bestsellers','Trending','Deals')])
async def test_native_schema_requires_exact_active_keys_and_bounded_drafts(labels):
    from app.services.opening_batch_copy import opening_schema
    from app.services.structured_output import response_format
    schema=response_format('openai/gpt-oss-120b',opening_schema(labels))['json_schema']['schema']
    assert set(schema['required'])==set(labels) and schema['additionalProperties'] is False
    draft=schema['$defs']['OpeningParagraphDraft']
    assert set(draft['required'])=={'introduction','insight','product_ids','claims'}
    assert draft['properties']['introduction']['maxLength']==350
    assert draft['properties']['claims']['maxItems']==10

@pytest.mark.asyncio
@pytest.mark.parametrize('invalid',['missing','extra','duplicate'])
async def test_partial_or_duplicate_identities_never_reach_review(invalid):
    groups=[(name,[row()]) for name in ('Personalized','Bestsellers','Trending','Deals')]
    draft=body(groups)
    if invalid=='missing':draft.pop('Deals')
    if invalid=='extra':draft['other']=draft['Deals']
    raw=json.dumps(draft)
    if invalid=='duplicate':raw=raw[:-1]+',"Deals":'+json.dumps(draft['Deals'])+'}'
    infer=AsyncMock(return_value=raw)
    with pytest.raises(ShoppingCopyError) as caught:await write_batch(SimpleNamespace(infer_sales_json=infer),groups)
    assert caught.value.stage=='writer_schema' and infer.await_count==1

@pytest.mark.asyncio
async def test_length_finish_reason_rejected_even_for_valid_partial_json():
    from app.services.free_llm_service import FreeLLMService,StructuredOutputError
    from app.services.opening_batch_copy import opening_schema
    svc=object.__new__(FreeLLMService);svc.__init__();svc.models=SimpleNamespace(brain_model='openai/gpt-oss-120b')
    svc._chat_completion=AsyncMock(return_value=SimpleNamespace(choices=[SimpleNamespace(finish_reason='length',message=SimpleNamespace(content=json.dumps(body([('Personalized',[row()])]))))]))
    with pytest.raises(StructuredOutputError):
        await svc.infer_sales_json([{'role':'user','content':'opening'}],response_schema=opening_schema(['Personalized']))
    assert svc._chat_completion.await_args.kwargs['max_tokens']==1800
