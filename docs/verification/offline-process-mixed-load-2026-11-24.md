# Offline mixed-process characterization, November24

This closes only the local synthetic real-process measurement gap. It does not
close full application, provider, model, owner-hardware or remote-Redis acceptance.
Raw numeric summaries accompany this file as JSON. Do not interpret them as an SLO.

## Boundary measured

A separate Uvicorn process handles actual loopback HTTP, using the production
async Redis limiter, actual disposable Redis7.4.2, SQLAlchemy/asyncpg against
disposable PostgreSQL19, the existing strict FreeLLMService adapter with a
controlled12ms async completion transport, and JSON serialization of100 SQL rows.
No application production handlers, loaded retrieval models, provider transport or
external merchant/source services are executed. SQL is generate_series and md5,
not production catalog queries/indexes/data. Loopback admission is not WAN Redis.

Two runs each send2000 requests, concurrency32. Latency starts after taking a
client concurrency slot, so excludes the waiting client backlog. It includes
HTTP transport, limiter queue/EVAL, SQL checkout/query, controlled adapter delay,
serialization and response reading. No timed warmup calls. App startup and
pre-measurement GC collection are outside request latency. Heartbeat5ms target
measures observed gaps, not exact scheduler lateness. GC callbacks stay active
throughout; Python's imported runtime threshold2000/10/10 is reported, not changed
by this harness. Allocation mode adds200 cyclic containers per request to provoke
natural GC. No timed explicit collections, GC disable or threshold tuning.

Both runs returned200 for all2000 requests, no HTTP errors. Exact results live in
the JSON because local timing is variable. A second run with outbound sockets
blocked except loopback/Unix services also passed. The model completion is fake
by explicit harness design, never a user-facing fallback. No provider request was
made. No saved database, owner system or deployed service was touched.

## Reproduce

Run the normal test bootstrap against disposable PostgreSQL and Redis only.
`TEST_POSTGRES_DSN` must name a disposable database. The normal PG verification
wrapper can provision/migrate its own throwaway database. Set
`TEST_REDIS_SERVER_BIN` to a local Redis binary if not on PATH.

```text
RUN_OFFLINE_PROCESS_BENCHMARK=1 poetry run pytest -q -s tests/test_offline_mixed_process.py
```

Run from apps/api, with the existing test environment. The test is deliberately
opt-in rather than a universal timing gate. Each test owns and stops its child
Uvicorn process and disposable Redis. Results default to
/tmp/offline-mixed-process; OFFLINE_BENCH_OUTPUT can change that artifact path.
The normal test wrapper owns PostgreSQL cleanup. No app startup or migration is
run by the harness itself. Logs and full GC/heartbeat samples are local artifacts.

## Gates retained

The required isolated150-request benchmark still requires exactly100 admissions,
50 quota rejections, heartbeat gap under0.2seconds, with GC enabled. This separate
characterization does not replace or weaken it. All5 existing async limiter tests
passed again, including fail-closed pause/recovery and no uncertain INCR replay.
The required CI step and production limiter are unchanged.

## Remaining risk

Full app mixed traffic, actual catalog SQL/vector retrieval, real model inference,
real Groq/source latency, owner CPU/memory pressure and remote Redis tail behavior
remain unmeasured. A41ms or other observed natural GC pause is evidence that the
process can pause, not a bound for another load or machine. The limiter's1second
budget cannot make the event loop responsive during a stop-the-world pause.
No live acceptance flags or canonical55 classification changed.
