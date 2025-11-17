# apps/api/Dockerfile

FROM python:3.11-slim AS builder

WORKDIR /app

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=false \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_CACHE_DIR=/tmp/poetry_cache \
    POETRY_VERSION=1.8.3

RUN addgroup --system --gid 1001 airdeliver \
    && adduser --system --uid 1001 --gid 1001 --home /home/airdeliver airdeliver

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir "poetry==${POETRY_VERSION}"

COPY poetry.lock pyproject.toml ./

RUN poetry install --no-root --without dev

FROM python:3.11-slim AS final

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV APP_USER=airdeliver
ENV APP_GROUP=airdeliver
ENV APP_UID=1001
ENV APP_GID=1001
ENV HOME=/home/airdeliver
ENV HF_HOME=/app/storage/models_cache/huggingface
ENV SENTENCE_TRANSFORMERS_HOME=/app/storage/models_cache/sentence_transformers

RUN addgroup --system --gid $APP_GID $APP_GROUP \
    && adduser --system --uid $APP_UID --gid $APP_GID --home /home/airdeliver $APP_USER

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY --chown=airdeliver:airdeliver ./app ./app
COPY --chown=airdeliver:airdeliver ./alembic.ini ./
COPY --chown=airdeliver:airdeliver ./alembic ./alembic
COPY --chown=airdeliver:airdeliver ./seed.py ./

RUN mkdir -p /app/static/avatars \
    && mkdir -p $SENTENCE_TRANSFORMERS_HOME \
    && mkdir -p $HF_HOME \
    && chown -R $APP_USER:$APP_GROUP /app/static \
    && chown -R $APP_USER:$APP_GROUP /app/storage \
    && chown -R $APP_USER:$APP_GROUP /home/airdeliver

USER $APP_USER

RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

HEALTHCHECK --interval=5s --timeout=3s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8000/api/v1/health || exit 1

EXPOSE 8000

CMD ["gunicorn", "app.main:app", "-w", "${WEB_CONCURRENCY:-4}", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
