import pytest
from app.schemas.shipping import ShippingAddress
from tests.test_ai_checkout_service import SHIPPING


@pytest.mark.parametrize('field,value', [('country','EG'),('postal_code','abc'),('postal_code','1234'),('region','XX'),('phone','123'),('line1','Address pending via Chat'),('recipient_name',' ')])
def test_invalid_shipping_is_rejected(field, value):
    with pytest.raises(ValueError):
        ShippingAddress(**{**SHIPPING, field:value})


def test_shipping_normalizes_codes_and_phone_without_guessing_a_missing_address():
    address = ShippingAddress(**{**SHIPPING, 'country':' us ', 'region':' ny ', 'phone':'(212) 555-0123'})
    assert address.country == 'US'
    assert address.region == 'NY'
    assert address.phone == '+12125550123'
    assert '123 Main Street' in address.display_address()
