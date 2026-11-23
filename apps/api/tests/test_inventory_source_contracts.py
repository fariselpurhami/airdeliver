from datetime import datetime,timezone,timedelta
from uuid import uuid4
import pytest
from pydantic import ValidationError
from app.inventory_sources.contracts import SourceIdentity,SourceTerms,Operation,operation_gate,ReservationResult,StockSnapshot,LAUNCH_CATEGORIES
NOW=datetime(2026,11,23,tzinfo=timezone.utc)

def terms(**change):
 return SourceTerms.model_validate(dict(version='fixture-only',approved=True,approval_reference='synthetic-fixture-not-authority',effective_at=NOW-timedelta(days=1),expires_at=NOW+timedelta(days=1),allowed_categories=list(LAUNCH_CATEGORIES),capabilities=list(Operation),permitted_operations=list(Operation),permits_airdeliver_checkout=True,permits_airdeliver_payment_collection=True,permits_airdeliver_branding=True,return_policy_reference='fixture-return-policy',**change))

@pytest.mark.parametrize('category',sorted(LAUNCH_CATEGORIES))
def test_every_launch_category_uses_same_gate(category):
 assert operation_gate(terms(),Operation.PLACE_ORDER,category,now=NOW)==()

@pytest.mark.parametrize('field,code',[('approved','terms_not_approved'),('permits_airdeliver_checkout','checkout_not_permitted'),('permits_airdeliver_payment_collection','payment_collection_not_permitted'),('permits_airdeliver_branding','branding_not_permitted')])
def test_permissions_independent_and_fail_closed(field,code):
 t=SourceTerms.model_validate({**terms().model_dump(),field:False})
 assert code in operation_gate(t,Operation.PLACE_ORDER,'clothing',now=NOW)

def test_capability_does_not_grant_commercial_permission():
 t=SourceTerms.model_validate({**terms().model_dump(),'permitted_operations':[]})
 assert 'operation_not_permitted' in operation_gate(t,Operation.CATALOG,'electronics',now=NOW)
 assert 'terms_not_current' in operation_gate(terms(),Operation.CATALOG,'electronics',now=NOW+timedelta(days=2))
 assert 'category_not_permitted' in operation_gate(terms(),Operation.CATALOG,'food',now=NOW)

@pytest.mark.parametrize('kind',['partner_merchant','airdeliver_own_stock'])
def test_identity_is_general_for_partner_and_own_stock(kind):
 i=SourceIdentity(source_key=uuid4().hex,seller_key=uuid4().hex,kind=kind,legal_seller_name='Synthetic fixture',inventory_country='US',seller_country='US')
 assert i.kind==kind
 with pytest.raises(ValidationError):SourceIdentity.model_validate({**i.model_dump(),'inventory_country':'CN'})

def test_no_held_or_fresh_stock_claim_without_evidence():
 with pytest.raises(ValidationError):ReservationResult(request_id=uuid4(),state='held',fence=1)
 unknown=ReservationResult(request_id=uuid4(),state='unknown',fence=1)
 assert unknown.reservation_reference is None
 with pytest.raises(ValidationError):StockSnapshot(variant_id='v',source_revision='r',observed_at=NOW,expires_at=NOW,available=10,origin_reference='o')
