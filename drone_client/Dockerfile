# drone_client/Dockerfile 

FROM python:3.11-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

WORKDIR /build

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git && \
    rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip

RUN pip install --no-cache-dir mavsdk==1.4.1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim-bookworm AS final

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app
ARG APP_USER=drone
ARG APP_UID=1001
ARG APP_GID=1001


RUN existing_group=$(getent group $APP_GID | cut -d: -f1) && \
    if [ -n "$existing_group" ]; then groupdel $existing_group; fi && \
    groupadd -g $APP_GID $APP_USER && \
    useradd -u $APP_UID -g $APP_GID -d /home/$APP_USER -s /bin/bash -m $APP_USER && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    libstdc++6 \
    procps && \
    rm -rf /var/lib/apt/lists/*


COPY --from=builder --chown=$APP_USER:$APP_USER /opt/venv /opt/venv
COPY --chown=$APP_USER:$APP_USER drone-control.py .

USER $APP_USER

CMD ["python", "drone-control.py"]
