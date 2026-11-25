from datetime import datetime,timezone,timedelta
from uuid import uuid4
import pytest
from pydantic import ValidationError
from app.schemas.returns_support import ReturnPolicyDraft,SupportIntakeDraft,intake_availability
NOW=datetime(2026,11,23,tzinfo=timezone.utc)

def policy(**changes):
 return ReturnPolicyDraft(version='fixture-v1',seller_reference='fixture-store',approval_state='proposed',window_days_from_delivery=30,window_clock='calendar_days_in_destination_timezone',destination_timezone='America/New_York',return_shipping_payer='case_review',original_shipping_refund='case_review',restocking_fee='case_review',allowed_condition_codes=['unopened'],support_queue_reference='unconfigured-fixture',effective_at=NOW-timedelta(days=1),expires_at=NOW+timedelta(days=1),**changes)

def test_unset_or_proposed_policy_cannot_claim_intake_ready():
 for p in (None,policy()):
  result=intake_availability(policy=p,queue_owner_verified=False,now=NOW)
  assert result['configuration_ready'] is False
  assert result['blocked_reasons']==['return_policy_not_approved','support_queue_owner_not_verified']
  assert not any(result[k] for k in ('intake_enabled','ticket_created','refund_started','return_accepted'))

def test_approved_policy_still_cannot_enable_unimplemented_intake():
 p=ReturnPolicyDraft.model_validate({**policy().model_dump(),'approval_state':'approved','approval_reference':'fixture-source-only'})
 result=intake_availability(policy=p,queue_owner_verified=True,now=NOW)
 assert result['configuration_ready'] is True and result['intake_enabled'] is False
 assert intake_availability(policy=p,queue_owner_verified=True,now=NOW+timedelta(days=2))['configuration_ready'] is False

@pytest.mark.parametrize('change',[{'window_days_from_delivery':True},{'window_days_from_delivery':0},{'destination_timezone':'Not/A_Zone'},{'approval_state':'approved'},{'effective_at':NOW.replace(tzinfo=None)}])
def test_policy_invalid_or_incomplete_values_refused(change):
 with pytest.raises(ValidationError):ReturnPolicyDraft.model_validate({**policy().model_dump(),**change})

def test_return_request_needs_unique_selected_purchase_lines_and_no_owner_in_payload():
 data=dict(request_id=uuid4(),order_id=1,kind='return',message='Please review this request.')
 with pytest.raises(ValidationError):SupportIntakeDraft(**data)
 line=dict(order_line_id=1,quantity=1,reason='changed_mind',condition_code='unopened')
 assert len(SupportIntakeDraft(**data,lines=[line]).lines)==1
 for extra in ({'lines':[line,line]},{'lines':[line],'user_id':99}):
  with pytest.raises(ValidationError):SupportIntakeDraft(**data,**extra)
