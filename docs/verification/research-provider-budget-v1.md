# Research provider budget and cooldown, 2026-11-24

Owner retest: source lookup accepted three pages, then extraction returned a Groq SDK RateLimitError. No source-backed answer was published. Neither a schema success nor a schema failure was observed. Usage charts alone do not identify the rejected request's quota dimension.

## Additive changes

- NeuralCore routing, extraction and review share a per-event-loop, per-model admission lock and cooldown across service instances. One timeout covers admission, retry delay and provider requests. Product research retains its existing outer eight-second deadline for lookup plus both model stages.
- Honor Retry-After seconds or HTTP-date and retry-after-ms. A cooldown longer than the remaining deadline returns without an early retry. Missing reset metadata on 429 imposes a local 60-second minimum cooldown, not a claimed provider reset. No SDK double retry.
- Numeric remaining/limit headers, bounded duration headers and an allowlisted quota-unit classification can be logged. Never log provider exception messages, prompt/source content, keys, organization identifiers or raw headers. Other failure classes remain unchanged.
- Local evidence packing retains contiguous exact UTF-8 windows with relevance overlap, preserves URLs and source positions, and budgets 2,400 UTF-8 bytes across all sources. It does not produce product facts or bypass exact-quote checks and independent model review. Evidence omitted by packing cannot support an answer. Missing evidence may lead to honest withholding.
- Research stages have conservative UTF-8-byte token upper bounds, a framing allowance and explicit output caps. Oversized requests are withheld before network execution. Output caps are 1,200 tokens for extraction and review; other NeuralCore stages use 2,048. No model selection changes.

## Limits, deliberately not claimed

This is process-local admission, NOT a cross-worker, cross-project or organization-wide token ledger. Other applications can consume the same organization quota. It does not guarantee every whole conversation fits a free minute quota. A real per-model local tokenizer and coordinated usage reservations need separate design; no tokenizer download was made. The conservative input bound applies only to research stages, not the larger historical router schema. A UTF-8 byte bound is not measured token usage. A 7,800-token local per-request ceiling is a conservative engineering limit, not the account's verified current entitlement. Account-specific lower limits can still reject a request.

Extraction and review caps include the provider's output budget; a cap can reduce response completeness. Truncation/schema failures must withhold rather than invent a reply. No claim that the old full-page result quality is preserved without live evaluation. Fixtures and model benchmark work are separate.

## Verification and owner retest

Offline tests cover native Groq SDK over real loopback HTTP, 429 long reset, short reset, shared admission, cancellation/queue deadline, safe metadata, oversized multilingual input, exact contiguous source windows, and the actual extraction/review strict-schema path. Scripted local responses are not provider acceptance evidence.

Ask the owner to inspect the same project's Organization Limits and the failed log entry around 2026-11-24 10:07 UTC. No new API request is needed to inspect those. Retest only after the reported reset with enough remaining quota, once. One UI question can use routing, extraction and review calls. Do not promise that 90 seconds fixes daily quotas or oversized input. No provider call, spending, model switch, deployment, reindex or fixture mutation was performed during development.

Sources read:
- https://console.groq.com/docs/rate-limits
- https://console.groq.com/docs/errors
- https://console.groq.com/settings/limits
- https://console.groq.com/dashboard/logs

All canonical live-qualified flags remain false. This is a narrow restoration checkpoint, not production parity.
