# P01 local-first deployment boundary and cloud-neutral preparation

Baseline: b2874748691431206f6de6dcd0e62ec96a1b0674. Planning only. Local operation continues; no cloud account, resource, bill, deploy, migration, seed, index rebuild or runtime configuration change is performed here. Future object storage remains on the existing S3 direction. Cloud-neutral means portable operational boundaries, not a promise that every S3-compatible provider is supported.

## Source-grounded present state

| Boundary | Current tracked implementation | What is not established |
| --- | --- | --- |
| Normal local composition | `scripts/dev_compose_quiet_volumes.py` uses base plus dev Compose, ignored `.env.dev`, project `airdeliver_dev` | Fresh machine performance and available RAM/disk are not measured by reading configuration |
| Object/vector storage | `docs/architecture/object-storage.md`, base Compose and `infra/s3` separate local RustFS from future AWS S3; Milvus keeps the internal MINIO_* adapter names | Local compatibility is not AWS IAM/TLS/egress proof or HA. Changing endpoint does not migrate data |
| API start dependency | Base `api-migrator` runs Alembic upgrade followed by `app.db.initial_data`; API depends on successful completion | A generic `compose up` is not a non-mutating production preflight. Do not run it against an unapproved database |
| Persistent state | PostgreSQL, OpenSearch, etcd/Milvus/object data, RabbitMQ, Redis, API storage and certificate volumes appear in base Compose | Declared volumes do not prove backups, restore correctness, replication or retention |
| Edge and web | Traefik TLS configuration, Next frontend, API service and internal network already exist | DNS/account ownership, certificate issuance, final deployed-host trust, payment/PWA/voice journeys remain unverified |
| Observability | Prometheus, Loki, Promtail, Grafana and container metrics are in base Compose | Agent-owned redaction does not certify proxy/third-party logs, alert delivery or retention |
| Kubernetes | Existing manifests include standalone stateful components | Manifests are not evidence of a running multi-AZ cluster. The old DR document's targets are not an achieved SLA |

## Environment contract, portable without premature provider choice

Keep one explicit configuration record per environment: immutable application/image revision, enabled features, endpoints, authentication identities, region/residency, state ownership, model/revision/dimension and vector namespaces, secret-store references, DNS/TLS, egress restrictions, backup location/retention, and rollback point. Record non-secret identifiers only. Development credentials must never become production defaults.

Preserve these service boundaries rather than replacing foundations:

- Web and API remain distinct. Browser-visible origins, secure cookies, CORS and WebSocket host checks must match the actual domain plan.
- PostgreSQL remains catalog/account/order source of truth. Search/vector stores are derived state, not the only recovery source.
- Milvus, its metadata and object store form a matching recovery set. Maintain model/revision/dimension/index provenance together. Keep the present retrieval model unchanged until its separate acceptance path passes.
- RabbitMQ and Redis require defined recovery/loss semantics, retry/idempotency behavior and network isolation. A queue depth or cache hit alone is not order correctness.
- API/worker provider egress must be explicit. Current work permits no paid provider, live Tavily or payment validation. A deployment may not silently turn those on.
- External S3 remains the production storage target described by current code. AWS-specific endpoint validation and workload IAM remain real constraints; another cloud would require a separately tested adapter/configuration change, not a hostname substitution.

## Preparation stages, not commands to execute

1. Freeze a candidate revision only after complete exact-head CI and postmerge verification. Record effective combined Compose configuration with values redacted, image digests, enabled profiles and all persistent volume identities. Do not paste rendered environments into evidence.
2. Inventory resources on the intended host: total/available RAM, disk/headroom/IO, CPU, architecture, filesystem and network limits. Measure cold and warm startup with the existing pinned model; configuration limits are not measured requirements. No new model download is included.
3. Produce an isolated restore packet: database backup plus schema revision, object/etcd/Milvus matching state, search rebuild provenance, keys available via the approved secret store and documented off-host restore route. Define RPO/RTO as targets until an actual timed drill passes.
4. Preview deployment side effects, especially the automatic migration/initial-data entrypoint, startup model acquisition, external calls, irreversible schema/index changes and service downtime. Obtain the owner's exact environment/scope approval before any affected operation. CI permission for disposable databases does not authorize a host or cluster deployment.
5. In a separately approved environment, test health/readiness, anonymous/authenticated boundaries, session behavior, retrieval freshness, cart/order idempotency and truthful provider failures using synthetic data. Measure resource usage and latency. Keep new cart activation, live merchant data and voice-last acceptance separate.
6. Test rollback before accepting release: compatible app/schema pair, restored state, matching model/vector metadata and a verified route back. A previous image alone cannot undo a schema or data change. Never delete the old recovery set during a canary.

## Release evidence packet

Require revision/digests, environment/region, time, authority scope, effective configuration references, migration/restore provenance, correctness tests, measured resource/latency results, monitoring/alert checks, known exclusions, rollback rehearsal and owner acceptance. No capacity, one-second, HA, disaster-recovery or production-readiness claim follows from this plan alone.

## Decisions deferred until a real deployment is requested

Provider/account/region, domain, budget ceiling, final capacity target, acceptable downtime, backup retention and operator ownership. These do not block local preparation and do not need to be guessed now. Future S3 account/permissions and actual migration remain independently gated.
