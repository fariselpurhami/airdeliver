import pytest
from app.services.capacity_evidence import supported_capacity

@pytest.mark.parametrize('feature,specs,expected',[
 ('at least 16GB RAM',{'RAM':'32GB'},True),
 ('minimum 16GB RAM',{'memory':'16 gigabytes'},True),
 ('min. 16GB RAM',{'RAM':'8GB'},False),
 ('at most 16GB RAM',{'RAM':'8GB'},True),
 ('maximum 16GB RAM',{'RAM':'32GB'},False),
 ('at least 16GB RAM',{'storage':'512GB','RAM':'8GB'},False),
 ('at least 16GB RAM',{'RAM':'32GiB'},False),
 ('at least 16GB RAM',{'RAM':'32768MB'},False),
 ('at least 16GB RAM',{'RAM':'8GB or32GB'},False),
 ('at least 16GB RAM',{},False),
 ('at least lots RAM',{'description':'at least lots RAM'},False),
 ('16GB RAM',{'RAM':'32GB'},False),
])
def test_explicit_bounds_same_typed_unit_only(feature,specs,expected):
 assert supported_capacity(feature,specs,'Laptop32GB RAM') is expected
