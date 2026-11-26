"""Browser-style legacy IPv4 spellings must not pass as public source DNS."""
import pytest
from app.services.product_knowledge_service import allowed_url
from app.services.research.publisher_binding import valid_host,PublisherBinding,PublisherRegistry

@pytest.mark.parametrize('host',[
 '127.1','127.0.1','0177.0.0.1','0x7f.0.0.1','0x7f.1',
 '0.0.0.0','10.1','169.254.1','192.168.1','0300.0250.0.1',
 '8.8.8.8','010.010.010.010',
])
def test_legacy_numeric_address_is_not_public_dns_source_or_publisher(host):
 assert not allowed_url('https://'+host+'/source')
 assert not valid_host(host)
 with pytest.raises(ValueError):PublisherRegistry((PublisherBinding('maker',(host,)),))

@pytest.mark.parametrize('host',['maker.example','v2.maker.example','127-1.maker.example','xn--bcher-kva.example'])
def test_ordinary_dns_digit_labels_and_punycode_remain_allowed(host):
 assert allowed_url('https://'+host+'/source') and valid_host(host)

@pytest.mark.parametrize('url',['https://@maker.example/a','https://:@maker.example/a','https://:password@maker.example/a'])
def test_any_explicit_userinfo_is_rejected_even_empty_username(url):
 assert not allowed_url(url)
