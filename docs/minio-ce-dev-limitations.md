# MinIO Community Edition compatibility, not production readiness

The upstream `minio/minio` repository is archived. The old Docker Hub image used by this repository failed a fresh CI pull on November 22, 2026. Quay is not assumed available as a fallback. Requiring a paid AIStor account is outside the user's instructions.

The development compatibility build under `infra/minio-ce` compiles the last public source revision and verifies its archive SHA-256. Both build and runtime images are pinned by digest. It preserves the actual S3 service required by Milvus. It does not remove MinIO, replace it with an in-memory fake, or claim the archived source is maintained. It preserves source licensing in the runtime image. OS packages are not individually pinned, so this is not a fully reproducible build claim.

Use only for disposable local test data on a private development network. Do not publish its port or put production uploads, customer data or secrets in it. Fresh development volumes are isolated from older volumes. Building from source needs network access, time, disk and memory; the first build is slower than pulling a cached image.

Official advisories identify high-severity unresolved Community Edition risks, including signature bypass and memory-exhaustion paths. A source build does not cure those issues. No production object-storage-ready claim is made. Production requires a maintained compatible S3 backend and tested Milvus integration/migration, or a properly licensed supported distribution selected by the owner. Existing production data is not migrated, overwritten or deleted by this development change.

Sources checked:
- https://github.com/minio/minio
- https://api.github.com/repos/minio/minio
- https://api.github.com/repos/minio/minio/commits/master
- https://github.com/minio/minio/security/advisories/GHSA-hv4r-mvr4-25vw
- https://github.com/minio/minio/security/advisories/GHSA-9c4q-hq6p-c237
- https://github.com/minio/minio/security/advisories/GHSA-h749-fxx7-pwpg
