# CAP-26: staged/universal retrieval code acceptance

Active ordinary HTTP targets and setup components use shared staged_search.
Retained NLU informational/universal paths use _execute_strategic_search, which
uses that same service. _execute_search and _legacy_execute_strategic_search
remain source-preserved dormant implementations, not active safe alternatives.
The former's historical budget-relaxation branch is not wired to production.
Published products still require current SQL cards, full hard brief, independent
writer/review and post-copy freshness. Target queries and tier labels are not
product, availability, physical compatibility or semantic-match proof.

Exact tier preserves historical price order; ranked tier reorders retrieved
candidates; broad tier occurs only after an empty high tier and changed query.
Repeating identical empty limit30 retrieval at limit10 cannot add evidence, so
that original redundant mid request remains dormant. Category filter is retained
at every active tier. Query/category/result-size/deadline/broadener shapes now
have explicit bounds. Mapping and object rows share positive nonboolean ID/name
validation; malformed siblings are withheld. Ranking cannot inject or replace a
retrieved row. Nonfinite prices cannot control exact ordering. Results retain
bounded unique identity. Any original multi-target transport failure withholds
the already-collected partial candidate list instead of treating it as full
retrieval; cancellation propagates. Missing matches remain scoped no-match.

Actual SQL/Redis mounted HTTP tests exercise current cards, per-target scope,
setup, stale mutation, timeout and exclusions. New transport tests exercise
mapping rows, malformed/oversize payloads, wrong query/category/timeout,
nonfinite values, rank injection, broad cancellation and original universal
partial-outage/cancel handling, plus invalid strategic query containers.71 focused
cases pass. All2221 then-collected cases covered on disposable PostgreSQL19/
realRedis:1107passed/3skipped and1109passed/4skipped with2bootstrap duplicates.
The final3 added strategic-container cases pass in the focused run, bringing
collection to2224. No unexpected failures.

Code completion requires exact-head scan and both storage jobs plus fast-forward.
Live multilingual relevance, extraction/assignment quality and actual merchant
index/model alignment remain unverified and parked. No provider/owner calls.
