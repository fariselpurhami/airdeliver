import pytest
from app.services.research.status_source_allowlist import policy_for_region

P=policy_for_region("US")

@pytest.mark.parametrize('url,tier',[
 ('https://www.apple.com/newsroom/2026/09/anything/',1),
 ('https://www.samsung.com/us/mobile/phones/',1),
 ('https://www.dell.com/en-us/shop/laptops',1),
 ('https://www.theverge.com/2026/9/1/story',2),
 ('https://www.rtings.com/headphones/reviews/x',2),
 ('https://www.fcc.gov/oet/ea/fccid',3),
])
def test_allowed_us_sources_have_tier(url,tier):
    assert P.classify(url).tier==tier and P.classify(url).region=='US'

@pytest.mark.parametrize('url',[
 'https://www.samsung.com/eg/mobile/phones/',      # wrong market path
 'https://www.dell.com/en-uk/shop/laptops',
 'https://www.amazon.com/dp/B000',                   # reseller
 'https://reddit.com/r/headphones/x',                # forum
 'http://www.apple.com/newsroom/',                   # not https
 'https://www.apple.com.evil.example/newsroom/',     # lookalike
 'https://evil.example/https://www.apple.com/',
 'https://user@www.apple.com/newsroom/',
])
def test_everything_else_is_rejected(url):
    assert P.classify(url) is None

def test_tier_limits_claim_kinds():
    assert {'release','price','availability'}<=P.classify('https://www.apple.com/newsroom/x').claims
    press=P.classify('https://www.theverge.com/x').claims
    assert 'release' in press and not {'price','availability'}&press
    reg=P.classify('https://www.fcc.gov/oet/ea/fccid').claims
    assert reg=={'certification'}

def test_unconfigured_region_is_refused_not_defaulted():
    with pytest.raises(ValueError):policy_for_region('EG')

def test_brand_domain_is_valid_only_for_its_own_brand():
    assert P.classify('https://www.apple.com/newsroom/x').brand=='apple'
    assert P.brand_matches('https://www.apple.com/newsroom/x','apple') is True
    assert P.brand_matches('https://www.apple.com/newsroom/x','samsung') is False
    assert P.brand_matches('https://www.theverge.com/x','samsung') is True  # press covers any brand
