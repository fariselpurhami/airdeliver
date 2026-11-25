import asyncio,base64
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.image_hint_boundary import image_data_url
from tests.test_llm_execution_limits import service,completion
PNG=base64.b64encode(b'\x89PNG\r\n\x1a\n'+b'test').decode()

@pytest.mark.parametrize('value',['bad!','data:image/jpeg;base64,'+PNG,'AAAA',True,'A'*8_000_001],ids=['bad-base64','wrong-mime','bad-header','wrong-type','oversize'])
def test_bad_payload_is_rejected(value):
    with pytest.raises(ValueError):image_data_url(value)

@pytest.mark.asyncio
async def test_png_and_data_uri_are_not_mislabeled_as_jpeg():
    llm=service();llm._chat_completion=AsyncMock(return_value=completion('blue running shoes'))
    llm._perform_tavily_title_lookup=AsyncMock(return_value='maker shoes')
    result=await llm.analyze_product_image('data:image/png;base64,'+PNG)
    assert result=='blue running shoes maker'
    messages=llm._chat_completion.await_args.kwargs['messages']
    assert messages[1]['content'][1]['image_url']['url']=='data:image/png;base64,'+PNG

@pytest.mark.asyncio
@pytest.mark.parametrize('raw',[None,42,{'text':'fake'},'x'*257,'https://unsafe.example/x','<instructions>'])
async def test_untrusted_hint_shape_is_withheld_before_enrichment(raw):
    llm=service();llm._chat_completion=AsyncMock(return_value=completion(raw));llm._perform_tavily_title_lookup=AsyncMock()
    assert await llm.analyze_product_image(PNG)=='generic product'
    llm._perform_tavily_title_lookup.assert_not_awaited()

@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['error','cancel','timeout','malformed'])
async def test_optional_enrichment_error_keeps_bounded_hint_cancellation_propagates(mode):
    llm=service();llm._chat_completion=AsyncMock(return_value=completion('blue running shoes'))
    effect={'error':ConnectionError('private'),'cancel':asyncio.CancelledError(),'timeout':TimeoutError(),'malformed':None}[mode]
    llm._perform_tavily_title_lookup=AsyncMock(side_effect=effect,return_value={'bad':'shape'})
    if mode=='cancel':
        with pytest.raises(asyncio.CancelledError):await llm.analyze_product_image(PNG)
    else:assert await llm.analyze_product_image(PNG)=='blue running shoes'

@pytest.mark.asyncio
async def test_truncated_valid_hint_and_invalid_image_never_enter_search():
    llm=service();reply=completion('blue running shoes');reply.choices[0].finish_reason='length'
    llm._chat_completion=AsyncMock(return_value=reply);llm._perform_tavily_title_lookup=AsyncMock()
    assert await llm.analyze_product_image(PNG)=='generic product'
    llm._perform_tavily_title_lookup.assert_not_awaited()
    llm._chat_completion.reset_mock()
    assert await llm.analyze_product_image('not-an-image')=='generic product'
    llm._chat_completion.assert_not_awaited()

@pytest.mark.asyncio
@pytest.mark.parametrize('method',['analyze_visual_context','analyze_product_image'])
async def test_provider_outage_and_cancellation_keep_fail_closed_contract(method):
    llm=service();llm._chat_completion=AsyncMock(side_effect=ConnectionError('private'))
    assert await getattr(llm,method)(PNG) in {'generic product','Visual signal interrupted.'}
    llm._chat_completion=AsyncMock(side_effect=asyncio.CancelledError())
    with pytest.raises(asyncio.CancelledError):await getattr(llm,method)(PNG)

@pytest.mark.asyncio
async def test_disabled_enrichment_does_not_search_or_claim_identity():
    llm=service();llm._chat_completion=AsyncMock(return_value=completion('blue running shoes'))
    llm._perform_tavily_title_lookup=AsyncMock()
    assert await llm.analyze_product_image(PNG,enrich_with_search=False)=='blue running shoes'
    llm._perform_tavily_title_lookup.assert_not_awaited()
