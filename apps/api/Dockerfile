# apps/api/Dockerfile

FROM python:3.11-slim-bookworm AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    POETRY_VERSION=1.8.3 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=false \
    POETRY_NO_INTERACTION=1 \
    VIRTUAL_ENV="/opt/venv" \
    HF_HOME="/data/storage/models_cache/huggingface" \
    SENTENCE_TRANSFORMERS_HOME="/data/storage/models_cache/sentence_transformers" \
    PATH="/opt/poetry/bin:/opt/venv/bin:$PATH"

FROM base AS builder
WORKDIR /app
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    git && \
    rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | python3 -
RUN python -m venv $VIRTUAL_ENV

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --only main

FROM base AS model_downloader
WORKDIR /models
RUN pip install --no-cache-dir sentence-transformers
RUN mkdir -p ${SENTENCE_TRANSFORMERS_HOME} && \
    python -c "import os; from sentence_transformers import SentenceTransformer; \
    print('Downloading model to:', os.environ['SENTENCE_TRANSFORMERS_HOME']); \
    os.makedirs(os.environ['SENTENCE_TRANSFORMERS_HOME'], exist_ok=True); \
    SentenceTransformer('all-MiniLM-L6-v2', cache_folder=os.environ['SENTENCE_TRANSFORMERS_HOME'])"

FROM base AS production
WORKDIR /app
ARG APP_USER=airdeliver
ARG APP_UID=1001
ARG APP_GID=1001

RUN groupadd -g $APP_GID $APP_USER && \
    useradd -u $APP_UID -g $APP_GID -d /home/$APP_USER -s /bin/bash -m $APP_USER && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq5 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder --chown=$APP_USER:$APP_USER $VIRTUAL_ENV $VIRTUAL_ENV
COPY --from=model_downloader --chown=$APP_USER:$APP_USER /data/storage /data/storage

COPY --chown=$APP_USER:$APP_USER ./app ./app
COPY --chown=$APP_USER:$APP_USER ./alembic.ini ./
COPY --chown=$APP_USER:$APP_USER ./alembic ./alembic
COPY --chown=$APP_USER:$APP_USER ./seed_data.json ./

USER $APP_USER

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/health || exit 1

EXPOSE 8000

CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-"]
