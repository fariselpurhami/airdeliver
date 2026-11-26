

def test_model_style_word_the_customer_typed_may_be_echoed_but_measurements_may_not():
    """Real path gap found by simulation: any answer saying "PS5" was withheld as an unsupported numeric claim."""
    import pytest
    from tests.test_shopping_discovery_contract import row
    from app.services.shopping_discovery import catalog_result
    from app.services.shopping_copy import validate_draft, ShoppingDraft
    card=catalog_result(row())
    def d(text):return ShoppingDraft.model_validate({'text':text,'product_ids':[1],'claims':[{'product_id':1,'field':'name','value':'Studio Headphones'}]})
    validate_draft(d("I can't see PS5 support on the Studio Headphones."),[card],{},{},'Are they compatible with a PS5?')
    with pytest.raises(ValueError):
        validate_draft(d("The Studio Headphones support PS5."),[card],{},{},'Are they compatible with a PS4?')
    with pytest.raises(ValueError):
        validate_draft(d("The Studio Headphones last 30h."),[card],{},{},'Do they last 30h?')
