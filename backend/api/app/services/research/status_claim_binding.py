"""Normalize reviewed status extraction against trusted source metadata and quotes.

No fetching or publisher configuration is performed here. The source adapter owns
verified publication time, model bindings and region; search-result metadata and
page/model self-claims must never populate those fields directly.
"""
from dataclasses import dataclass
from datetime import datetime
from pydantic import BaseModel,ConfigDict,Field,StrictInt,StrictStr
from typing import Literal
from app.services.research.product_status_policy import StatusEvidence


@dataclass(frozen=True)
class VerifiedStatusSource:
    final_url:str
    text:str
    observed_at:datetime
    published_at:datetime
    region:str
    exact_models:tuple[str,...]


def validate_status_source(source):
    """Validate adapter metadata shape, never authenticate its origin."""
    if not isinstance(source,VerifiedStatusSource):raise ValueError('verified_metadata_required')
    dates=(source.observed_at,source.published_at)
    if (not isinstance(source.text,str) or not 1<=len(source.text)<=6000
        or not isinstance(source.final_url,str)
        or not isinstance(source.region,str) or not source.region.strip()
        or not isinstance(source.exact_models,tuple) or not source.exact_models
        or any(not isinstance(key,str) or not key.strip() for key in source.exact_models)
        or len(set(source.exact_models))!=len(source.exact_models)
        or any(not isinstance(d,datetime) or d.tzinfo is None or d.utcoffset() is None for d in dates)):
        raise ValueError('verified_metadata_required')


class ExtractedStatus(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    source:StrictInt=Field(ge=0,le=8)
    model_key:StrictStr
    assertion:Literal['announced','scheduled_release','released','discontinued']
    effective_iso:StrictStr
    quote:StrictStr=Field(min_length=2,max_length=1200)


def _normalize_status_claim(claim,sources,registry):
    if not isinstance(claim,ExtractedStatus) or claim.source>=len(sources):raise ValueError('invalid_status_source')
    source=sources[claim.source]
    if not isinstance(source,VerifiedStatusSource):raise ValueError('verified_metadata_required')
    publisher=registry.publisher_for(source.final_url)
    if publisher is None:raise ValueError('unbound_status_publisher')
    if claim.model_key not in source.exact_models:raise ValueError('unbound_status_model')
    if claim.quote not in source.text:raise ValueError('unsupported_status_quote')
    # An ISO effective instant must appear verbatim in the supporting excerpt.
    # Broader natural-language date normalization needs its own verified adapter.
    if claim.effective_iso not in claim.quote:raise ValueError('unsupported_effective_instant')
    try:instant=datetime.fromisoformat(claim.effective_iso)
    except ValueError as exc:raise ValueError('invalid_effective_instant') from exc
    return StatusEvidence(model_key=claim.model_key,source_url=source.final_url,
        publisher_key=publisher,official_binding=True,exact_identity=True,
        assertion=claim.assertion,observed_at=source.observed_at,
        published_at=source.published_at,effective_at=instant,region=source.region)


def validate_status_claim(claim,sources,registry):
    """Validate exact evidence shape without claiming independent review.

    Returns no publishable evidence. Semantic entailment is a later review step.
    """
    _normalize_status_claim(claim,sources,registry)


def bind_status_claim(claim,sources,registry,*,reviewed):
    if reviewed is not True:raise ValueError('status_review_required')
    return _normalize_status_claim(claim,sources,registry)
