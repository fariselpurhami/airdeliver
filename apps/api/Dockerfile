# apps/api/Dockerfile

FROM python:3.11-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    POETRY_VERSION=2.2.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=false \
    POETRY_VIRTUALENVS_CREATE=false \
    VIRTUAL_ENV="/opt/venv" \
    DATA_DIR="/datastorage" \
    HF_HOME="/datastorage/models/cache/huggingface" \
    SENTENCE_TRANSFORMERS_HOME="/datastorage/models/cache/sentence_transformers" \
    PATH="/opt/poetry/bin:$VIRTUAL_ENV/bin:$PATH"

FROM base AS builder

WORKDIR /app

RUN --mount=type=cache,target=/var/cache/apt/archives,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get -o Acquire::ForceIPv4=true -o Acquire::Retries=3 update && \
    apt-get -o Acquire::ForceIPv4=true -o Acquire::Retries=3 install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    git

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --default-timeout=600 "poetry==$POETRY_VERSION" && \
    poetry config installer.max-workers 10

RUN python -m venv $VIRTUAL_ENV

COPY pyproject.toml .

RUN poetry lock

RUN --mount=type=cache,target=/root/.cache/pypoetry \
    --mount=type=cache,target=/root/.cache/pip \
    poetry install --no-root --only main --no-interaction --no-ansi

FROM base AS runtime-base

WORKDIR /app

ARG APP_USER=airdeliver
ARG APP_UID=1001
ARG APP_GID=1001

RUN groupadd -g $APP_GID $APP_USER || true && \
    useradd -u $APP_UID -g $APP_GID -d /home/$APP_USER -s /bin/bash -m $APP_USER

RUN --mount=type=cache,target=/var/cache/apt/archives,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get -o Acquire::ForceIPv4=true -o Acquire::Retries=3 update && \
    apt-get -o Acquire::ForceIPv4=true -o Acquire::Retries=3 install -y --no-install-recommends \
    libpq5 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder --chown=$APP_USER:$APP_USER $VIRTUAL_ENV $VIRTUAL_ENV

RUN mkdir -p $DATA_DIR && chown -R $APP_USER:$APP_USER $DATA_DIR

FROM runtime-base AS development

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install watchfiles

COPY --chown=$APP_USER:$APP_USER . .

USER $APP_USER
EXPOSE 8000

FROM runtime-base AS production

COPY --chown=$APP_USER:$APP_USER alembic.ini .
COPY --chown=$APP_USER:$APP_USER alembic ./alembic
COPY --chown=$APP_USER:$APP_USER seed_data.json .
COPY --chown=$APP_USER:$APP_USER app ./app
COPY --chown=$APP_USER:$APP_USER *.py .

USER $APP_USER

CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-"]
