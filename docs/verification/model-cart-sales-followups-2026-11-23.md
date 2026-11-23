# Model cart sales follow-ups

November 23, 2026. Builds on PR36 shared sales orchestration.

## Active path

Both HTTP and worker cart mutations publish the existing read-only recommendation event after persistence. The worker consumer keeps existing bundle and alternative retrieval, then calls CartSalesService and the shared writer plus independent review. FreeLLMService exposes a strict JSON adapter through its existing admission/retry/deadline transport. Provider failure is not converted to successful empty prose on this path.

Fixed cart confirmations remain. Sales prose and cards are published only when the model and review succeed. Optional provider failure does not undo, delay or replay the cart mutation. The former rich direct copy methods and old optional consumer are preserved as explicit legacy implementations, not deleted. A named constructor switch permits explicit legacy characterization; default traffic uses the shared follow-up path.

## Evidence and stale-result gates

- Fresh PostgreSQL rows, not cached/index product snapshots, before generation and again after writer/review await.
- Active, positive local stock, non-demo, valid USD-priced candidates only.
- Added-item suggestions require the existing catalog complement assertion and the existing engine price window. This does not prove physical compatibility.
- Removal alternatives retain same-category and engine price-window rules. The removed item's price is not represented as the customer's budget or removal reason.
- Cart membership is checked before search, after search and after model work. A changed cart suppresses delayed advice.
- Structured cards carry local catalog provenance and explicitly unverified merchant stock. No automatic cart mutation.
- No customer language is stored on the event today. Follow-ups use concise English rather than claiming language personalization. Connecting consented conversation context is a later plan step.

## Verification

Disposable PostgreSQL 19 migrated through repository head, real Redis, actual worker consumer and UI publication serialization. Controlled boundaries are catalog retrieval ordering and model transport; no provider was contacted. Coverage includes both operations, demo exclusion, inflight price/stock/activity/relation/deletion changes, cart change, rejected review, provider error and deadline error. Transport tests verify strict JSON and failure propagation, and both injected-AI mutation paths are checked to avoid model/search work on the mutation critical path.

Earlier AMQP/legacy tests remain as characterization of the preserved optional adapter. New production behavior is tested at the worker/SQL/Redis boundaries. Hosted CI additionally runs the broker and both storage matrices.

No owner-machine operations, deployment, migration rollout, seeded data changes, payments, email or live provider calls. Source-level tests do not verify live bilingual prose quality, provider latency, supplier stock or deployed workers.
