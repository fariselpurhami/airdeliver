# apps/api/Dockerfile

FROM python:3.11-slim as builder

WORKDIR /app

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=false \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_CACHE_DIR=/tmp/poetry_cache

RUN pip install --no-cache-dir --upgrade pip poetry

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential curl && \
    rm -rf /var/lib/apt/lists/*

COPY poetry.lock pyproject.toml ./

RUN poetry install --no-root --without dev

FROM python:3.11-slim as final

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY ./app ./app
COPY ./alembic.ini ./
COPY ./alembic ./alembic
COPY ./seed.py ./

RUN apt-get update && apt-get install -y curl --no-install-recommends && rm -rf /var/lib/apt/lists/*

HEALTHCHECK --interval=5s --timeout=3s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8000/ws/health || exit 1

EXPOSE 8000

CMD ["bash", "-c", \

     "alembic upgrade base && \
      alembic upgrade head && \
      uvicorn app.main:app --host 0.0.0.0 --port 8000"]
