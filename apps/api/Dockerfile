
FROM python:3.11-slim as builder

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential curl && \
    pip install poetry==1.8.3 && \
    rm -rf /var/lib/apt/lists/*

COPY poetry.lock pyproject.toml ./

RUN poetry export --without dev --without-hashes -f requirements.txt -o requirements.txt --extras "email"

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

RUN ls /install/lib/python3.11/site-packages/ | grep jose

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONPATH=/app

RUN mkdir -p /usr/local/lib/python3.11/site-packages

COPY --from=builder /install/lib/python3.11/site-packages/. /usr/local/lib/python3.11/site-packages/

COPY --from=builder /install/bin /usr/local/bin

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
