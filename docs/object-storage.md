# Local RustFS, future Amazon S3

Production target: Amazon S3. No AWS account/resource is created, and nothing is
paid for or uploaded to AWS by the local development stack.

## Why RustFS locally

Pinned RustFS1.0.6 Apache2 image passed our real S3/Milvus integration and
cache-free recovery tests. It is the local compatibility backend, not a claim
of production safety. Current upstream operational issues9488/9517 and no HA,
disk-failure/partition/soak proof remain relevant. Single container, single disk,
console disabled, no storage port published, Docker network access only.
The service remains named `minio` solely to preserve the internal DNS contract.
Archived source-built MinIO is not used by development or default production.
Its source remains in `infra/minio-ce`, old volumes remain untouched, and its
base Compose service is opt-in `legacy-minio` for historical recovery only.
Never enable that profile for new production.

## Existing local setup, do not overwrite configuration

```sh
git pull
docker network inspect airdeliver-global-net >/dev/null 2>&1 || docker network create airdeliver-global-net
docker compose --env-file .env.dev -f docker-compose.yml -f docker-compose.dev.yml -p airdeliver_dev up --build -V
```

If `.env.dev` does not exist, generate a fresh isolated stack first:

```sh
LOCAL_UID="$(id -u)" LOCAL_GID="$(id -g)" docker compose --env-file /dev/null -f docker-compose.dev-setup.yml run --rm configure --fresh
```

Do NOT rerun setup by deleting an existing `.env.dev`. Existing configurations
continue working with explicit **local-only** fallback credentials. For new
setups the helper generates private random `DEV_S3_ACCESS_KEY` and
`DEV_S3_SECRET_KEY`; never set these to AWS keys. To replace fallback credentials,
edit those two values locally in ignored mode0600 `.env.dev`, update both at
once, and restart RustFS+Milvus. Other secrets are not changed.

### Data boundary

Changing an endpoint is not migration. Default new dev RustFS data, etcd and
Milvus volumes use a new `_rustfs_v1_` namespace. This intentionally starts an
empty vector index rather than pairing historical etcd metadata with an empty
object store. PostgreSQL and OpenSearch volumes are unchanged. Existing
`minio-data`, `etcd-data`, `milvus-data` are not deleted or reformatted.
Historical AIRDELIVER_DEV_ETCD_VOLUME/MILVUS_VOLUME overrides are deliberately
not reused. New override names are AIRDELIVER_DEV_RUSTFS_ETCD_VOLUME and
AIRDELIVER_DEV_RUSTFS_MILVUS_VOLUME; never point those to historical volumes.
Existing production data must not use this dev switch.
Rebuild indexes from the authoritative catalog or make a separately tested
migration. The demo seeder adds demo products; it is NOT a migration/reindexer
for existing production products.

```sh
# Optional demo catalog, real embeddings. Default GTE1.5B has high memory needs.
docker compose --env-file .env.dev -f docker-compose.yml -f docker-compose.dev.yml -p airdeliver_dev --profile tools run --rm api-seeder
```

No `down -v`, no pruning, no data removal. Old-server restoration requires the
old matching endpoint, credentials, object volume AND etcd/Milvus metadata
snapshot. Do not guess volume names.

## Future production configuration, not a launch instruction

Base Compose targets external AWS S3 with TLS, virtual-host addressing and IAM
role auth. Startup refuses an empty bucket/region or a non-AWS TLS endpoint.
Set `S3_REGION`, `S3_ENDPOINT` as host:443, `S3_BUCKET_NAME`, and `S3_ROOT_PATH`.
The example region us-east-1 is a placeholder, not a residency decision. Choose
region deliberately before provisioning, and keep bucket/region consistent.
Pre-create the bucket; restrict public access, use encryption and explicit
retention/versioning/lifecycle and backup policies for the deployment's RPO/RTO.
Do not expire active Milvus objects with an indiscriminate lifecycle rule.

Prefer `S3_USE_IAM=true` and a workload IAM role. For approved non-role setups,
`S3_USE_IAM=false`, `S3_ACCESS_KEY_ID` and `S3_SECRET_ACCESS_KEY` can be injected
at runtime by a secret manager or ignored protected env file, never repository
or chat. Environment credentials are visible to Docker administrators. Temporary
session credentials should use workload IAM, not a token-less static-key path.
No credential chain, AWS permissions or egress test has been performed against
an AWS account. Local success does not prove AWS IAM/TLS/network readiness.
Milvus uses `MINIO_*` names even for AWS; our S3_* names map to these settings.
Application services connect to Milvus through `MILVUS_URI`; the source audit
found no independent boto/S3 object upload path requiring a second client.

`infra/s3/milvus-policy.example.json` is a scoped example, not a deployed grant.
Replace bucket and match the `milvus` prefix to S3_ROOT_PATH. Use a dedicated
Milvus bucket: bucket existence/list checks need bucket-level ListBucket without
a prefix; this grants visibility to that dedicated bucket, not all account
buckets. Object read/write/delete, multipart parts and abort are restricted to
the Milvus prefix. No CreateBucket, bucket-policy administration,
ListAllMyBuckets or IAM privileges. Validate exact permission needs on AWS
before launch, including HeadBucket, multipart and deletion. Do not widen to
s3:* to make startup errors disappear. SSE-KMS additionally requires a reviewed
KMS key policy and narrowly scoped KMS permissions, not included here.

Kubernetes: `infra/k8s/10-milvus.yml` references externally provided config.
`infra/s3/milvus-s3-config.yml.example` is deliberately non-applied. Set up the
service-account role and egress/DNS/TLS before deployment. No cluster was
changed or validated by this local work.

## Validation scope

Real disposable PostgreSQL19 and full backend tests; RustFS+Milvus2.6.17+
OpenSearch integration with17products, learned MiniLM384 vectors, replay and
Milvus compute recreation without cached vector files. Default production
GTE1.5B1536 remains a separate model/resource test. No AWS, HA or whole-platform
production certification implied.

Official sources:
- https://milvus.io/docs/deploy_s3.md
- https://milvus.io/docs/configure_minio.md
- https://github.com/milvus-io/milvus/blob/v2.6.17/configs/milvus.yaml
- https://github.com/milvus-io/milvus/blob/v2.6.17/pkg/config/env_source.go
- https://docs.aws.amazon.com/AmazonS3/latest/userguide/example-policies-s3.html
- https://github.com/rustfs/rustfs/releases/tag/1.0.6
- https://github.com/rustfs/rustfs/issues/9488
- https://github.com/rustfs/rustfs/issues/9517
