# Dev object-store outage and worker readiness, 2026-11-24

## Evidence and limits

Owner-reported inspection showed the RustFS container named `airdeliver-minio` exited with code0 at00:06:25 UTC and inherited `on-failure`. Milvus had restarted14 times while object storage was unavailable. Etcd finished near the same time and restarted. This establishes the missing object store at inspection time, not what originally stopped the containers. Current `OOMKilled=false` does not rule out earlier memory events. No storage deletion or reset is justified.

Dev Compose keeps the matching persistent set: `rustfs-data:/data`, `etcd-data:/etcd`, `milvus-data:/var/lib/milvus`. A normal container restart does not itself erase named volumes. Wrong volume selection, unavailable objects or metadata, and collection loading still require direct checks. Collection discovery is not proof every vector is loaded.

## Changes

- RustFS explicitly uses `restart: unless-stopped`. Unexpected clean exits can recover; a deliberate manual stop remains stopped.
- Etcd has an `etcdctl endpoint health` probe. Initial Milvus Compose startup waits for healthy etcd and object storage. `depends_on` is not a runtime dependency supervisor and cannot prevent every later Milvus restart loop.
- Worker Milvus SDK connection/retry and schema calls run off the health event loop. Startup remains not-ready until initialization completes.
- Worker logs Milvus stage start/completion. Text warmup logs sample start and an elapsed in-flight heartbeat every30seconds. A pending heartbeat means native encoding is still in flight, not that inference has made useful progress.
- No readiness thresholds, model settings, data, mounts or existing operations were removed.

## Interpreting health

The worker healthcheck still has a390second start period,10second interval,6second timeout and6retries. Failed probes during grace do not count; a successful probe can make it healthy earlier. Continuous failures normally become unhealthy after grace plus the retry sequence. This is separate from the dev20minute warmup and25minute total text-startup budgets. The effective container configuration and health history are the source of truth, not container age alone.

The health server should remain responsive with503 while a Milvus connect attempt blocks. The existing recovery loop retries degraded AI startup after30seconds. Reaching Milvus connection in the initialization sequence means that attempt already passed text initialization. Hybrid request retrieval can degrade to keyword/SQL results on vector failure; worker health is not a continuous Milvus gRPC liveness guarantee.

## Validation

Tests cover actual combined Compose configuration, persistent volume retention, healthy initial dependency gates, a blocked Milvus connector while worker health responds503, and warmup heartbeat cleanup on encoder failure. No owner environment operation, provider call, migration, seeding or secret rotation was performed by this change.
