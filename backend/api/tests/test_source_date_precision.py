"""Synthetic publication shapes, not verified real-publisher metadata."""
from datetime import date,datetime,timedelta,timezone
import pytest
from app.services.research.source_date_precision import parse_source_publication

@pytest.mark.parametrize('raw',['2026-03-03','2026-03-03Z'])
def test_day_only_publication_retains_day_without_invented_instant(raw):
 value=parse_source_publication(raw)
 assert value.precision=='day' and value.day==date(2026,3,3)
 assert value.instant is None
 assert value.raw==raw

def test_full_publication_preserves_timezone_and_instant_not_search_calendar_day():
 value=parse_source_publication('2026-03-11T08:00:00+09:00')
 assert value.precision=='instant' and value.day==date(2026,3,11)
 assert value.instant.utcoffset()==timedelta(hours=9)
 assert value.instant.astimezone(timezone.utc)==datetime(2026,3,10,23,tzinfo=timezone.utc)

@pytest.mark.parametrize('raw',['2026-03-11T08:00:00Z','2026-03-11T08:00:00.123+00:00'])
def test_aware_iso_instants_keep_original_precision(raw):
 value=parse_source_publication(raw)
 assert value.precision=='instant' and value.raw==raw
 assert value.instant.tzinfo is not None

@pytest.mark.parametrize('raw',[
 '',None,123,True,' March 3, 2026','2026-03-03 ', 'today','2026/03/03',
 '2026-02-30','2026-3-3','2026-03-03T00:00:00','2026-03-03T00:00:00-00:00',
 '2026-03-03T00:00:00+00:60','2026-03-03T00:00:00+01:99','2026-03-03T24:00:00Z','2026-03-03T00:00:00+25:00',
 '2026-03-03T00:00:00+14:01','2026-03-03T00:00:00+15:00',
 '2026-03-03T00:00:00Z extra',
 '20260303','2026-W10-2','2026-03-03\n','2026-03-03T00:00:00+00:00\x00'])
def test_unsupported_or_ambiguous_publication_fails_closed(raw):
 with pytest.raises(ValueError,match='unsupported_publication_date'):parse_source_publication(raw)

def test_date_parser_does_not_return_verified_status_or_release_evidence():
 value=parse_source_publication('2026-03-03')
 assert not hasattr(value,'assertion') and not hasattr(value,'publisher_key')
 assert not hasattr(value,'region') and not hasattr(value,'model_key')
 with pytest.raises((AttributeError,TypeError)):
  value.precision='instant'
