from datetime import datetime,timezone,timedelta
import pytest
from pydantic import ValidationError
from app.services.us_quote_policy import QuoteInput,USShippingPolicy,TaxAssessment,quote_basis,prepare_quote
NOW=datetime(2026,11,23,tzinfo=timezone.utc)

def fixture():
 request=QuoteInput(address=dict(recipient_name='Test Buyer',line1='123 Test Street',city='Test City',region='CA',postal_code='90210',country='US',phone='2025550101'),lines=[dict(product_id=1,quantity=2,unit_price_cents=1001,available=2,active=True)])
 policy=USShippingPolicy(version='fixture-v1',approved_reference='fixture-only-not-approved-policy',regions=['CA'],flat_cents=599,free_at_cents=5000,expires_at=NOW+timedelta(hours=1))
 tax=TaxAssessment(quote_basis_sha256=quote_basis(request,policy,now=NOW)['quote_basis_sha256'],amount_cents=183,source_reference='fixture-assessment-not-tax-advice',reviewed_by='Test operator',expires_at=NOW+timedelta(minutes=10))
 return request,policy,tax

def test_exact_cents_and_no_claim_of_reservation_or_payment_readiness():
 r,p,t=fixture();q=prepare_quote(r,p,t,now=NOW)
 assert q['total_cents']==2784 and q['display_total']=='27.84'
 assert q['ready_for_payment'] is False and q['stock_reserved'] is False
 assert 'address' not in q and '90210' not in str(q)
 assert q['expires_at']==t.expires_at.isoformat()

@pytest.mark.parametrize('field,value',[('postal_code','90211'),('line1','124 Test Street'),('region','NY')])
def test_destination_change_invalidates_assessment(field,value):
 r,p,t=fixture();r=QuoteInput.model_validate({**r.model_dump(),'address':{**r.address.model_dump(),field:value}})
 with pytest.raises(ValueError):prepare_quote(r,p,t,now=NOW)

@pytest.mark.parametrize('change',[{'flat_cents':600},{'version':'fixture-v2'},{'free_at_cents':0}])
def test_shipping_changes_invalidate_tax_basis(change):
 r,p,t=fixture();p=USShippingPolicy.model_validate({**p.model_dump(),**change})
 with pytest.raises(ValueError):prepare_quote(r,p,t,now=NOW)

def test_expiry_stock_and_price_rechecks():
 r,p,t=fixture()
 with pytest.raises(ValueError):prepare_quote(r,p,t,now=NOW+timedelta(minutes=11))
 for change in ({'available':1},{'active':False},{'unit_price_cents':1002},{'quantity':1}):
  changed=QuoteInput.model_validate({**r.model_dump(),'lines':[{**r.lines[0].model_dump(),**change}]})
  with pytest.raises(ValueError):prepare_quote(changed,p,t,now=NOW)

def test_zero_tax_is_explicit_not_a_fallback():
 r,p,t=fixture();t=TaxAssessment.model_validate({**t.model_dump(),'amount_cents':0})
 assert prepare_quote(r,p,t,now=NOW)['tax_cents']==0
 with pytest.raises(ValidationError):TaxAssessment.model_validate({k:v for k,v in t.model_dump().items() if k!='amount_cents'})

@pytest.mark.parametrize('value',[True,1.5,'100'])
def test_money_rejects_coercion(value):
 r,p,t=fixture()
 with pytest.raises(ValidationError):TaxAssessment.model_validate({**t.model_dump(),'amount_cents':value})

def test_free_shipping_threshold_and_duplicate_lines():
 r,p,t=fixture();p=USShippingPolicy.model_validate({**p.model_dump(),'free_at_cents':2002})
 assert quote_basis(r,p,now=NOW)['shipping_cents']==0
 with pytest.raises(ValidationError):QuoteInput.model_validate({**r.model_dump(),'lines':[r.lines[0].model_dump()]*2})
