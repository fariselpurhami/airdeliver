"""Explicit suffix comparators preserve capacity family, kind and ambiguity."""
from types import SimpleNamespace
import pytest
from app.services.capacity_evidence import supported_capacity
from app.services.shopping_discovery import ShoppingBrief,catalog_result

@pytest.mark.parametrize('feature,specs,expected',[
 ('16GB RAM at least',{'RAM':'32GB'},True),
 ('16GB RAM minimum',{'RAM':'8GB'},False),
 ('16GB RAM at most',{'RAM':'8GB'},True),
 ('16GB RAM maximum',{'RAM':'32GB'},False),
 ('رام ١٦ جيجابايت على الأقل',{'RAM':'32GB'},True),
 ('١٦ جيجابايت رام بحد أدنى',{'RAM':'8GB'},False),
 ('التخزين ١ تيرابايت على الأقل',{'storage':'1000GB'},True),
 ('التخزين ١ تيرابايت بحد أقصى',{'storage':'1001GB'},False),
 ('RAM 16GB علي الاقل',{'RAM':'16000MB'},True),
 ('RAM 16GB بحد ادنى',{'storage':'32GB'},False),
 ('1GiB RAM minimum',{'RAM':'1000MB'},False),
 ('16GB RAM at least',{'RAM':'8GB or32GB'},False),
 ('at least 16GB RAM at most',{'RAM':'32GB'},False),
 ('16GB RAM at least at most',{'RAM':'32GB'},False),
 ('16GB RAM at least',{},False),
])
def test_explicit_suffix_capacity_contract(feature,specs,expected):
    assert supported_capacity(feature,specs) is expected
    row=SimpleNamespace(id=7,name='Laptop',sku='laptop',is_active=True,inventory=2,price=50,currency='USD',attributes=specs,category='computers')
    card=catalog_result(row)
    assert ShoppingBrief(required_features=[feature]).permits(card) is expected
    assert ShoppingBrief(excluded_terms=[feature]).permits(card) is (not expected)
