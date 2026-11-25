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


def test_typed_capacity_reverses_only_explicit_key_and_value_without_converting_units():
    brief=ShoppingBrief(required_features=['16GB RAM'])
    assert brief.permits(card('Laptop',{'RAM':'16 GB'}))
    assert brief.permits(card('Laptop',{'memory':'16 gigabytes'}))
    assert not brief.permits(card('Laptop',{'RAM':'116 GB'}))
    assert not brief.permits(card('Laptop',{'RAM':'16384 MB'}))
    assert not brief.permits(card('Laptop',{'RAM':'16 GiB'}))
    assert not brief.permits(card('Laptop',{'RAM':'8GB or16GB'}))
    assert not brief.permits(card('Laptop',{'storage':'16GB'}))
    assert not brief.permits(card('Laptop',{'RAM':'8GB','storage':'16GB'}))
    assert ShoppingBrief(required_features=['1TB SSD']).permits(card('Laptop',{'SSD':'1 terabyte'}))
    assert not ShoppingBrief(required_features=['1TB SSD']).permits(card('Laptop',{'HDD':'1TB'}))


def test_explicit_capacity_in_current_name_remains_valid_but_ambiguous_variants_do_not():
    brief=ShoppingBrief(required_features=['16GB RAM'])
    assert brief.permits(card('Laptop16 GB RAM',{})) is False  # No lexical boundary.
    assert brief.permits(card('Laptop 16 GB RAM',{}))
    assert not brief.permits(card('Laptop 116GB RAM',{}))
    assert not brief.permits(card('Laptop 8GB or16GB RAM',{}))
    assert not brief.permits(card('Laptop 8GB/16GB RAM',{}))
