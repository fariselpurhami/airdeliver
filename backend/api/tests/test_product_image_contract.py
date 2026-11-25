from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.services.product_serialization import serialize_product,FALLBACK
from app.api.v1.endpoints.products import read_products,get_featured_recommendation


def product(image):
    data={'id':1,'name':'demo','image':image,'inventory':10}
    return SimpleNamespace(model_dump=lambda:data.copy(),inventory=10)


@pytest.mark.parametrize('url',['https://images.unsplash.com/photo-demo','/images/local.jpg'])
def test_image_field_is_preserved_and_aliased(url):
    row=serialize_product(product(url));assert row['image']==row['image_url']==url


@pytest.mark.parametrize('value',[None,'','javascript:alert(1)','//evil.invalid/image','http://user:pass@example.invalid/a'])
def test_missing_unsafe_urls_get_actual_local_asset(value):
    row=serialize_product(product(value));assert row['image_url']==FALLBACK


@pytest.mark.asyncio
async def test_actual_list_and_featured_endpoints_use_same_contract():
    p=product('https://images.unsplash.com/photo-demo')
    db=SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(scalars=lambda:SimpleNamespace(all=lambda:[p],first=lambda:p))))
    rows=await read_products(db=db,skip=0,limit=10,page=None,category=None)
    featured=await get_featured_recommendation(db=db)
    assert rows[0]['image_url']==featured['image_url']==p.model_dump()['image']
