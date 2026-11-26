

def test_stock_place_tell_matches_unicode_hyphen_and_nbsp_variants():
    from app.services.conversation.shopping_copy import _STOCK_PLACE
    for t in ('listed as in\u2011stock locally','in\u00a0stock\u202flocally','locally\u2011in\u2011stock','in our\u00a0shop'):
        assert _STOCK_PLACE.search(t),t
    assert not _STOCK_PLACE.search('instock reports say the shop is far')
