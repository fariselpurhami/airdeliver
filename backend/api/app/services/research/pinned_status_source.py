"""Inactive exact-snapshot integrity adapter, never a metadata verifier.

Pins must be separately established by an application-owned review process.
No pins ship here. A hash binds text to that reviewed record; it cannot prove
that the record's publisher, model, date or region assertions are correct.
Changed text needs a new review, never automatic pin refresh. No fetching.
"""
from dataclasses import dataclass
from datetime import datetime
import hashlib,hmac,re
from app.services.research.publisher_binding import PublisherRegistry
from app.services.research.status_claim_binding import VerifiedStatusSource,validate_status_source


@dataclass(frozen=True)
class StatusSourcePin:
    final_url:str
    publisher_key:str
    content_sha256:str
    published_at:datetime
    region:str
    exact_models:tuple[str,...]


def bind_pinned_status_source(*,final_url,text,observed_at,pin,registry):
    if not isinstance(pin,StatusSourcePin) or not isinstance(registry,PublisherRegistry):
        raise ValueError('reviewed_source_pin_required')
    if (not isinstance(pin.content_sha256,str) or re.fullmatch(r'[0-9a-f]{64}',pin.content_sha256) is None
        or type(text) is not str or final_url!=pin.final_url):
        raise ValueError('source_pin_mismatch')
    publisher=registry.publisher_for(final_url)
    if publisher is None or publisher!=pin.publisher_key:raise ValueError('source_pin_publisher_mismatch')
    if not hmac.compare_digest(hashlib.sha256(text.encode('utf-8')).hexdigest(),pin.content_sha256):
        raise ValueError('source_pin_content_mismatch')
    source=VerifiedStatusSource(final_url,text,observed_at,pin.published_at,pin.region,pin.exact_models)
    validate_status_source(source)
    return source
