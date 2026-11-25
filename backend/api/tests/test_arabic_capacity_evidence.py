"""Explicit bounded Arabic aliases, not semantic feature extraction."""
from types import SimpleNamespace
import pytest
from app.services.capacity_evidence import supported_capacity
from app.services.shopping_discovery import ShoppingBrief,catalog_result

@pytest.mark.parametrize('feature,specs,expected',[
 ('١٦ جيجابايت رام',{'RAM':'16GB'},True),
 ('رام ١٦ جيجا بايت',{'memory':'16000MB'},True),
 ('على الأقل ١٦ جيجابايت رام',{'RAM':'32GB'},True),
 ('علي الاقل ١٦ جيجابايت رام',{'RAM':'8GB'},False),
 ('بحد أدنى ١ تيرابايت تخزين',{'storage':'1000GB'},True),
 ('بحد ادنى ١ تيرا بايت التخزين',{'storage':'999GB'},False),
 ('على الأكثر ١٦ جيجابايت رام',{'RAM':'8GB'},True),
 ('بحد أقصى ١٦ جيجابايت رام',{'RAM':'32GB'},False),
 ('١ تيرابايت تخزين',{'سعة التخزين':'1000GB'},True),
 ('16GB RAM',{'الرام':'١٦ جيجابايت'},True),
 ('١٦ جيجابايت ذاكرة الوصول العشوائي',{'RAM':'16GB'},True),
 ('١٦ جيجابايت رام',{'storage':'16GB'},False),
 ('١ تيرابايت تخزين',{'SSD':'1000GB'},False),
 ('١٦ جيجابايت رام',{'RAM':'16GiB'},False),
 ('١٦ جيجابايت رام',{'RAM':'8GB أو16GB'},False),
 ('على الأقل رام كتير',{'description':'على الأقل رام كتير'},False),
 ('١٦ جيجابايت رام',{'RAM':'116GB'},False),
 ('١٦٫٥ جيجابايت رام',{'RAM':'16.5GB'},True),
])
def test_explicit_arabic_aliases_keep_kind_family_and_bound(feature,specs,expected):
    assert supported_capacity(feature,specs) is expected

@pytest.mark.parametrize('feature,expected',[
 ('على الأقل ١٦ جيجابايت رام',True),
 ('بحد أقصى ١٦ جيجابايت رام',False),
 ('١٦ جيجابايت تخزين',False),
])
def test_customer_literal_grounding_and_actual_catalog_gate(feature,expected):
    row=SimpleNamespace(id=7,name='Laptop',sku='laptop',is_active=True,inventory=2,price=50,currency='USD',attributes={'RAM':'32GB'},category='electronics')
    card=catalog_result(row)
    brief=ShoppingBrief(required_features=[feature]).grounded('عايز لابتوب '+feature)
    assert brief.required_features==[feature]
    assert brief.permits(card) is expected
    assert ShoppingBrief(excluded_terms=['٣٢ جيجابايت رام']).grounded('بدون ٣٢ جيجابايت رام').permits(card) is False

@pytest.mark.parametrize('name',[
 'لابتوب ١٦ جيجابايت رام أو ٣٢ جيجابايت رام',
 'لابتوب خيارات ١٦ جيجابايت رام',
 'لابتوب ١٦ جيجابايت رام / ٣٢ جيجابايت رام',
])
def test_arabic_name_variants_cannot_be_single_capacity_evidence(name):
    assert supported_capacity('١٦ جيجابايت رام',{},name) is False

def test_unambiguous_current_name_literal_capacity_retained():
    assert supported_capacity('١٦ جيجابايت رام',{},'لابتوب ١٦ جيجابايت رام') is True
