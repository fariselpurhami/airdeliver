from types import SimpleNamespace
from app.services.shopping_discovery import ShoppingBrief,catalog_result


def card(name,specs):
    return catalog_result(SimpleNamespace(id=1,name=name,sku='real',category='computers',price=100,currency='USD',inventory=2,is_active=True,attributes=specs))


def test_literal_constraints_survive_grounding_but_model_inventions_do_not():
    brief=ShoppingBrief(excluded_terms=['red','invented'],required_features=['16GB RAM','invented'])
    grounded=brief.grounded('I need16GB RAM and no red')
    assert grounded.excluded_terms==['red'] and grounded.required_features==['16GB RAM']
    assert grounded.permits(card('Laptop',{'memory':'16GB RAM','color':'blue'}))
    assert not grounded.permits(card('Laptop',{'memory':'8GB RAM','color':'blue'}))
    assert not grounded.permits(card('Laptop',{'memory':'16GB RAM','color':'red'}))
    assert not grounded.permits(card('Laptop',{}))


def test_typographic_capacity_spacing_does_not_reject_same_explicit_feature():
    brief=ShoppingBrief(required_features=['16GB RAM'])
    assert brief.permits(card('Laptop',{'memory':'16 GB RAM'}))
    assert not brief.permits(card('Laptop',{'memory':'8 GB RAM'}))


def test_literal_feature_boundaries_do_not_match_substrings_or_digit_prefixes():
    assert ShoppingBrief(excluded_terms=['red']).permits(card('Infrared sensor',{}))
    assert not ShoppingBrief(excluded_terms=['red']).permits(card('Sensor',{'color':'red'}))
    assert not ShoppingBrief(required_features=['16GB RAM']).permits(card('Laptop',{'memory':'116GB RAM'}))
    assert not ShoppingBrief(required_features=['wired']).permits(card('Adapter',{'connection':'unwired'}))
    assert ShoppingBrief(required_features=['USB-C']).permits(card('Adapter',{'connection':'USB - C'}))
