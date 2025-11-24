# apps/c2-gateway/Dockerfile 

FROM python:3.11-slim-bookworm AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    POETRY_VERSION=1.8.3 \
    POETRY_HOME="/opt/poetry" \
    POETRY_NO_INTERACTION=1 \
    VIRTUAL_ENV="/opt/venv" \
    PATH="/opt/poetry/bin:/opt/venv/bin:$PATH"

FROM base AS builder
WORKDIR /app
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    curl && \
    rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | python3 -

RUN python -m venv $VIRTUAL_ENV

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --only main

FROM base AS production
WORKDIR /app
ARG APP_USER=airdeliver
ARG APP_UID=1001
ARG APP_GID=1001

RUN pip install --no-cache-dir watchfiles

RUN existing_group=$(getent group $APP_GID | cut -d: -f1) && \
    if [ -n "$existing_group" ]; then groupdel $existing_group; fi && \
    groupadd -g $APP_GID $APP_USER && \
    useradd -u $APP_UID -g $APP_GID -d /home/$APP_USER -s /bin/bash -m $APP_USER && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    curl && \
    rm -rf /var/lib/apt/lists/*


COPY --from=builder --chown=$APP_USER:$APP_USER $VIRTUAL_ENV $VIRTUAL_ENV
COPY --chown=$APP_USER:$APP_USER ./app ./app

USER $APP_USER
EXPOSE 8001

HEALTHCHECK --interval=5s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8001/ws/health || exit 1

CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8001", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]
