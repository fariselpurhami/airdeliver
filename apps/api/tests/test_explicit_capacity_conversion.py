from decimal import Decimal
import pytest
from app.services.capacity_evidence import supported_capacity
from app.services.shopping_discovery import ShoppingBrief,catalog_result
from types import SimpleNamespace

@pytest.mark.parametrize('feature,specs,expected',[
 ('1TB storage',{'storage':'1000GB'},True),
 ('1TB storage',{'storage':'1024GB'},False),
 ('at least 1TB storage',{'storage':'1024GB'},True),
 ('at most 1TB storage',{'storage':'1001GB'},False),
 ('at least 16GB RAM',{'RAM':'15999MB'},False),
 ('at least 16GB RAM',{'RAM':'16000MB'},True),
 ('0.5TB SSD',{'SSD':'500GB'},True),
 ('1GiB RAM',{'RAM':'1024MiB'},True),
 ('1TiB storage',{'storage':'1024GiB'},True),
 ('1GB RAM',{'RAM':'1024MiB'},False),
 ('1GiB RAM',{'RAM':'1000MB'},False),
 ('1TB storage',{'RAM':'1000GB'},False),
 ('1TB storage',{'SSD':'1000GB'},False),
 ('1TB storage',{'storage':'512GB or 1000GB'},False),
 ('1TB storage',{'storage':'1000GB/2000GB'},False),
])
def test_exact_explicit_capacity_family_conversion(feature,specs,expected):
    assert supported_capacity(feature,specs) is expected

@pytest.mark.parametrize('feature,expected',[('at least 1TB storage',True),('at most 999GB storage',False),('1TiB storage',False)])
def test_actual_card_brief_gate_converts_only_explicit_same_family(feature,expected):
    row=SimpleNamespace(id=7,name='Disk',sku='disk',is_active=True,inventory=2,price=50,currency='USD',attributes={'storage':'1000GB'},category='Storage')
    card=catalog_result(row)
    assert ShoppingBrief(required_features=[feature]).permits(card) is expected
    assert ShoppingBrief(excluded_terms=['1TB storage']).permits(card) is False
