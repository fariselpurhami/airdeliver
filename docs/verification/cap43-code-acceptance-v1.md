# CAP-43: client/native/admission lifecycle code acceptance

Current HTTP already installs one request-local turn budget. Retained NLU
process_message and direct opening entrypoint now do too, reusing a nested
budget rather than resetting it. Existing6-call/16000-estimated-token limits
remain unchanged. Local turn estimates are not tokenizer/cost measurements;
shared Redis model ledger remains cross-worker admission, reservations survive
unknown/failed requests and successful reported usage reconciles them. Missing
Redis uses existing process-local model serialization; configured Redis failure
does not bypass shared limits. No deferred scheduling, priority, reduced review
or quota-policy redesign is introduced. Synchronous writer/reviewer remains.

Request-scoped NeuralCore provider client is closed by its dependency generator.
Existing FreeLLM singleton now has lazy/idempotent close; API shutdown and worker
resource close invoke it without creating a new provider connection. Existing
OpenSearch generator/worker HTTP close and Milvus bounded retry contracts remain.
Native embedding/vision/vector gates retain slots until actual worker completion,
not merely caller timeout, with shielded native work and finally-owned resources.
Native process/model stack persists for process lifetime by design; there is no
new unloading or live model-version/accuracy claim.

55 focused cases pass across actual local HTTP OpenSearch connection close,
real Redis serialization/reconciliation/cooldown/cancel/independent owners,
provider local transport deadlines/retries, nested entrypoint budgets, actual
request dependency close and singleton/worker shutdown. Existing native admission
and mixed-process controlled tests are in full regression. These do not prove
whole-app distributed latency, external quota calibration or owner hardware SLO.
All2273collected covered on3fresh disposable PostgreSQL19/realRedis runs:
755pass2skip,755pass3skip,758pass2skip with2bootstrap duplicates. Live provider/owner work is
parked. Code closure requires latest-head scan/both storage jobs and fast-forward.
