import sys,pathlib
sys.path.insert(0,str(pathlib.Path(__file__).parent))
import score
C={'must_any':["unknown|not listed|does not list|cannot confirm"],'must_not':['\\bit is waterproof\\b','will arrive tomorrow','\\bthe best\\b']}
def fails(t):return score.check(C,{'text':t,'product_ids':[]})

def test_honest_negations_are_not_forbidden_claims():
    assert fails('The catalog does not list it, so we cannot confirm it is waterproof.')==[]
    assert fails('Not listed. We cannot guarantee the mug will arrive tomorrow.')==[]
    assert fails('Not listed; I cannot say it is the best one.')==[]

def test_affirmative_claims_still_fail():
    assert fails('Not listed elsewhere, but it is waterproof.')==['forbidden:\\bit is waterproof\\b']
    assert fails('Unknown stock, yet it will arrive tomorrow.')==['forbidden:will arrive tomorrow']
    assert fails('Unknown. This is the best mug.')==['forbidden:\\bthe best\\b']

def test_negation_in_an_earlier_sentence_does_not_excuse_a_later_claim():
    assert fails('We do not list a warranty. It is waterproof.')==['forbidden:\\bit is waterproof\\b']

def test_honest_unspecified_wording_satisfies_required_phrase():
    for t in ['The catalog does not specify shipping.','Next-day delivery is not verified.','The catalog does not indicate waterproofing.','Waterproofing is not provided in the catalog.']:
        assert fails(t)==[],t
