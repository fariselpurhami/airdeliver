# Weak CPU search budget

Owner runtime evidence:5s staged search expired before GTE native query embedding
finished18.54s. Health was ready. Other queries2.39s and warmup variable. CPU/RAM
contention between API/worker is plausible, not measured proof. Owner ultimately
requires few-seconds responses on2019Intel16GB, not longer waiting. Unshipped
35s/120s deadline experiment was reverted, no production budget raised.

## Changes

Keyword search starts independently of semantic encoding, both in parallel.
Semantic encode+Milvus enrichment gets validated SEARCH_EMBEDDING_BUDGET_SECONDS,
default1.5s, max3s. If semantic misses its subdeadline, existing OpenSearch/SQL
candidate fallback can continue, not discard a completed lexical result because
GTE is slow. Hard product constraints, currentSQLhydration, model prose/review
unchanged. SQL no-match remains no-match, not invented similarity or spec.

Native thread cancellation cannot stop inference. Existing shared model gate
stays held until actual completion; subsequent requests do not launch overlapping
native work. Successful vectors including late completion go to per-engine,
process-local128entry10minuteTTL cache. Key includes model object identity,
modelname/revision/dimension/queryprompt and sanitizedquery; immutable stored
vectors, finite/dimension/nonzero validation. No price/stock/customer profile cached.
Search-ID cache key now also binds retrieval contract so switches do not reuse
old rankings, while productfacts always come from currentSQL.

Not a distributed worker/API inference service. Does not eliminate duplicate
resident models or guarantee CPU scheduling latency. Granite pinned document and
query contract is the selected hardware-fit path; do not mix query models into
GTEspace. Owner measuredGranite~84ms median in synthetic benchmark, not appp99.
All query/cache timing still needs real app acceptance after controlledcutover.

All sink/overall deadlines remain existingbounds, so slow keyword/DB may still
fail tier. This is not a total-response few-seconds guarantee: routing, multiple
targets and provider writer/review latency/quota remain separate limits. Logs
separate semantic enrichment timeout from provider failures; don't claim quality
acceptance or quota fix from this change.

Actual boundary tests: delayednativeencoder, keywordbranchstartswithoutwaiting,
SQLfallbackreturnsundertestbudget, secondquerycannotspawnanothernativeencode,
latevectorcachehitwithoutrecompute, bounds/TTL/copy/invalidvectorrejection.
No provider/model calls or ownerexecution. Canonical55liveacceptance unchanged.
