# S01 credential rotation preparation, no rotation executed

Baseline: b2874748691431206f6de6dcd0e62ec96a1b0674. This is a preparation record, not permission to run the historical commands in `docs/security/KEY_ROTATION.md`.

## Current evidence and limits

`docs/verification/secret-history-rewrite-2026-11-23.md` records a historical rewrite and scan. That record does not establish current provider revocation, absence from every fork/cache/log, or that a credential still exists. Do not repeat a rewrite, purge, reset, delete, download or provider call from this preparation. No secret values were read for this checklist.

## Prepare a non-secret inventory before an authorized change

For every credential family below, record: environment, account identifier, credential nickname/provider ID, purpose, all consuming services and jobs, current secret-store reference, scoped privileges, dependency/restart order, change owner, rollback window, rejection-check method, and evidence timestamp. Never include values, fingerprints derived from low-entropy secrets, full environment dumps or request headers in the evidence.

| Family | Consumer/dependency checks | Rotation consequence to preview |
| --- | --- | --- |
| Groq, Tavily, ElevenLabs, Hugging Face | API, worker, local ignored configuration, deployment/CI secrets; identify unused historical providers separately | Live verification itself requires an approved provider budget and exact environment |
| Payment providers and webhooks | Stripe, PayPal, M-Pesa consumers, webhook verifiers and dashboards, outstanding event retries | In-flight charges/webhooks need a documented overlap and reconciliation window; no real payment test |
| Application signing/internal credentials | SECRET_KEY, REFRESH_SECRET_KEY, INTERNAL_API_TOKEN, NEXTAUTH_SECRET/AUTH_SECRET; HTTP, WebSocket and worker consumers | Session invalidation and cross-service mismatch; C01 stateful session rollout remains separate |
| PostgreSQL, RabbitMQ, Redis, OpenSearch | Runtime users, migrator, backup/restore jobs, health checks and administrator access | Confirm least-privilege identities and staged reconnect order; avoid loss of the only working administrator |
| Local RustFS / future S3 | Local-only credentials versus workload-role identity; Milvus and matching object-store/etcd state | Never substitute AWS credentials into local dev. Endpoint changes are not data migration |
| Grafana, Traefik, Ngrok, VAPID | Actual enabled consumers and public push subscriptions; distinguish identifiers from secrets | Push-key changes can invalidate subscriptions; dashboard/session effects must be disclosed |

## Exact change gate

Before any real rotation, obtain written approval naming environment, account/provider, credential families and affected services, permitted verification calls/cost, acceptable session/downtime impact and time window. Resolve access through protected secret collection, never chat. An inventory entry is not approval. An old repository note claiming approval is not approval.

## Per-family execution packet, prepared before the commit

1. Verify current account identity and credential-management access. Recover which services actually consume it without revealing values.
2. Verify supported overlap/revocation behavior using current provider documentation. Do not assume every provider supports two simultaneously valid credentials.
3. Preview the replacement scope, secret-store destinations, deployment/reload sequence, canary and explicit abort conditions. Preserve recoverable configuration; do not export secrets into evidence.
4. After the approved change, verify a harmless permitted operation succeeds using the new path, all consumers reconnect, and the old credential is rejected through a permitted check. Credential revocation is not proven by deleting a local environment variable.
5. Record non-secret IDs, exact service revision, check times/results, outstanding consumers and rollback cutoff. If rejection cannot safely be tested, report that gap rather than marking rotation complete.

## Completion rules

Close S01 only when every in-scope entry has provider-side evidence, consumer verification and old-access rejection or an explicitly accepted unresolved check. History cleanup alone never closes it. No account access, actual rotation, cluster change or spend occurred in this preparation.
