# drone_client/Dockerfile

FROM python:3.11-slim-bookworm AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential cmake git && \
    rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir mavsdk==1.4.1 && \
    pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim-bookworm AS final

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN groupadd -g 1001 drone && \
    useradd -u 1001 -g drone -s /bin/bash -m drone && \
    apt-get update && \
    apt-get install -y --no-install-recommends libstdc++6 && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder --chown=drone:drone /opt/venv /opt/venv
COPY --chown=drone:drone drone-control.py .

USER drone

CMD ["python", "drone-control.py"]
