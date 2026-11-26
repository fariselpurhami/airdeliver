"""Inactive bounded original-HTML metadata candidates, never verified sources.

No requests, redirects, publisher entries, model/region bindings or status
assertions. Canonical URLs are untrusted candidates and are never followed.
Publication conflicts are retained rather than resolved by newest-wins.
"""
from dataclasses import dataclass
from html.parser import HTMLParser
import json
from app.services.product_knowledge_service import allowed_url
from app.services.research.source_date_precision import ParsedPublication,parse_source_publication


@dataclass(frozen=True)
class MetadataCandidates:
    final_url:str
    canonical_urls:tuple[str,...]
    publications:tuple[ParsedPublication,...]

    @property
    def ambiguous_publication(self):return len(self.publications)>1


def _unique_json_object(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('ambiguous_json_object')
        result[key]=value
    return result


class _Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.canonical=[];self.dates=[];self.in_ld=False;self.parts=[];self.count=0

    def candidate(self):
        self.count+=1
        if self.count>32:raise ValueError('metadata_candidate_limit')

    def date(self,raw):
        self.candidate()
        try:value=parse_source_publication(raw)
        except ValueError:return
        if value not in self.dates:self.dates.append(value)

    def handle_starttag(self,tag,attrs):
        if len({key for key,_ in attrs})!=len(attrs):
            if tag=='script':self.in_ld=False;self.parts=[]
            return
        attrs={key:value for key,value in attrs if value is not None}
        if tag=='link' and 'canonical' in attrs.get('rel','').lower().split():
            self.candidate();url=attrs.get('href')
            if isinstance(url,str) and url not in self.canonical:self.canonical.append(url)
        if tag=='meta' and attrs.get('name','').lower()=='date':self.date(attrs.get('content'))
        if tag=='script':
            self.in_ld=attrs.get('type','').lower()=='application/ld+json'
            self.parts=[]

    def handle_data(self,data):
        if self.in_ld:self.parts.append(data)

    def handle_endtag(self,tag):
        if tag!='script' or not self.in_ld:return
        self.in_ld=False
        try:payload=json.loads(''.join(self.parts),object_pairs_hook=_unique_json_object)
        except (ValueError,RecursionError):return
        # Reject the whole JSON payload when depth exceeds the bounded walk.
        stack=[(payload,0)];articles=[]
        while stack:
            obj,depth=stack.pop()
            if depth>16:return
            if isinstance(obj,dict):
                types=obj.get('@type',[])
                if isinstance(types,str):types=[types]
                if isinstance(types,list) and 'NewsArticle' in types and 'datePublished' in obj:
                    articles.append(obj['datePublished'])
                stack.extend((v,depth+1) for v in obj.values() if isinstance(v,(dict,list)))
            elif isinstance(obj,list):stack.extend((v,depth+1) for v in obj if isinstance(v,(dict,list)))
        for value in articles:self.date(value)


def extract_metadata_candidates(html,*,final_url):
    if type(html) is not str or len(html)>262144 or not allowed_url(final_url):
        raise ValueError('invalid_metadata_input')
    try:size=len(html.encode('utf-8'))
    except UnicodeEncodeError as exc:raise ValueError('invalid_metadata_input') from exc
    if size>262144:raise ValueError('invalid_metadata_input')
    parser=_Parser();parser.feed(html);parser.close()
    return MetadataCandidates(final_url,tuple(parser.canonical),tuple(parser.dates))
