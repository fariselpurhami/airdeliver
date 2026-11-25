# airdeliver on Kubernetes

Production manifests for the full airdeliver stack. These mirror
`docker-compose.yml` service-for-service and use the same env contract as
`backend/api/app/core/config.py`.

## Prerequisites
- A cluster with an Ingress controller: **Traefik** (same edge proxy as the
  compose stack). Install via `helm install traefik traefik/traefik`.
- A default StorageClass for RWO volumes, plus an RWX-capable class for the
  shared model cache (see `12-storage.yml` for the fallback).
- Container images pushed to a registry:
  - `backend/api` -> `yourregistry/airdeliver-api:latest`
  - `frontend/web` -> `yourregistry/airdeliver-web:latest` (build args
    `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_WS_URL`, `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` are baked in
    at build time).

## Install
1. Fill in every `CHANGE_ME` in `00-namespace-config.yml` (or create the
   `airdeliver-secrets` Secret out-of-band instead of applying that doc).
2. Replace `yourregistry/...` image names and the hosts in `03-ingress.yml`.
3. Apply in numeric order:
   `kubectl apply -f 00-namespace-config.yml -f 12-storage.yml`
   `kubectl apply -f 06-postgres.yml -f 07-redis.yml -f 08-rabbitmq.yml -f 09-opensearch.yml -f 10-milvus.yml`
   `kubectl apply -f 01-service.yml -f 02-api-deployment.yml -f 04-web.yml -f 05-api-worker.yml`
   `kubectl apply -f 03-ingress.yml -f 11-monitoring.yml`
4. Verify: `kubectl -n airdeliver get pods` (all Ready), then
   `kubectl -n airdeliver port-forward svc/api 8000:8000` and hit
   `/api/v1/health`.

## Notes
- Database migrations run as an initContainer of the api Deployment
  (`alembic upgrade head`).
- The api-worker Deployment is 1 replica on purpose; the RabbitMQ queues it
  consumes are quorum queues declared at startup.
- TLS: the Ingress expects a `airdeliver-tls` secret; use cert-manager or
  provide the cert manually.
- Stateful data services here are single-node by design. For HA, adopt the
  corresponding operators (CloudNativePG, Spotahome Redis, RabbitMQ Cluster
  Operator, OpenSearch Operator, milvus-operator) rather than growing these
  manifests.

## Object storage target

`10-milvus.yml` now requires external Amazon S3 configuration via
`milvus-s3-config`. See `../../docs/object-storage.md` and the non-applied
`../s3/milvus-s3-config.yml.example`. Workload IAM role/service-account binding,
bucket provisioning and permission checks are prerequisites, not automated.
The old MinIO manifests are preserved in `legacy/minio.yml.example` for
historical reference only. No PVC is deleted by this repository change.
Do not upgrade an existing Milvus2.3 installation or change its bucket in place
without Milvus's supported upgrade and data migration/rollback plan.
