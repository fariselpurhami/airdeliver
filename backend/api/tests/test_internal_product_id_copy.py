"""Structured IDs are routing metadata, never shopper-facing prose."""
import pytest
from app.services.shopping_copy import ShoppingDraft,validate_draft
from app.services.shopping_discovery import catalog_result
from tests.test_shopping_discovery_contract import row

@pytest.mark.parametrize('text',['Studio Headphones (ID 1).','Studio Headphones, product ID: 1.','Studio Headphones (ID\u202f1).'])
def test_internal_id_cannot_be_laundered_through_valid_name_claim(text):
 item=row();item.name='Studio Headphones 1';card=catalog_result(item)
 draft=ShoppingDraft(text=text,product_ids=[card.id],claims=[{'product_id':card.id,'field':'name','value':card.name}])
 with pytest.raises(ValueError,match='internal_product_id_in_copy'):validate_draft(draft,[card])


def test_model_name_digits_without_id_label_are_not_internal_id():
 item=row();item.name='Studio Headphones 1';card=catalog_result(item)
 draft=ShoppingDraft(text=card.name+' is listed.',product_ids=[card.id],claims=[{'product_id':card.id,'field':'name','value':card.name}])
 validate_draft(draft,[card])


def test_exact_catalog_name_containing_id_label_remains_a_name():
 item=row();item.name='Studio ID 1';card=catalog_result(item)
 draft=ShoppingDraft(text=card.name+' is listed.',product_ids=[card.id],claims=[{'product_id':card.id,'field':'name','value':card.name}])
 validate_draft(draft,[card])


@pytest.mark.asyncio
async def test_actual_consultation_rejects_id_even_with_correct_name_claim_before_review():
 import json
 from unittest.mock import AsyncMock
 from tests.test_llm_execution_limits import service,completion
 from tests.test_sales_response_service import request
 svc=service();card=request().products[0]
 svc._chat_completion=AsyncMock(return_value=completion(json.dumps({'text':card.name+f' (ID {card.id}).','product_ids':[card.id],'claims':[{'product_id':card.id,'field':'name','value':card.name}]})))
 result=await svc.consult_catalog(question='Which item is listed?',cards=[card])
 assert result.response_kind=='system_notice' and result.products==[]
 assert svc._chat_completion.await_count==1
