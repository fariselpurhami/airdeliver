

def test_stock_place_tell_matches_unicode_hyphen_and_nbsp_variants():
    from app.services.conversation.shopping_copy import _STOCK_PLACE
    for t in ('listed as in\u2011stock locally','in\u00a0stock\u202flocally','locally\u2011in\u2011stock','in our\u00a0shop'):
        assert _STOCK_PLACE.search(t),t
    assert not _STOCK_PLACE.search('instock reports say the shop is far')


def test_sole_product_short_reference_is_accepted_but_multi_product_needs_full_name():
    """Real run (n=1, bait-02, 12:54 AM): the rewrite said "The watch" for "The Smart Watch", the names guard rejected it and the robotic original shipped."""
    from tests.test_writer_voice_repair import run,draft,OK
    robotic="The Studio Headphones you asked about are listed in our catalog.\n\n- Battery life: not specified in the available product details.\n- Weight: not mentioned in the specifications we have."
    friend="The headphones are a fit to look at.\n\n- I don't have the battery life.\n- I don't have the weight."
    text,seen=run([draft(robotic),draft(friend),OK])
    assert text==friend and len(seen)==3
