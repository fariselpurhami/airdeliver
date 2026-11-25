# P05 million-record catalog benchmark preparation

Baseline b2874748691431206f6de6dcd0e62ec96a1b0674. Accepted target is one million product records, not one million concurrent users. Concurrent users are a separate experiment. The one-second response goal remains a goal, not a demonstrated property. No dataset was generated or loaded, no model downloaded, no store/index changed and no live provider called in this preparation.

## Separate measurements

1. **Catalog capacity and correctness:** authoritative PostgreSQL count, active/eligible counts, unique SKU/ID reconciliation, missing/extra/duplicate IDs in OpenSearch and Milvus, exact vector dimension/model/revision, index readiness, storage growth and rebuild time. Equal counts alone cannot prove equal identities.
2. **Retrieval latency and quality:** actual mounted application retrieval, lexical/dense/fusion ablations, category/price/stock/attribute constraints, English and Arabic, exact-model and ambiguous names, misspellings, no-match and unsupported-spec cases. Preserve honest abstention. Do not use random vectors to claim learned relevance.
3. **Full HTTP chat:** time from client request to complete usable reply, provider/routing/review/serialization stages, first useful output separately from completion, correctness and truthful failures. Provider-free mock time is only an application overhead control, not AI response speed.
4. **Concurrency:** fixed million-record state with independently chosen request arrival rate, simultaneous users, think time, session mix, ramp/soak duration and cancellation behavior. User count is not requests per second. Do not infer it from store counts.

## Staged isolated protocol

- Start with a small synthetic smoke set, then 10k, 100k and one million records. Every stage uses a distinct approved disposable namespace and manifests. Never repurpose production/development volumes or overwrite the owner's existing catalog. Generating/loading a large fixture or index remains a separately authorized execution step.
- Preserve the active model/revision/dimension and importer serialization. Existing `catalog_contract.py` defaults to GTE1536; a smaller offline model is only a separately labelled control. Do not switch profiles to make a benchmark look faster.
- Freeze deterministic dataset source, generation version/seed, SHA256, field-size distributions, categories, languages, inactive/out-of-stock proportions, price distributions and provenance. Label all products synthetic and non-offers. Duplicating one thousand products a thousand times can measure storage mechanics, not realistic semantic quality.
- Keep dev and held-out query sets separate. Existing retrieval labels are draft, not owner-adjudicated acceptance. Freeze labels and no-match policy before measuring; never tune on the held-out set. Count hard-constraint violations and bad recommendations, not only top-k recall.
- Record exact hardware/architecture, OS/container/image revisions, CPU/RAM/cgroup limits, swap, storage medium/free space/IO, network topology, store versions/configuration, index parameters, replicas, thread/batch limits, model cache and state. Estimate disk/RAM headroom before each larger stage. Stop on pressure, eviction, disk thresholds or uncontrolled service degradation.
- Capture cold startup/index-load and warm steady-state separately. Declare warm-up requests, cache state, fixed sample count, concurrency, offered rate and timeout. Keep every error/timeout/cancellation in denominator and latency summaries. Report p50/p95/p99/max and error counts, not averages alone. Do not silently drop provider queue time.
- Measure CPU/RSS/cgroup peak/swap/IO and per-store/index storage alongside timing. Store full run manifest, compact per-request timings, failed case IDs and source receipts without customer text, tokens or credentials.
- After each stage reconcile SQL/search/vector identities and exact schema/dimensions. Do not run a larger stage after a failed correctness or resource check. Retain run evidence; cleanup needs its own exact scope and must not delete shared volumes.

## Offline evidence checker

`backend/api/scripts/catalog_scale_evidence.py` reads only a supplied JSON artifact. It cannot seed, index, connect to a database, run a model or load-test anything. It requires exact revision/dataset/model identity, equal positive reported counts for all three stores, declared scope/concurrency/warm-up, nonempty requests with supported statuses and finite nonnegative latency. It includes failures in all percentiles, reports their denominator and always sets `production_accepted=false`.

`reported_counts_equal_million` means exactly what its name says, not that this helper independently checked a store. Original count/ID reconciliation receipts are still required. `one_second_observed_all_requests` is descriptive of the submitted rows, not an SLA or a pass on response quality. Even an all-green latency sample cannot prove arbitrary future traffic.

Test-first: twelve cases failed because the helper did not exist. After implementation all twelve pass, including malformed/missing latency, NaN/bool/negative values, hidden status, mismatched counts and smaller-catalog non-claims. Compatibility run with the existing embedding benchmark tests: 27 passed. No million-record measurement has occurred.

## Execution and acceptance gates

Before store execution, obtain exact disposable environment/namespace, allowed synthetic seed/index/model execution, resource/time/disk ceilings, stop conditions and cleanup scope. Current CI synthetic exception must not be stretched to an unbounded million-record run. Live AI calls remain within their separately approved budget, currently stopped. A full-stack model response run needs a new bounded plan, not a hidden automatic retry loop.

Owner acceptance needs original run receipts, identity reconciliation, relevance/constraint/no-match results, error/latency/resource distributions at the agreed workload, restored rollback route and explicit review of remaining gaps. No claim of millions of users, production readiness or one-second general performance is supported by this preparation.
