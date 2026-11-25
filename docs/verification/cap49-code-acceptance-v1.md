# CAP-49: image identification and optional enrichment code acceptance

Both current image-identification callers are inventoried: NeuralCore visual
search and the retained NLU image route. They treat the returned text as a
retrieval hint, not product identity, availability or card evidence. Their
existing current-SQL/brief/publication gates remain. The optional title adapter
uses CAP50's bounded async transport, URL validation and cancellation cleanup.

The image hint boundary now validates encoded byte size, strict base64, basic
supported format signature and data-URI MIME agreement before calling a model.
PNG/WebP/GIF payloads are no longer labeled JPEG. This is a transport signature
check, not full image decoding: the vector/image decoder's separate pixel/edge
and native-lifetime gates remain authoritative for local decoding.

Vision responses require bounded literal text and cannot publish truncated,
non-string, URL/markup or empty hints. Optional enrichment failure/timeout keeps
the original bounded hint. Cancellation propagates from model and enrichment.
Malformed title output cannot be stringified into hints. Error logs no longer
include remote payload tracebacks. Current callers, synchronous foundation,
model selection and quotas are unchanged; no provider calls were made.

Controlled acceptance:2126collected cases covered on disposable PostgreSQL19
with real Redis in two splits1060passed/3skipped and1061passed/4skipped, two
bootstrap cases duplicated. New cases cover malformed payloads/MIME, optional
search enable/disable, bad/truncated output, provider outage, cancel and title
failure. Existing visual/current-card/decoder tests cover the downstream gates.

Code complete is subject to exact-head CI and merge. Real image recognition,
ranking, adversarial semantics and owner profile remain unverified/parked. No
whole-capability or production-ready claim, no owner-machine action or spend.
