"""Publisher identity is configured by the application, never by source text."""
import pytest
from app.services.research.publisher_binding import PublisherRegistry, PublisherBinding


def registry():
 return PublisherRegistry((PublisherBinding('maker',('news.maker.example','www.maker.example')),))

@pytest.mark.parametrize('url',['https://news.maker.example/release','https://www.maker.example/products/x'])
def test_exact_https_configured_host_binding(url):
 assert registry().publisher_for(url)=='maker'

@pytest.mark.parametrize('url',[
 'http://news.maker.example/release','https://news.maker.example.attacker.test/release',
 'https://news.maker.example@attacker.test/release','https://attacker.test/?official=maker',
 'https://news.maker.example:444/release','https://other.maker.example/release',
 'https://news.maker.example./release','https://news.maker.example/%0aattack',
 'https://127.0.0.1/release','https://news.maker.example\\@attacker.test/release',
])
def test_similar_unconfigured_or_ambiguous_source_never_binds(url):
 assert registry().publisher_for(url) is None


def test_source_publisher_claim_cannot_select_its_own_binding():
 assert registry().publisher_for('https://attacker.test/official') is None


def test_conflicting_registry_host_rejected():
 with pytest.raises(ValueError):
  PublisherRegistry((PublisherBinding('maker',('news.maker.example',)),PublisherBinding('other',('news.maker.example',))))

@pytest.mark.parametrize('hosts',[('*.maker.example',),('com',),('127.0.0.1',),('https://maker.example',),('maker.example:443',),('maker.example.',)])
def test_invalid_configured_hosts_rejected(hosts):
 with pytest.raises(ValueError):PublisherRegistry((PublisherBinding('maker',hosts),))


def test_empty_registry_is_safe_by_default():
 assert PublisherRegistry(()).publisher_for('https://news.maker.example/release') is None


def test_explicit_default_tls_port_does_not_change_identity():
 assert registry().publisher_for('https://news.maker.example:443/release')=='maker'


def test_binding_does_not_follow_redirect_or_infer_product_identity():
 # The caller must check the final fetched URL independently. No HTTP occurs.
 assert registry().publisher_for('https://redirect.example/?to=news.maker.example') is None
 assert registry().publisher_for('https://news.maker.example/unrelated')=='maker'
