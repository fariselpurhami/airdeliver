import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.query_rewrite import review_query

@pytest.mark.asyncio
@pytest.mark.parametrize('accepted',[True,False])
async def test_customer_only_expansion_is_reviewed_and_literal_target_preserved(accepted):
    infer=AsyncMock(return_value=json.dumps({'preserves_request':accepted,'no_invented_identity':True,'preserves_constraints':True}))
    query='headphones lightweight travel'
    result=await review_query(infer,'headphones for travel',query,[SimpleNamespace(product_name='headphones')])
    assert result==(query if accepted else None)
    assert infer.await_count==1

@pytest.mark.asyncio
async def test_rewrite_cannot_erase_literal_model_or_smuggle_url():
    infer=AsyncMock()
    assert await review_query(infer,'Phone17','Phone20',[SimpleNamespace(product_name='Phone17')]) is None
    assert await review_query(infer,'phone','https://evil.invalid',[]) is None
    infer.assert_not_awaited()
