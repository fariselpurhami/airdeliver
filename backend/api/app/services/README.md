# Service ownership

- conversation: NLU, reviewed product copy, opening, planning and answer orchestration.
- catalog: catalog visibility, commerce/search clients, serialization and import.
- cart: existing cart operations, journal, reconciliation and read-only sales follow-up.
- checkout: checkout orchestration and bounded quote preparation.
- payments: gateways, completion and durable payment event delivery.
- memory: customer consent, shopping memory, erasure and generation fences.
- behavior: existing model artifacts, training, experimentation and gamification.
- retrieval: staged retrieval, embedding warmup and query-vector caching.
- research: product sources, bounded evidence and search transport.
- provider_capacity: quota/admission, usage, diagnostics and capacity evidence.
- infrastructure: cache, broker and notification adapters.
- observability: currency-separated admin payment metrics.

Legacy app.services.<module> imports are compatibility entrypoints. They refer to
exactly the same module objects as the canonical domain imports, preserving
shared state and existing callers. Do not create a second implementation there.
The original voice service stays at its established path until the separate,
owner-directed voice phase. Domain ownership is not feature/live certification.
