# Local-development compatibility build. MinIO CE is archived, not supported.
# Official public registries stopped serving the old images. Preserve the real
# S3 foundation from verifiable source, never substitute an in-memory fake.
FROM golang:1.26.11-bookworm@sha256:dc40a13b61304647ed7e5d581d246b86413dfc29d63c6d018310feb93cd98fc0 AS builder
WORKDIR /src
ADD --checksum=sha256:71794c2df26aad0cc99e8421c58b7aa2dd55969f979b0e7d1e931042e9fabcd6 https://codeload.github.com/minio/minio/tar.gz/7aac2a2c5b7c882e68c1ce017d8256be2feea27f /tmp/minio.tar.gz
RUN tar -xzf /tmp/minio.tar.gz --strip-components=1 && rm /tmp/minio.tar.gz
ENV CGO_ENABLED=0 GOTOOLCHAIN=local GOMAXPROCS=2
RUN --mount=type=cache,target=/go/pkg/mod --mount=type=cache,target=/root/.cache/go-build go build -p 2 -trimpath -o /out/minio .

FROM debian:bookworm-slim@sha256:734a72b3d6142a71993b4bc580ca01d8ca687f77a2c422d96a961d3376b179bc
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl && rm -rf /var/lib/apt/lists/*
COPY --from=builder /out/minio /usr/local/bin/minio
COPY --from=builder /src/LICENSE /usr/share/doc/minio/LICENSE
LABEL org.opencontainers.image.source="https://github.com/minio/minio" org.opencontainers.image.revision="7aac2a2c5b7c882e68c1ce017d8256be2feea27f" org.opencontainers.image.licenses="AGPL-3.0"
EXPOSE 9000
VOLUME /minio_data
CMD ["minio", "server", "/minio_data"]
