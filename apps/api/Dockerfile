# apps/api/Dockerfile - Golden Enterprise Edition
# Validated by Chief Software Architect
# Final Version: Offline Model Support + Robust Worker Setup

# -----------------------------------------------------------------------------
# STAGE 1: Base Configuration
# -----------------------------------------------------------------------------
FROM python:3.11-slim-bookworm AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    POETRY_VERSION=1.8.3 \
    POETRY_HOME="/opt/poetry" \
    POETRY_NO_INTERACTION=1 \
    # Virtual Env Location
    VIRTUAL_ENV="/opt/venv" \
    # Data Locations
    DATA_DIR="/data/storage" \
    HF_HOME="/data/storage/models_cache/huggingface" \
    # Important: This matches the path where you manually downloaded the model
    SENTENCE_TRANSFORMERS_HOME="/data/storage/models_cache/sentence_transformers" \
    PATH="/opt/poetry/bin:/opt/venv/bin:$PATH"

# -----------------------------------------------------------------------------
# STAGE 2: Builder & Dependencies
# -----------------------------------------------------------------------------
FROM base AS builder
WORKDIR /app
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    git && \
    rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Create virtualenv
RUN python -m venv $VIRTUAL_ENV

# Install Dependencies
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --only main

# -----------------------------------------------------------------------------
# STAGE 3: Model Placeholder (Offline Strategy)
# -----------------------------------------------------------------------------
FROM base AS model_downloader
WORKDIR /models
# ARCHITECTURAL NOTE: 
# We skipped the 'RUN python -c download...' command here.
# Since you downloaded the model locally to your host machine,
# we will rely on the Docker Volume Mount to provide it at runtime.
# This prevents build-time network timeouts.

# -----------------------------------------------------------------------------
# STAGE 4: Final Production Runtime
# -----------------------------------------------------------------------------
FROM base AS production
WORKDIR /app
ARG APP_USER=airdeliver
ARG APP_UID=1001
ARG APP_GID=1001

# 1. Robust User/Group Creation
RUN existing_group=$(getent group $APP_GID | cut -d: -f1) && \
    if [ -n "$existing_group" ]; then groupdel $existing_group; fi && \
    groupadd -g $APP_GID $APP_USER && \
    useradd -u $APP_UID -g $APP_GID -d /home/$APP_USER -s /bin/bash -m $APP_USER && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq5 \
    libgomp1 \
    curl && \
    rm -rf /var/lib/apt/lists/*

# 2. Create directory structure
RUN mkdir -p $HF_HOME && \
    mkdir -p $SENTENCE_TRANSFORMERS_HOME && \
    chown -R $APP_USER:$APP_USER $DATA_DIR

# 3. Copy the Virtual Env (Libs) FIRST
COPY --from=builder --chown=$APP_USER:$APP_USER $VIRTUAL_ENV $VIRTUAL_ENV

# 4. CRITICAL FIX: Install 'watchfiles' AFTER copying the venv
# This ensures the binary is not overwritten by the COPY command above
RUN pip install --no-cache-dir watchfiles

# 5. Copy Application Code
COPY --chown=$APP_USER:$APP_USER ./alembic.ini ./
COPY --chown=$APP_USER:$APP_USER ./alembic ./alembic
COPY --chown=$APP_USER:$APP_USER ./seed_data.json ./
COPY --chown=$APP_USER:$APP_USER ./app ./app

# Set User
USER $APP_USER
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Default Command (Will be overridden by docker-compose for Dev)
CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-"]
