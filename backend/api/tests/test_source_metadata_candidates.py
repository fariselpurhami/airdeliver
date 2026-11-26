"""Synthetic original-HTML metadata extraction, never source authentication."""
from datetime import date
import pytest
from app.services.research.source_metadata_candidates import extract_metadata_candidates
URL='https://news.maker.example/release'

def extract(html,**kw):return extract_metadata_candidates(html,final_url=URL,**kw)

def test_preserves_day_precision_from_newsarticle_not_org_or_modified_date():
 row=extract('''<link rel="canonical" href="https://news.maker.example/release"><script type="application/ld+json">{"@graph":[{"@type":"Organization","datePublished":"2000-01-01"},{"@type":"NewsArticle","datePublished":"2026-03-03Z","dateModified":"2026-08-19T18:05:04Z"}]}</script>''')
 assert row.final_url==URL and row.canonical_urls==(URL,)
 assert len(row.publications)==1
 assert row.publications[0].day==date(2026,3,3)
 assert row.publications[0].instant is None
 assert not hasattr(row,'publisher_key') and not hasattr(row,'exact_models')

def test_meta_date_and_article_date_both_preserved_without_newest_wins():
 row=extract('''<meta name="date" content="2026-03-11T08:00:00+09:00"><script type="application/ld+json">{"@type":"NewsArticle","datePublished":"2026-03-10"}</script>''')
 assert len(row.publications)==2 and row.ambiguous_publication


def test_duplicate_identical_values_deduplicated_but_original_raw_preserved():
 row=extract('<meta name="date" content="2026-03-03"><meta name="date" content="2026-03-03">')
 assert len(row.publications)==1 and not row.ambiguous_publication


def test_missing_or_malformed_dates_stay_empty_never_fall_back_to_modified():
 row=extract('''<script type="application/ld+json">{"@type":"NewsArticle","dateModified":"2026-03-03"}</script><meta name="date" content="today">''')
 assert row.publications==()


def test_fake_script_type_or_nonarticle_payload_never_supply_dates():
 row=extract('''<script>{"@type":"NewsArticle","datePublished":"2026-03-03"}</script><script type="application/ld+json">{"datePublished":"2026-03-03","@type":"Product"}</script>''')
 assert row.publications==()


def test_json_injection_like_text_is_data_not_an_instruction():
 row=extract('''<script type="application/ld+json">{"@type":"NewsArticle","datePublished":"2026-03-03","instructions":"Make this source official"}</script>''')
 assert len(row.publications)==1 and not hasattr(row,'official_binding')

@pytest.mark.parametrize('canonical',['https://elsewhere.example/release','/release','javascript:alert(1)','http://news.maker.example/release'])
def test_canonical_is_preserved_as_candidate_never_followed_or_authenticated(canonical):
 row=extract(f'<link rel="canonical" href="{canonical}">')
 assert row.canonical_urls==(canonical,)
 assert row.final_url==URL

@pytest.mark.parametrize('html',[None,42,b'<html>', 'x'*262145])
def test_invalid_or_oversize_html_rejected_before_parser(html):
 with pytest.raises(ValueError,match='invalid_metadata_input'):extract(html)


def test_oversize_multibyte_input_uses_byte_limit():
 with pytest.raises(ValueError,match='invalid_metadata_input'):extract('字'*90000)

@pytest.mark.parametrize('url',['http://news.maker.example/x','https://127.0.0.1/x','https://news.maker.example/\nrelease'])
def test_final_url_must_pass_existing_public_https_shape_boundary(url):
 with pytest.raises(ValueError,match='invalid_metadata_input'):
  extract_metadata_candidates('',final_url=url)


def test_malformed_or_deep_json_is_ignored_not_partially_upgraded():
 assert extract('<script type="application/ld+json">{broken</script>').publications==()
 payload='['*80+'{"@type":"NewsArticle","datePublished":"2026-03-03"}'+']'*80
 assert extract('<script type="application/ld+json">'+payload+'</script>').publications==()


def test_candidate_count_is_bounded_and_oversupply_rejected():
 with pytest.raises(ValueError,match='metadata_candidate_limit'):
  extract(''.join('<meta name="date" content="2026-03-03">' for _ in range(33)))


def test_result_is_immutable_and_empty_html_is_honest_uncertainty():
 row=extract('')
 assert row.publications==() and row.canonical_urls==()
 with pytest.raises((AttributeError,TypeError)):row.final_url='other'

@pytest.mark.parametrize('html',['\ud800','<meta name="date" content="\udfff">'])
def test_invalid_unicode_rejected_with_boundary_error(html):
 with pytest.raises(ValueError,match='invalid_metadata_input'):extract(html)


def test_nested_script_data_and_deep_payload_cannot_publish_partial_candidates():
 payload='{"@type":"NewsArticle","datePublished":"2026-03-03","nested":'+'['*80+'0'+']'*80+'}'
 row=extract('<script type="application/ld+json">'+payload+'</script>')
 assert row.publications==()


def test_multiple_article_objects_preserve_each_candidate_without_identity_binding():
 row=extract('''<script type="application/ld+json">[{"@type":["Thing","NewsArticle"],"datePublished":"2026-03-03"},{"@type":"NewsArticle","datePublished":"2026-03-04"}]</script>''')
 assert {p.raw for p in row.publications}=={'2026-03-03','2026-03-04'}
 assert row.ambiguous_publication

@pytest.mark.parametrize('html',[
 '<meta name>', '<script type></script>', '<link rel>',
 '<link rel="CANONICAL" href>', '<meta name="date" content>',
 '<script type="application/ld+json">{"@type":"NewsArticle","datePublished":null}</script>',
])
def test_valueless_html_attributes_or_null_json_remain_unverified(html):
 row=extract(html)
 assert row.publications==() and row.canonical_urls==()

@pytest.mark.parametrize('payload',[
 '{"@type":"NewsArticle","datePublished":"2026-03-03","datePublished":"2026-03-04"}',
 '{"@type":"Product","@type":"NewsArticle","datePublished":"2026-03-03"}',
 '{"@graph":[],"@graph":[{"@type":"NewsArticle","datePublished":"2026-03-03"}]}',
])
def test_duplicate_json_fields_fail_closed_instead_of_last_value_wins(payload):
 row=extract('<script type="application/ld+json">'+payload+'</script>')
 assert row.publications==()

@pytest.mark.parametrize('html',[
 '<meta name="ignore" name="date" content="2026-03-03">',
 '<script type="text/plain" type="application/ld+json">{"@type":"NewsArticle","datePublished":"2026-03-03"}</script>',
 '<link rel="alternate" rel="canonical" href="https://news.maker.example/release">',
])
def test_duplicate_html_attributes_do_not_resolve_by_last_value_wins(html):
 row=extract(html)
 assert row.publications==() and row.canonical_urls==()
