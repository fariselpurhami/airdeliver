# infrastructure/router/Dockerfile         

FROM python:3.9-slim-bullseye as builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --target=/install \
    mavproxy==1.8.74 \
    future==1.0.0 \
    pyserial==3.5 \
    pymavlink==2.4.41 \
    lxml==5.1.0

FROM python:3.9-slim-bullseye

LABEL maintainer="airdeliver Engineering <eng@airdeliver.com>"
LABEL service="mavlink-sidecar"
LABEL version="1.0.0"

RUN groupadd -g 10001 router && \
    useradd -u 10001 -g router -s /bin/bash -m router

RUN apt-get update && apt-get install -y --no-install-recommends \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local/lib/python3.9/site-packages
ENV PATH="/usr/local/lib/python3.9/site-packages/bin:${PATH}"

WORKDIR /app
COPY --chown=router:router entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

USER router

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD nc -z -u -v 127.0.0.1 14550 || exit 1

STOPSIGNAL SIGTERM

ENTRYPOINT ["/app/entrypoint.sh"]
