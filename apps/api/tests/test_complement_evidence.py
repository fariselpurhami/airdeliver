from types import SimpleNamespace as Product
import pytest
from app.services.complement_evidence import catalog_asserts_complement


@pytest.mark.parametrize('raw',[None,'','bad','{}','[true]','[1]','["other"]','["shoe", 2]'])
def test_unknown_malformed_or_other_relation_abstains(raw):
    assert not catalog_asserts_complement(Product(id=1,sku='shoe'),Product(id=2,attributes={'complement_for_skus':raw}))


def test_only_explicit_exact_anchor_sku_relation_qualifies():
    anchor=Product(id=1,sku='shoe')
    assert catalog_asserts_complement(anchor,Product(id=2,attributes={'complement_for_skus':'["shoe"]'}))
    assert not catalog_asserts_complement(anchor,Product(id=1,attributes={'complement_for_skus':'["shoe"]'}))
    assert not catalog_asserts_complement(anchor,Product(id=2,name='shoe laces compatible shoe',attributes={}))
