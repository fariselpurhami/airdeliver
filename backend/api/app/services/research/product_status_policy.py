"""Product-status resolver for trusted, normalized evidence, not model output.

Preparation boundary: not yet wired into product research. official_binding,
exact_identity and supersedes must be established by the application's verified
publisher/identity policy, never accepted from source prose or an LLM verdict.
Fresh retrieval does not make an old announcement current release confirmation.
"""
from dataclasses import dataclass
from datetime import datetime,timedelta
from typing import Literal
from pydantic import BaseModel,ConfigDict,field_validator
from app.services.product_knowledge_service import allowed_url

class StatusEvidence(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True,strict=True)
    model_key:str
    source_url:str
    publisher_key:str
    official_binding:bool
    exact_identity:bool
    assertion:Literal['announced','scheduled_release','released','discontinued']
    observed_at:datetime
    published_at:datetime
    effective_at:datetime
    region:str
    supersedes:tuple[str,...]=()

    @field_validator('observed_at','published_at','effective_at')
    @classmethod
    def aware(cls,value):
        if value.tzinfo is None or value.utcoffset() is None:raise ValueError('timezone_required')
        return value

    @field_validator('source_url')
    @classmethod
    def source_https(cls,value):
        if not allowed_url(value):raise ValueError('invalid_source_url')
        return value

@dataclass(frozen=True)
class ProductStatus:
    state:str
    sources:tuple[str,...]=()
    effective_at:datetime|None=None
    merchant_stock:str='unverified'


def resolve_status(model_key,evidence,*,now,region,max_age):
    if now.tzinfo is None or now.utcoffset() is None or max_age<=timedelta(0):raise ValueError('invalid_status_clock')
    rows=[r for r in evidence if r.model_key==model_key and r.exact_identity and r.official_binding
          and r.region==region and timedelta(0)<=now-r.observed_at<=max_age and r.published_at<=now
          and timedelta(0)<=now-r.published_at<=max_age]
    # Explicit supersession is upstream trusted metadata, never newest-wins.
    superseded={u for r in rows for u in r.supersedes}
    rows=[r for r in rows if r.source_url not in superseded]
    if not rows:return ProductStatus('unverified')
    statuses=set()
    for row in rows:
        if row.assertion=='scheduled_release':
            state='scheduled' if row.effective_at>now else 'schedule_elapsed_unconfirmed'
        elif row.assertion=='released' and row.effective_at>now:
            state='unverified'
        else:state=row.assertion
        statuses.add((state,row.effective_at))
    sources=tuple(dict.fromkeys(r.source_url for r in rows))
    # Different effective dates matter for schedules, not independent reports of
    # an already confirmed release. No inferred nonexistence state is possible.
    states={s for s,_ in statuses}
    if len(states)>1 or ('scheduled' in states and len(statuses)>1):return ProductStatus('conflicting',sources)
    state=next(iter(states));effective=min(r.effective_at for r in rows)
    return ProductStatus(state,sources,effective)
