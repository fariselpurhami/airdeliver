# CAP-50: Tavily search code acceptance

Active caller inventory:
- Product research: lookup_product_sources uses bounded async transport, URL and
  source shape checks, no provider-generated answer, exact quote/schema/review.
- FreeLLMService._perform_web_search: legacy NLU recovery web wrapper, retained
  old consultation body and voice phantom-product tool. The wrapper now returns
  only attributed, bounded untrusted excerpts, never Tavily's synthetic answer.
  Voice's own behavior is unchanged; web transport is shared infrastructure.
- FreeLLMService._perform_tavily_title_lookup: optional image search enrichment.
  A valid URL and literal string title are required; hint is not identity proof.

Original sync SDK methods are preserved under explicit legacy names, with no
active application caller. All active routes now share async fixed-endpoint
transport. No detached sync thread continues after cancellation. One total
request deadline includes stream reading; response limit is128KiB decoded,
result count3, excerpt6k (raw wrapper2k), no redirects, no search-generated
summary. Current URL policy excludes credentials, plain HTTP, IP literals,
internal/local hosts and nonstandard ports. URLs are source labels, never
fetched by this boundary. Malformed top-level/results/items/text are rejected
or excluded, duplicate sources deduplicated. Logs carry error class, not raw
query, remote error payload or secret. HTTP status errors retain research's
auth/rate-limit/server notices. No retries, new fallback provider or cost grant.

Controlled verification covers fixed request/provenance, malformed types, URL
policy, duplicate rows, HTTP failures, oversize/cancel/deadline stream close,
optional title types and retained-body tripwires. The2104collected-case suite
was covered in disposable PostgreSQL19/realRedis splits1049pass/3skip and
1050pass/4skip, two bootstrap cases duplicated. Two additional lifetime/audit
cases pass focused. This is source/transport code acceptance only, subject to
exact-head scan, both storage jobs and merge. Actual source relevance/semantic
entailment and owner runtime remain parked and unverified. No provider calls,
owner-machine execution, voice-model work or spending performed.
