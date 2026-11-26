"""Reviewed publisher allowlist for product status evidence, per market region.

Inactive preparation: nothing here fetches pages or calls a provider. A match
proves only that a URL is on a reviewed host (and region path where required);
it does not prove the page's product, date or claim. Only the US region is
configured now, as approved by the owner; add a region by adding data to
REGION_SOURCES, not by changing code.
"""
from dataclasses import dataclass
from urllib.parse import urlsplit
import re
from app.services.research.publisher_binding import valid_host

TIER_CLAIMS={1:frozenset({'release','price','availability','announcement'}),
             2:frozenset({'release','announcement'}),
             3:frozenset({'certification'})}


@dataclass(frozen=True)
class Source:
    key:str
    tier:int
    host:str
    path_prefix:str='/'
    brand:str|None=None  # tier 1 hosts are valid only for their own brand


@dataclass(frozen=True)
class Classified:
    key:str
    tier:int
    claims:frozenset
    brand:str|None
    region:str


def _t1(brand,host,prefix='/'):return Source(brand,1,host,prefix,brand)
def _t2(key,host):return Source(key,2,host)

REGION_SOURCES={
 'US':(
  _t1('apple','www.apple.com'),_t1('apple','support.apple.com'),
  _t1('samsung','www.samsung.com','/us/'),
  _t1('sony','electronics.sony.com'),
  _t1('lg','www.lg.com','/us/'),
  _t1('dell','www.dell.com','/en-us/'),
  _t1('hp','www.hp.com','/us-en/'),
  _t1('lenovo','www.lenovo.com','/us/en/'),
  _t1('logitech','www.logitech.com','/en-us/'),
  _t1('xiaomi','www.mi.com','/us/'),
  _t2('theverge','www.theverge.com'),_t2('arstechnica','arstechnica.com'),
  _t2('engadget','www.engadget.com'),_t2('techcrunch','techcrunch.com'),
  _t2('cnet','www.cnet.com'),_t2('tomsguide','www.tomsguide.com'),
  _t2('gsmarena','www.gsmarena.com'),_t2('notebookcheck','www.notebookcheck.net'),
  _t2('rtings','www.rtings.com'),
  Source('fcc',3,'www.fcc.gov'),
 ),
}


def us_status_sources():return REGION_SOURCES['US']


class UsStatusPolicy:
    """Region-parametrised policy; name kept for the US-first configuration."""
    def __init__(self,sources,region='US'):
        seen=set()
        for s in sources:
            if s.tier not in TIER_CLAIMS or not valid_host(s.host) or not s.path_prefix.startswith('/'):raise ValueError('invalid_source')
            if s.tier==1 and not s.brand:raise ValueError('tier1_needs_brand')
            if (s.host,s.path_prefix) in seen:raise ValueError('duplicate_source')
            seen.add((s.host,s.path_prefix))
        self._sources=tuple(sources);self.region=region

    def classify(self,url):
        if type(url) is not str or not 0<len(url)<=2048 or re.search(r'[\x00-\x20\x7f\\]',url):return None
        try:
            p=urlsplit(url)
            if p.scheme!='https' or p.username is not None or p.password is not None or p.port not in {None,443}:return None
            host=p.hostname
        except ValueError:return None
        if not valid_host(host):return None
        path=p.path or '/'
        if re.search(r'%(?:2e|2f|5c|00)',path,re.I) or '/../' in path+'/':return None
        for s in self._sources:
            if s.host==host and path.startswith(s.path_prefix):
                return Classified(s.key,s.tier,TIER_CLAIMS[s.tier],s.brand,self.region)
        return None

    def brand_matches(self,url,brand):
        c=self.classify(url)
        return c is not None and (c.tier!=1 or c.brand==brand)


def policy_for_region(region):
    if region not in REGION_SOURCES:raise ValueError('region_not_configured')
    return UsStatusPolicy(REGION_SOURCES[region],region)
