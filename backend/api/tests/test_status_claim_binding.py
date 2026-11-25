"""Exact quote and trusted metadata binding, not live research acceptance."""
from datetime import datetime,timezone,timedelta
from dataclasses import replace
import pytest
from app.services.research.status_claim_binding import VerifiedStatusSource,ExtractedStatus,bind_status_claim
from app.services.research.publisher_binding import PublisherRegistry,PublisherBinding
from app.services.research.product_status_policy import resolve_status
NOW=datetime(2026,11,25,21,tzinfo=timezone.utc)
QUOTE='Maker Model X released at 2026-11-25T20:00:00+00:00 in US.'


def source():return VerifiedStatusSource('https://news.maker.example/x',QUOTE,NOW,NOW-timedelta(hours=2),'US',('maker:x',))
def claim(**changes):
 data=dict(source=0,model_key='maker:x',assertion='released',effective_iso='2026-11-25T20:00:00+00:00',quote=QUOTE);data.update(changes);return ExtractedStatus(**data)
def registry():return PublisherRegistry((PublisherBinding('maker',('news.maker.example',)),))


def test_reviewed_exact_quote_maps_trusted_metadata_then_resolves_without_stock_claim():
 row=bind_status_claim(claim(),[source()],registry(),reviewed=True)
 assert row.publisher_key=='maker' and row.region=='US'
 result=resolve_status('maker:x',[row],now=NOW,region='US',max_age=timedelta(hours=6))
 assert result.state=='released' and result.merchant_stock=='unverified'

@pytest.mark.parametrize('mode',['review','quote','date','model','host','metadata','out_of_range','naive'])
def test_unverified_status_does_not_self_upgrade(mode):
 c=claim();sources=[source()];reviewed=True
 if mode=='review':reviewed=False
 elif mode=='quote':c=claim(quote=QUOTE+' forged')
 elif mode=='date':c=claim(effective_iso='2026-11-24T20:00:00+00:00')
 elif mode=='model':c=claim(model_key='maker:xs')
 elif mode=='host':sources=[replace(source(),final_url='https://news.maker.example.attacker.test/x')]
 elif mode=='metadata':sources=[{'final_url':'https://news.maker.example/x','official':True}]
 elif mode=='out_of_range':c=claim(source=1)
 elif mode=='naive':sources=[replace(source(),published_at=datetime(2026,11,25))]
 with pytest.raises(ValueError):bind_status_claim(c,sources,registry(),reviewed=reviewed)


def test_fresh_fetch_cannot_make_old_publication_current():
 row=bind_status_claim(claim(),[replace(source(),published_at=NOW-timedelta(days=100))],registry(),reviewed=True)
 assert resolve_status('maker:x',[row],now=NOW,region='US',max_age=timedelta(hours=6)).state=='unverified'


def test_wrong_region_keeps_status_unverified():
 row=bind_status_claim(claim(),[source()],registry(),reviewed=True)
 assert resolve_status('maker:x',[row],now=NOW,region='EG',max_age=timedelta(hours=6)).state=='unverified'
