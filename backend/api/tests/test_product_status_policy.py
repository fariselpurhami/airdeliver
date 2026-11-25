"""Release truth must not come from model memory or a failed catalog search."""
from datetime import datetime,timedelta,timezone
import pytest
from app.services.research.product_status_policy import StatusEvidence,resolve_status
NOW=datetime(2026,11,25,21,tzinfo=timezone.utc)

def evidence(**changes):
    return StatusEvidence(**dict(model_key='maker:model-x',source_url='https://maker.example/products/model-x',publisher_key='maker',official_binding=True,assertion='released',observed_at=NOW,published_at=NOW-timedelta(hours=2),effective_at=NOW-timedelta(hours=1),region='US',exact_identity=True,**changes))

def change(**changes):
    base=dict(model_key='maker:model-x',source_url='https://maker.example/products/model-x',publisher_key='maker',official_binding=True,assertion='released',observed_at=NOW,published_at=NOW-timedelta(hours=2),effective_at=NOW-timedelta(hours=1),region='US',exact_identity=True);base.update(changes);return StatusEvidence(**base)

def resolve(rows,**kwargs):return resolve_status('maker:model-x',rows,now=NOW,region='US',max_age=timedelta(hours=6),**kwargs)

def test_current_official_exact_model_release_is_not_stock():
    result=resolve([evidence()]);assert result.state=='released';assert result.merchant_stock=='unverified';assert result.sources==('https://maker.example/products/model-x',)

def test_empty_catalog_and_empty_search_cannot_prove_nonexistence():
    assert resolve([]).state=='unverified'

@pytest.mark.parametrize('patch',[{'official_binding':False},{'exact_identity':False},{'model_key':'maker:model-xs'},{'region':'JP'},{'observed_at':NOW-timedelta(days=2)}])
def test_unbound_sibling_other_region_or_stale_evidence_stays_unverified(patch):
    assert resolve([change(**patch)]).state=='unverified'

def test_tomorrow_schedule_is_not_released_or_unannounced():
    result=resolve([change(assertion='scheduled_release',effective_at=NOW+timedelta(days=1))]);assert result.state=='scheduled';assert result.effective_at==NOW+timedelta(days=1)

def test_passed_launch_schedule_needs_actual_release_confirmation():
    assert resolve([change(assertion='scheduled_release')]).state=='schedule_elapsed_unconfirmed'

def test_announcement_is_not_release():
    assert resolve([change(assertion='announced')]).state=='announced'

def test_conflicting_current_official_assertions_are_not_averaged():
    assert resolve([evidence(),change(assertion='scheduled_release',effective_at=NOW+timedelta(days=1))]).state=='conflicting'

def test_explicit_supersession_must_be_trusted_metadata_not_recency_alone():
    old=change(source_url='https://maker.example/news/old',assertion='scheduled_release',effective_at=NOW+timedelta(days=1))
    assert resolve([old,evidence()]).state=='conflicting'
    current=change(supersedes=('https://maker.example/news/old',))
    assert resolve([old,current]).state=='released'

def test_future_dated_source_is_not_current_confirmation():
    assert resolve([change(published_at=NOW+timedelta(days=1))]).state=='unverified'

@pytest.mark.parametrize('field',['observed_at','published_at','effective_at'])
def test_naive_instants_rejected(field):
    with pytest.raises(ValueError):change(**{field:datetime(2026,11,25)})

def test_no_evidence_shape_can_claim_global_nonexistence():
    with pytest.raises(ValueError):change(assertion='nonexistent')

def test_unverified_source_cannot_self_upgrade_with_official_looking_url():
    assert resolve([change(official_binding=False,source_url='https://maker.example/official-release')]).state=='unverified'
